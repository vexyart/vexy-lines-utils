---
this_file: TODO.md
---

# TODO: vexy-lines-utils v3.0

## Phase 1: Fix Preference Domain
- [x] Update APP_DOMAIN in core/plist.py from "com.vexy-art.lines" to "com.fontlab.vexy-lines"
- [x] Update all tests that reference the old domain
- [x] Update documentation (README, CLAUDE.md)

## Phase 2: MCP Client Module
- [x] Create src/vexy_lines_utils/mcp/ package with __init__.py
- [x] Implement mcp/client.py — TCP connection, JSON-RPC framing, initialize handshake
- [x] Implement mcp/types.py — dataclasses for DocumentInfo, LayerNode, FillParams, RenderStatus
- [x] Implement mcp/tools.py — typed methods for all 25 MCP tools (merged into client.py)
- [x] Write unit tests for MCPClient connect/disconnect/send/receive (mocked socket)
- [x] Write unit tests for each tool wrapper method

## Phase 3: Expand CLI
- [x] Add mcp-status subcommand
- [x] Add new-document subcommand
- [x] Add open subcommand
- [x] Add tree subcommand
- [x] Add add-fill subcommand
- [x] Add render subcommand
- [x] Add --json flag for machine-readable output
- [x] Update README with new CLI documentation

## Phase 4: Testing
- [x] Add tests/test_mcp_client.py with mocked socket tests
- [x] Add tests for CLI subcommands (in test_package.py TestMCPCLI)
- [x] Update tests/test_package.py for new plist domain
- [x] Add _private/mcp/test_integration.py for live testing

## Phase 5: Documentation and Release
- [x] Update README.md with MCP API section
- [x] Update DEPENDENCIES.md
- [x] Write CHANGELOG.md entry for v3.0
- [ ] Tag and release v3.0.0
