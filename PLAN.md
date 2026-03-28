---
this_file: PLAN.md
---

# PLAN: vexy-lines-utils v3.0 — Full Vexy Lines Python SDK

## Project Scope

Expand vexy-lines-utils from an export-only CLI tool into a comprehensive Python SDK that drives the Vexy Lines desktop app through two channels:
1. **AppleScript + plist injection** (existing) — headless batch export on macOS
2. **MCP API** (new) — programmatic document manipulation via the app's embedded JSON-RPC server

## Phase 1: Fix Preference Domain (Breaking Change)

The app's QSettings domain changed from `com.vexy-art.lines` to `com.fontlab.vexy-lines`. The current code in `core/plist.py` uses the old domain.

### Tasks
- Update `APP_DOMAIN` in `core/plist.py` from `"com.vexy-art.lines"` to `"com.fontlab.vexy-lines"`
- Update all tests that reference the old domain
- Update documentation (README, CLAUDE.md)
- This is a breaking change for users on old Vexy Lines versions — document in CHANGELOG

## Phase 2: MCP Client Module

Add a TCP JSON-RPC 2.0 client that connects to the Vexy Lines MCP server at `localhost:47384`.

### Architecture
```
vexy_lines_utils/
  mcp/
    __init__.py        # Public API: MCPClient, MCPError
    client.py          # TCP connection, JSON-RPC send/receive, initialize handshake
    tools.py           # Typed Python methods wrapping each MCP tool
    types.py           # Dataclasses for tool responses (DocumentInfo, LayerTree, FillParams, etc.)
```

### Design Decisions
- **Synchronous TCP socket** — matches existing sync codebase, keeps it simple
- **Single `MCPClient` class** — context manager, handles connect/initialize/disconnect
- **Typed wrappers** — one Python method per MCP tool with type hints and docstrings
- **Dataclass responses** — structured results, not raw dicts
- **No external dependencies** — uses stdlib `socket` and `json` only

### MCPClient API sketch
```python
with MCPClient(host="127.0.0.1", port=47384) as client:
    # Document ops
    doc = client.new_document(width=800, height=600, dpi=300, source_image="/path/to/img.jpg")
    info = client.get_document_info()
    tree = client.get_layer_tree()

    # Structure manipulation
    group_id = client.add_group(caption="Eyes")
    layer_id = client.add_layer(group_id=group_id)
    fill_id = client.add_fill(layer_id=layer_id, fill_type="circular", color="#ff0000")

    # Fill parameters
    client.set_fill_params(fill_id, interval=20, angle=30, thickness=2)
    params = client.get_fill_params(fill_id)

    # Masks (SVG paths in pixel coordinates)
    client.set_layer_mask(layer_id, paths=["M 100 200 C 150 100 250 100 300 200 Z"])

    # Render and export
    client.render_all()
    client.export_document("/path/to/output.pdf")
    client.save_document()
```

### Tasks
- Create `src/vexy_lines_utils/mcp/` package
- Implement `client.py` with TCP connection, JSON-RPC framing, initialize handshake
- Implement `types.py` with dataclasses for DocumentInfo, LayerNode, FillParams, RenderStatus
- Implement `tools.py` with typed methods for all 25 MCP tools
- Write unit tests (mock TCP socket) for client connect/disconnect/send/receive
- Write unit tests for each tool wrapper method
- Write integration test script (requires running Vexy Lines app)

## Phase 3: Expand CLI

Add new CLI subcommands beyond `export`:

### New subcommands
- `vexy-lines-utils mcp-status` — check if MCP server is reachable
- `vexy-lines-utils new-document` — create a new document via MCP
- `vexy-lines-utils open` — open a .lines file via MCP
- `vexy-lines-utils tree` — print the layer tree of the current document
- `vexy-lines-utils add-fill` — add a fill to a layer
- `vexy-lines-utils render` — trigger render_all

### Tasks
- Add new Fire subcommands to `__main__.py`
- Each subcommand creates an MCPClient, calls the method, prints the result
- Add `--json` flag for machine-readable output
- Update README with new CLI documentation

## Phase 4: Testing

### Unit tests (mock-based, cross-platform)
- MCPClient connect/disconnect lifecycle
- JSON-RPC message framing (newline-delimited)
- Initialize handshake
- Each tool wrapper: correct params sent, response parsed into dataclass
- Error handling: connection refused, timeout, server error responses
- PlistManager with new domain

### Integration tests (require running Vexy Lines on macOS)
- Full MCP workflow: new_document → add_group → add_layer → add_fill → render → export
- Export pipeline (existing tests updated for new domain)

### Tasks
- Add `tests/test_mcp_client.py` with mocked socket tests
- Add `tests/test_mcp_tools.py` with tool wrapper tests
- Update `tests/test_package.py` for new plist domain
- Add `_private/mcp/test_integration.py` for live testing (not in CI)

## Phase 5: Documentation and Release

### Tasks
- Update README.md with MCP API section and new CLI commands
- Update CLAUDE.md with architecture changes
- Update DEPENDENCIES.md (no new runtime deps expected)
- Write CHANGELOG.md entry for v3.0
- Tag and release v3.0.0

## Dependencies

**No new runtime dependencies.** The MCP client uses stdlib `socket` + `json`. This is intentional — the package stays minimal.

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| App not running when MCP called | Medium | Clear error message with recovery suggestion |
| Port 47384 conflict | Low | Make port configurable |
| Old domain users broken | High | Document breaking change, detect old domain and warn |
| MCP protocol changes | Low | Pin protocol version "2024-11-05" |

## Success Criteria

1. `uvx hatch test` passes with all new tests
2. Existing export pipeline works with new plist domain
3. MCPClient can execute full workflow: new_document → add_fill → render → export
4. CLI has working `mcp-status` and `tree` subcommands
5. README documents both export and MCP usage
