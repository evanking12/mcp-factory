# Active Prompt: 008-campaign-closeout

Write campaign closeout and durable blocker notes after final green Sponsor Demo E2E.

## Required Work

- Rerun Sponsor Demo E2E after all changes.
- Download and parse artifact.
- Record green run URL, artifact paths, known risks, optional diagnostics, and UI/backend verification.
- Add family-blocker writebacks for cmd.exe analyzer instability, bridge recovery/Azure Run Command risk, and fragmented requirement evidence.
- Update README Sponsor Demo section with canonical final run and artifact interpretation.

## Passing Criteria

- `python -m py_compile scripts/ci_verify.py scripts/gui_bridge.py`
- Campaign closeout exists.
- README references canonical final run and artifact model.
- GitHub Actions report is green and diagnosable.
- Worktree is clean after commit/push.
