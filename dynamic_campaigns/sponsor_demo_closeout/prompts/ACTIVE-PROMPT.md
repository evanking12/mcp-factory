# Active Prompt: 002-diagnostics

Add diagnosable timing and recovery evidence to Windows target summaries and final sponsor markdown.

## Required Work

- Add top-level timing breakdown fields to each Windows target summary:
  - `health_wait_seconds`
  - `session_check_seconds`
  - `session_cache_used`
  - `bridge_analyzer_seconds`
  - `retry_seconds`
  - `restart_seconds`
  - `vm_restart_seconds`
  - `post_grace_seconds`
  - `timeout_or_failure_classification`
- Add final markdown sections for slow targets, optional failures, required failures, bridge recovery events, and session/cache proof.
- Classify optional diagnostics clearly.

## Passing Criteria

- `python -m py_compile scripts/ci_verify.py scripts/gui_bridge.py`
- focused diagnostics tests pass.
- Target summaries explain `cmd_exe` and `notepad_exe` wall time without reading raw logs.
- Final summary says whether slowness came from analyzer time, bridge recovery, VM restart, or timeout.
- Campaign tranche `002-diagnostics` is written.
