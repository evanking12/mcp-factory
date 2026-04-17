# Tranche 002: Diagnostics

Status: passed

## Blocker

The current final summary proves pass/fail, but it does not yet explain why a target was slow or how much time was spent in bridge health/session guards, analyzer execution, retry, task restart, VM restart, or post-grace verification.

## Fix Intent

Add machine-readable timing breakdown fields to every Windows target summary and human-readable diagnostics sections to the final sponsor markdown.

## Evidence To Fill

- Test results:
  - `python -m py_compile scripts\ci_verify.py scripts\gui_bridge.py` passed.
  - `python scripts\ci_verify.py bridge-target-e2e --help` passed.
  - `python scripts\ci_verify.py direct-bridge-e2e --help` passed.
  - `python -m pytest tests\test_ci_verify_sponsor_summary.py tests\test_ci_verify_bridge_cache.py -q` passed: 11 tests.
- Artifact fields:
  - `health_wait_seconds`
  - `session_check_seconds`
  - `session_cache_used`
  - `bridge_analyzer_seconds`
  - `retry_seconds`
  - `restart_seconds`
  - `vm_restart_seconds`
  - `post_grace_seconds`
  - `dominant_time_source`
  - `timeout_or_failure_classification`
- Final summary sections:
  - Slow Windows Targets
  - Required Windows Failures
  - Optional Diagnostic Failures
  - Bridge Recovery Events
  - Session And Cache Proof
- CI rerun URL: `https://github.com/evanking12/mcp-factory/actions/runs/24540377217`
- Artifact path: GitHub Actions artifact `sponsor-demo-e2e`, downloaded locally to `C:\Users\evanw\AppData\Local\Temp\sponsor-demo-e2e-24540377217`
- CI artifact verification:
  - `final-summary.json` has `passed=true`.
  - Every `windows/*/*.summary.json` contains all requested timing fields.
  - `final-summary.md` contains the slow target, required failure, optional failure, bridge recovery, and session/cache sections.
  - Slow target causes were visible without logs: `kernel32_dll` was dominated by `session_check`; `notepad_exe` was dominated by `analyzer`.
- Status: passed.
