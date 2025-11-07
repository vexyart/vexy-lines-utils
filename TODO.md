---
this_file: TODO.md
---

# TODO - Quality Improvements

## Completed Phases

### Phase 1: Enhanced Test Coverage  COMPLETED
- [x] Add test for WindowWatcher.get_current_state() method
- [x] Add test for navigation strategies
- [x] Run pytest-cov to measure coverage (achieved 50%)

### Phase 2: PDF Export Validation  COMPLETED
- [x] Implement validate_pdf() function
- [x] Add PDF magic bytes verification
- [x] Integrate validation into _verify_export()
- [x] Add tests for PDF validation (5 tests)

### Phase 3: Graceful Interruption Handling  COMPLETED
- [x] Create InterruptionHandler class
- [x] Integrate interruption check into export loop
- [x] Add cleanup logic for partial exports

### Phase 4: Additional Quality & Robustness  COMPLETED
- [x] Add export summary statistics with timing
- [x] Add configuration validation with constants

### Phase 5: Bug Fixes & Code Quality  COMPLETED
- [x] Fix AttributeError in EnhancedVexyLinesExporter
- [x] Smart unsaved changes dialog handling
- [x] Zero ruff warnings achieved

### Phase 6: UX & Error Improvements  COMPLETED
- [x] Track PDF validation failures separately (was already done)
- [x] Add progress indicators with ETA to batch operations
- [x] Improve error messages with contextual suggestions

## Current Status (v1.0.7)

**Test count:** 42 tests
**Test pass rate:** 100%
**Code quality:** Zero ruff warnings
**Test duration:** 4.09s

## Future Enhancements (Optional)

### Low Priority Tasks
- [ ] Validate menu/dialog patterns are non-empty in config
- [ ] Add explicit tests for configuration validation edge cases
- [ ] Add `--no-auto-close` CLI flag if users want to keep files open
- [ ] Consider atomacos integration if PyXA proves insufficient
- [ ] Add dry-run validation (check permissions before running)

### Feature Ideas (Not Planned)
- Enhanced CLI progress bars with rich library
- Configuration file support (.toml)
- Parallel processing of multiple files
- Additional export formats (SVG, EPS)

## Notes
- Project is stable and production-ready
- Focus on maintaining quality over adding features
- All core functionality is implemented and tested
- Error handling is comprehensive with recovery suggestions
