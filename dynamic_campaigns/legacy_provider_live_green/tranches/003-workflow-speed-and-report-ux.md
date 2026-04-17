# Tranche 003 - Workflow Speed And Report UX

## Goal

Add workflow controls for partial iteration and a report-only path that can
re-render final reports from an existing artifact without VM or GPT time.

## Evidence To Write

- Sponsor Demo E2E exposes skip/only/report-only inputs.
- Separate report-only workflow exists.
- `sponsor-report.html` is generated and uploaded.

## Local Evidence

- Added Sponsor Demo E2E dispatch inputs:
  - `skip_windows_targets`
  - `skip_gpt_matrix`
  - `only_windows_target`
  - `only_gpt_case`
  - `report_only_run_id`
- Added `.github/workflows/sponsor-demo-report-only.yml`.
- Added `.github/workflows/sponsor-report-fixture.yml`.
- Added `sponsor-report.html` generation from `summarize-sponsor-demo`.
- YAML parsing passed locally for all workflows.

## Status

Complete locally; report-only workflow run pending after push.
