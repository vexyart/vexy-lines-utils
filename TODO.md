---
this_file: TODO.md
---

# TODO - Quality Improvements

## Phase 1: Enhanced Test Coverage ✅ COMPLETED
- [x] Add test for WindowWatcher.get_current_state() method
- [x] Add test for _navigate_to_folder_direct() navigation strategy
- [x] Add test for _set_filename_simple() navigation strategy
- [x] Add test for navigation strategy fallback/retry behavior
- [x] Run pytest-cov to measure coverage (achieved 50% - reasonable for UI automation)

## Phase 2: PDF Export Validation ✅ COMPLETED
- [x] Implement validate_pdf() function with size check
- [x] Add PDF magic bytes verification (%PDF- header)
- [x] Integrate validation into _verify_export() method
- [x] Add tests for PDF validation logic (5 tests)
- [x] Log warnings for suspiciously small/large exports

## Phase 3: Graceful Interruption Handling ✅ COMPLETED
- [x] Create InterruptionHandler class with signal handling (implemented in utils/interrupt.py)
- [x] Integrate interruption check into export loop (in EnhancedVexyLinesExporter)
- [x] Add cleanup logic for partial exports (handled via signal restore)
- [x] Update statistics to reflect interrupted state (raises AutomationError with USER_INTERRUPT)
- [x] Add test for graceful interruption behavior (test_interrupt_handler in test_refactored_modules.py)

---

## Phase 4: Additional Quality & Robustness Improvements

### Task 1: Add Export Summary Statistics ✅ MOSTLY COMPLETE
- [x] Add total export time tracking to ExportStats
- [x] Calculate and log average time per file
- [x] Add skipped file count to statistics
- [ ] Include PDF validation failure count separately
- [x] Add test for enhanced statistics tracking

### Task 2: Improve Error Message Clarity
- [ ] Add specific suggestions to timeout errors (check permissions, app state, etc.)
- [ ] Create error message helper functions for common failures
- [ ] Add file path context to all error messages
- [ ] Include recovery suggestions in AutomationError messages
- [ ] Add test for error message formatting

### Task 3: Add Dry-Run Validation
- [ ] In dry-run mode, validate all .lines files before reporting success
- [ ] Check for read permissions on .lines files
- [ ] Verify write permissions in target directories
- [ ] Report potential issues that would cause failures in real run
- [ ] Add test for dry-run validation checks

---

## Phase 5: Post-Bug-Fix Quality Improvements

### Task 1: Separate PDF Validation Failures in Statistics
- [ ] Add `validation_failures` list to ExportStats for PDF validation failures
- [ ] Distinguish between export failures and validation failures in stats
- [ ] Update `human_summary()` to report validation failures separately
- [ ] Add tests for validation failure tracking
- [ ] Ensure backward compatibility in `as_dict()` output

### Task 2: Add Configuration Validation
- [ ] Validate timeout_multiplier range at config initialization
- [ ] Validate max_retries bounds at config initialization
- [ ] Add helpful error messages for invalid configuration
- [ ] Validate menu/dialog patterns are non-empty
- [ ] Add tests for configuration validation edge cases

### Task 3: Enhance Logging for Batch Operations
- [ ] Add progress indicator (e.g., "Processing 3/10 files...")
- [ ] Log time remaining estimate based on average speed
- [ ] Add summary log at the end with total time and success rate
- [ ] Improve debug logging with timing information for each step
- [ ] Add tests to verify logging output structure
