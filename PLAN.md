---
this_file: PLAN.md
---

# Improvement Plan - Quality & Robustness Focus

## Project Scope (One Sentence)
Automate batch export of Vexy Lines .lines files to PDF via macOS UI automation with robust error handling.

## Current State Assessment

### Strengths
- Core export functionality operational
- Smart skip logic for existing PDFs
- Three-tiered folder navigation strategy
- Comprehensive logging with f-string formatting
- All 15 tests passing, zero linting warnings
- Good error diagnostics with UI state logging

### Identified Gaps (Quality & Robustness)
1. **Test Coverage:** New navigation strategies lack unit tests
2. **PDF Validation:** No verification that exported PDFs are valid/complete
3. **Graceful Shutdown:** No signal handling for user interruption (Ctrl+C)
4. **Integration Testing:** Missing end-to-end workflow validation
5. **Error Recovery:** No cleanup of partial exports on failure

## Phase 1: Enhanced Test Coverage (Priority: High)

### Objective
Ensure all code paths are tested, especially new navigation strategies.

### Tasks
- [ ] Add tests for WindowWatcher.get_current_state()
- [ ] Add tests for alternative navigation strategies (_navigate_to_folder_direct, _set_filename_simple)
- [ ] Add test for navigation strategy fallback behavior
- [ ] Verify test coverage >80% with `pytest-cov`

### Success Criteria
- New test count: 18-20 tests
- Coverage: >80% on core automation logic
- All navigation code paths exercised

### Technical Approach
- Use mocking to simulate navigation failures
- Test recursive retry with different error codes
- Verify log messages contain expected diagnostics

## Phase 2: PDF Export Validation (Priority: High)

### Objective
Verify exported PDFs are valid, complete, and not corrupted.

### Tasks
- [ ] Add PDF file validation after export
- [ ] Check PDF size is reasonable (>1KB, <500MB)
- [ ] Verify PDF magic bytes (header: `%PDF-`)
- [ ] Add optional PDF parsing check (using pypdf if available)
- [ ] Log warnings for suspiciously small/large PDFs

### Success Criteria
- Detect corrupted/incomplete PDFs before marking success
- Add test for PDF validation logic
- Gracefully handle validation failures without crashing

### Technical Approach
```python
def validate_pdf(pdf_path: Path) -> bool:
    """Validate exported PDF file."""
    # Size check
    size = pdf_path.stat().st_size
    if size < 1024:  # Less than 1KB
        logger.warning(f"PDF suspiciously small: {size} bytes")
        return False

    # Magic bytes check
    with open(pdf_path, 'rb') as f:
        header = f.read(5)
        if not header.startswith(b'%PDF-'):
            logger.error("Invalid PDF header")
            return False

    return True
```

### Packages Needed
- None (stdlib only)
- Optional: `pypdf` for deep validation (deferred)

## Phase 3: Graceful Interruption Handling (Priority: Medium)

### Objective
Allow users to safely interrupt batch operations with Ctrl+C.

### Tasks
- [ ] Add signal handler for SIGINT (Ctrl+C)
- [ ] Implement graceful shutdown that completes current file
- [ ] Add cleanup of partial exports on interruption
- [ ] Display summary of completed/interrupted files
- [ ] Add test for interruption handling

### Success Criteria
- User can press Ctrl+C during batch operation
- Current file completes (or fails cleanly)
- Remaining files are skipped gracefully
- Final statistics reflect interrupted state
- No corrupted state left behind

### Technical Approach
```python
class InterruptionHandler:
    def __init__(self):
        self.interrupted = False
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, sig, frame):
        if not self.interrupted:
            logger.warning("Interrupt received, finishing current file...")
            self.interrupted = True
        else:
            logger.error("Force quit!")
            sys.exit(1)
```

### Edge Cases
- Double Ctrl+C for force quit
- Interruption during Save dialog
- Cleanup of partially written PDFs

## Implementation Order

1. **Phase 1 (Test Coverage)** - Foundation for confident changes
2. **Phase 2 (PDF Validation)** - Immediate user value, prevents silent failures
3. **Phase 3 (Graceful Interruption)** - UX improvement, less critical

## Non-Goals (Explicitly Out of Scope)

- L Adding new export formats (SVG, EPS, PNG)
- L Configuration file support (.toml, .yaml)
- L Progress bars or fancy TUI
- L Parallel processing of multiple files
- L Analytics or telemetry
- L Cloud integration or remote execution
- L GUI application wrapper

## Success Metrics

- Test count: 18-20 tests (from 15)
- Test coverage: >80%
- Zero regressions in existing functionality
- PDF validation catches actual corruption
- User can safely Ctrl+C without data loss

## Timeline Estimate

- Phase 1: 1-2 hours
- Phase 2: 1 hour
- Phase 3: 1-2 hours
- Total: 3-5 hours

## Risk Assessment

| Phase | Risk | Mitigation |
|-------|------|------------|
| Phase 1 | Test brittleness | Use dependency injection, avoid mocking PyXA directly |
| Phase 2 | False positives | Tune validation thresholds, make checks configurable |
| Phase 3 | Platform differences | Test on multiple macOS versions, handle edge cases |
