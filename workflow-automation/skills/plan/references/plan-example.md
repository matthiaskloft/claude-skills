# Plan: CSV Export

**Created**: 2026-03-10
**Author**: Claude

## Status

| Phase | Status | Date | Notes |
|-------|--------|------|-------|
| Plan | DONE | 2026-03-10 | Approved |
| Phase 1: Core export | TODO | | |
| Phase 2: CLI integration | TODO | | |
| Ship | TODO | | |

## Summary

**Motivation**: Users currently have to manually copy pipeline results from
the console. They need a way to export processed data to CSV files for use
in spreadsheets and downstream tools.

**Outcome**: Users can call `pipeline.export("output.csv")` or pass
`--export csv` on the command line to write results directly to a file.

## Assumptions

- The pipeline's output is always a tabular structure (rows + columns)
- CSV is sufficient for the first version; other formats (Parquet, JSON)
  can be added later
- File paths are provided by the user, not auto-generated

## Design Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Export API | Method on Pipeline vs. standalone function | Method on Pipeline | Keeps export close to the data; avoids passing internal state around |
| CSV library | Built-in csv module vs. pandas | Built-in csv | No new dependency; pipeline output is simple enough |
| Overwrite behavior | Error if exists vs. overwrite vs. prompt | Error if exists | Safest default; user can delete manually |

_Add a row for each major design decision._

## Scope

### In Scope
- `Pipeline.export(path, delimiter=",")` method
- `--export` CLI flag with path argument
- Header row from column names
- Error on existing file

### Out of Scope
- Other formats (Parquet, JSON, Excel)
- Streaming export for large datasets
- Auto-generated filenames

## Implementation Plan

### Phase 1: Core export

**Files to create:**
- `src/export.py` — export logic (write_csv function)
- `tests/test_export.py` — unit tests

**Files to modify:**
- `src/pipeline.py` — add `export()` method

**Steps:**
1. Create `write_csv(rows, columns, path, delimiter)` in `src/export.py`
2. Add `export()` method to Pipeline that calls `write_csv`
3. Write tests: happy path, existing file error, custom delimiter, empty data

**Depends on:** None

### Phase 2: CLI integration

**Files to create:**
- None

**Files to modify:**
- `src/cli.py` — add `--export` flag
- `tests/test_cli.py` — add CLI export tests

**Steps:**
1. Add `--export` argument to argparse in `src/cli.py`
2. Wire it to `pipeline.export()` after pipeline execution
3. Write tests: CLI flag parsing, end-to-end export via CLI

**Depends on:** Phase 1 (core export must exist)

## Verification & Validation

- **Automated**: Unit tests for export logic, CLI integration tests
- **Manual**: Run pipeline on sample data, export to CSV, open in a
  spreadsheet and verify contents match console output

## Dependencies

- No new external dependencies

## Notes

_Living section — updated during implementation._

## Review Feedback

_Populated by plan-reviewer agent._
