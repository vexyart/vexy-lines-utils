# this_file: tests/test_mcp_client.py
"""Unit tests for the MCP client module."""

from __future__ import annotations

import json
import socket
from unittest.mock import MagicMock, patch

import pytest

from vexy_lines_utils.mcp.client import PROTOCOL_VERSION, MCPClient, MCPError
from vexy_lines_utils.mcp.types import DocumentInfo, LayerNode, NewDocumentResult, RenderStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(result: dict, req_id: int = 1) -> bytes:
    """Encode a successful JSON-RPC response as newline-terminated bytes."""
    return (json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}) + "\n").encode()


def _make_error_response(code: int, message: str, req_id: int = 1) -> bytes:
    """Encode a JSON-RPC error response as newline-terminated bytes."""
    return (json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}) + "\n").encode()


def _tool_response(text: str, req_id: int = 1) -> bytes:
    """Wrap text in a tools/call content array response."""
    return _make_response({"content": [{"type": "text", "text": text}]}, req_id)


def _make_client_with_socket(mock_sock: MagicMock) -> MCPClient:
    """Build an MCPClient and inject mock_sock directly (bypasses _connect)."""
    client = MCPClient(auto_launch=False)
    client._sock = mock_sock
    client._request_id = 0
    client._buffer = b""
    return client


# ---------------------------------------------------------------------------
# MCPError
# ---------------------------------------------------------------------------


class TestMCPError:
    def test_mcp_error_when_created_then_message_attribute_set(self):
        err = MCPError("boom")
        assert err.message == "boom"

    def test_mcp_error_when_created_then_is_exception(self):
        err = MCPError("oops")
        assert isinstance(err, Exception)

    def test_mcp_error_when_raised_then_caught_as_exception(self):
        with pytest.raises(MCPError, match="kaboom"):
            msg = "kaboom"
            raise MCPError(msg)


# ---------------------------------------------------------------------------
# MCPClient._connect / _close
# ---------------------------------------------------------------------------


class TestMCPClientConnection:
    def test_connect_when_successful_then_socket_created(self):
        mock_sock_instance = MagicMock()
        with patch("socket.socket", return_value=mock_sock_instance):
            client = MCPClient(host="127.0.0.1", port=47384)
            client._connect()
        mock_sock_instance.connect.assert_called_once_with(("127.0.0.1", 47384))
        assert client._sock is mock_sock_instance

    def test_connect_when_os_error_then_raises_mcp_error(self):
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect.side_effect = OSError("refused")
        with patch("socket.socket", return_value=mock_sock_instance):
            client = MCPClient(auto_launch=False)
            with pytest.raises(MCPError, match="Cannot connect"):
                client._connect()
        assert client._sock is None

    def test_connect_when_os_error_then_closes_socket(self):
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect.side_effect = OSError("refused")
        with patch("socket.socket", return_value=mock_sock_instance):
            client = MCPClient(auto_launch=False)
            with pytest.raises(MCPError):
                client._connect()
        mock_sock_instance.close.assert_called_once()

    def test_close_when_socket_open_then_shuts_down_and_closes(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._close()
        mock_sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        mock_sock.close.assert_called_once()
        assert client._sock is None

    def test_close_when_socket_none_then_no_error(self):
        client = MCPClient(auto_launch=False)
        client._sock = None
        client._close()  # should not raise


# ---------------------------------------------------------------------------
# JSON-RPC framing: _send_bytes / _recv_response
# ---------------------------------------------------------------------------


class TestJSONRPCFraming:
    def test_send_bytes_when_called_then_sends_compact_newline_delimited_json(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._send_bytes({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        sent = mock_sock.sendall.call_args[0][0]
        assert sent.endswith(b"\n")
        parsed = json.loads(sent.decode())
        assert parsed["method"] == "ping"
        # compact: no spaces after separators
        assert b" " not in sent.rstrip(b"\n")

    def test_send_bytes_when_not_connected_then_raises_mcp_error(self):
        client = MCPClient(auto_launch=False)
        client._sock = None
        with pytest.raises(MCPError, match="Not connected"):
            client._send_bytes({"method": "x"})

    def test_recv_response_when_complete_line_in_buffer_then_returns_result(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _make_response({"status": "ok"}, req_id=1)
        result = client._recv_response()
        assert result == {"status": "ok"}

    def test_recv_response_when_data_arrives_in_chunks_then_reassembles(self):
        mock_sock = MagicMock()
        full = _make_response({"x": 1})
        # Split at byte 10
        mock_sock.recv.return_value = full[10:]
        client = _make_client_with_socket(mock_sock)
        client._buffer = full[:10]
        result = client._recv_response()
        assert result == {"x": 1}

    def test_recv_response_when_connection_closed_then_raises_mcp_error(self):
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b""  # server closed
        client = _make_client_with_socket(mock_sock)
        with pytest.raises(MCPError, match="Connection closed"):
            client._recv_response()

    def test_recv_response_when_invalid_json_then_raises_mcp_error(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = b"not-json\n"
        with pytest.raises(MCPError, match="Invalid JSON"):
            client._recv_response()

    def test_recv_response_when_server_returns_error_then_raises_mcp_error(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _make_error_response(code=-32601, message="Method not found")
        with pytest.raises(MCPError, match="MCP error -32601: Method not found"):
            client._recv_response()


# ---------------------------------------------------------------------------
# Handshake
# ---------------------------------------------------------------------------


class TestHandshake:
    def test_handshake_when_version_matches_then_sends_initialized_notification(self):
        mock_sock = MagicMock()
        # Response to initialize, then nothing needed for notification
        handshake_resp = _make_response({"protocolVersion": PROTOCOL_VERSION}, req_id=1)
        mock_sock.recv.return_value = b""  # won't be called again
        client = _make_client_with_socket(mock_sock)
        client._buffer = handshake_resp
        client._handshake()

        calls = mock_sock.sendall.call_args_list
        assert len(calls) == 2  # initialize request + initialized notification
        init_msg = json.loads(calls[0][0][0])
        assert init_msg["method"] == "initialize"
        assert init_msg["params"]["protocolVersion"] == PROTOCOL_VERSION
        notif_msg = json.loads(calls[1][0][0])
        assert notif_msg["method"] == "notifications/initialized"
        assert "id" not in notif_msg  # notifications have no id

    def test_handshake_when_version_mismatch_then_raises_mcp_error(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _make_response({"protocolVersion": "1999-01-01"}, req_id=1)
        with pytest.raises(MCPError, match="Protocol mismatch"):
            client._handshake()


# ---------------------------------------------------------------------------
# call_tool
# ---------------------------------------------------------------------------


class TestCallTool:
    def test_call_tool_when_content_is_json_then_returns_parsed_dict(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        payload = json.dumps({"status": "ok", "id": 42})
        client._buffer = _tool_response(payload, req_id=1)
        result = client.call_tool("some_tool")
        assert result == {"status": "ok", "id": 42}

    def test_call_tool_when_content_is_plain_text_then_returns_string(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _tool_response("render started", req_id=1)
        result = client.call_tool("render_all")
        assert result == "render started"

    def test_call_tool_when_no_content_then_returns_raw_result(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _make_response({"content": []}, req_id=1)
        result = client.call_tool("empty_tool")
        assert result == {"content": []}


# ---------------------------------------------------------------------------
# Tool wrappers
# ---------------------------------------------------------------------------


class TestNewDocument:
    def test_new_document_when_called_with_size_then_includes_width_height_in_args(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        payload = json.dumps({"status": "created", "width": 200.0, "height": 100.0, "dpi": 300.0, "root_id": 1})
        client._buffer = _tool_response(payload, req_id=1)
        result = client.new_document(width=200.0, height=100.0)
        assert isinstance(result, NewDocumentResult)
        assert result.status == "created"
        assert result.width == 200.0
        assert result.root_id == 1
        sent = json.loads(mock_sock.sendall.call_args[0][0])
        assert sent["params"]["arguments"]["width"] == 200.0
        assert sent["params"]["arguments"]["height"] == 100.0

    def test_new_document_when_no_width_height_then_omits_them_from_args(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        payload = json.dumps({"status": "created", "width": 0, "height": 0, "dpi": 300.0, "root_id": 0})
        client._buffer = _tool_response(payload, req_id=1)
        client.new_document()
        sent = json.loads(mock_sock.sendall.call_args[0][0])
        args = sent["params"]["arguments"]
        assert "width" not in args
        assert "height" not in args
        assert args["dpi"] == 300

    def test_new_document_when_plain_text_response_then_raises_mcp_error(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _tool_response("unexpected string", req_id=1)
        with pytest.raises(MCPError, match="Unexpected response from new_document"):
            client.new_document()


class TestGetDocumentInfo:
    def test_get_document_info_when_called_then_returns_document_info(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        payload = json.dumps(
            {"width_mm": 210.0, "height_mm": 297.0, "resolution": 300.0, "units": "mm", "has_changes": True}
        )
        client._buffer = _tool_response(payload, req_id=1)
        info = client.get_document_info()
        assert isinstance(info, DocumentInfo)
        assert info.width_mm == 210.0
        assert info.units == "mm"
        assert info.has_changes is True


class TestGetLayerTree:
    def test_get_layer_tree_when_nested_then_returns_recursive_layer_node(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        tree = {
            "id": 0,
            "type": "document",
            "caption": "root",
            "visible": True,
            "children": [
                {
                    "id": 1,
                    "type": "group",
                    "caption": "bg",
                    "visible": True,
                    "children": [{"id": 2, "type": "layer", "caption": "layer1", "visible": False, "children": []}],
                }
            ],
        }
        client._buffer = _tool_response(json.dumps(tree), req_id=1)
        node = client.get_layer_tree()
        assert isinstance(node, LayerNode)
        assert node.type == "document"
        assert len(node.children) == 1
        group = node.children[0]
        assert group.type == "group"
        assert group.children[0].visible is False


class TestAddFill:
    def test_add_fill_when_called_then_sends_layer_id_and_fill_type(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _tool_response(json.dumps({"fill_id": 99}), req_id=1)
        result = client.add_fill(layer_id=5, fill_type="solid", color="#ff0000")
        sent = json.loads(mock_sock.sendall.call_args[0][0])
        args = sent["params"]["arguments"]
        assert args["layer_id"] == 5
        assert args["fill_type"] == "solid"
        assert args["color"] == "#ff0000"
        assert result == {"fill_id": 99}


class TestSetFillParams:
    def test_set_fill_params_when_kwargs_given_then_forwarded_in_args(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _tool_response("ok", req_id=1)
        client.set_fill_params(42, color="#00ff00", opacity=0.5)
        sent = json.loads(mock_sock.sendall.call_args[0][0])
        args = sent["params"]["arguments"]
        assert args["fill_id"] == 42
        assert args["color"] == "#00ff00"
        assert args["opacity"] == 0.5


class TestRenderAll:
    def test_render_all_when_called_then_returns_text_string(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _tool_response("render started", req_id=1)
        result = client.render_all()
        assert result == "render started"


class TestGetRenderStatus:
    def test_get_render_status_when_rendering_true_then_returns_render_status(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _tool_response(json.dumps({"rendering": True}), req_id=1)
        status = client.get_render_status()
        assert isinstance(status, RenderStatus)
        assert status.rendering is True

    def test_get_render_status_when_plain_text_then_raises_mcp_error(self):
        mock_sock = MagicMock()
        client = _make_client_with_socket(mock_sock)
        client._buffer = _tool_response("not json", req_id=1)
        with pytest.raises(MCPError, match="Unexpected response from get_render_status"):
            client.get_render_status()


# ---------------------------------------------------------------------------
# Types: LayerNode.from_dict
# ---------------------------------------------------------------------------


class TestLayerNodeFromDict:
    def test_from_dict_when_flat_node_then_parses_all_fields(self):
        d = {"id": 7, "type": "fill", "caption": "ink", "visible": False, "fill_type": "hatching", "children": []}
        node = LayerNode.from_dict(d)
        assert node.id == 7
        assert node.type == "fill"
        assert node.fill_type == "hatching"
        assert node.visible is False
        assert node.children == []

    def test_from_dict_when_nested_children_then_recurses(self):
        d = {
            "id": 1,
            "type": "group",
            "caption": "g",
            "visible": True,
            "children": [{"id": 2, "type": "layer", "caption": "l", "visible": True, "children": []}],
        }
        node = LayerNode.from_dict(d)
        assert len(node.children) == 1
        assert node.children[0].id == 2

    def test_from_dict_when_optional_fields_missing_then_uses_defaults(self):
        d = {"id": 3, "type": "layer"}
        node = LayerNode.from_dict(d)
        assert node.caption == ""
        assert node.visible is True
        assert node.fill_type is None
        assert node.children == []


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager_when_exited_normally_then_closes_socket(self):
        mock_sock_instance = MagicMock()
        handshake_resp = _make_response({"protocolVersion": PROTOCOL_VERSION}, req_id=1)
        mock_sock_instance.recv.return_value = b""
        with patch("socket.socket", return_value=mock_sock_instance):
            client = MCPClient(auto_launch=False)
            client._buffer = handshake_resp
            # Manually wire up: _connect sets _sock, _handshake reads buffer
            with patch.object(client, "_connect", lambda: setattr(client, "_sock", mock_sock_instance)):
                with patch.object(client, "_handshake"):
                    with client:
                        pass
        mock_sock_instance.close.assert_called()
