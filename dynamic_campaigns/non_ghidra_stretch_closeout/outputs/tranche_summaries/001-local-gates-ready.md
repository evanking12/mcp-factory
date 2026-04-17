# Tranche 001 Local Checkpoint

Status: local implementation ready; remote proof not yet dispatched.

Implemented:
- Focused Remote DCOM workflow now uses same-subnet Azure client VM mode.
- Full Sponsor Demo E2E accepts `remote_dcom_run_id` and imports the focused
  `sponsor-remote-dcom-runtime` artifact.
- Final Sponsor Demo summary can require Remote DCOM with
  `--require-remote-dcom`.
- UI hard legacy proof panel names `remote_dcom_runtime`.

Gate expectation:
- Local gates must pass before commit.
- Focused Remote DCOM workflow is the next authoritative gate.
- Full Sponsor Demo E2E must be run only after a passing focused DCOM run ID is
  available.

Truth boundary:
- Remote DCOM is still not claimed as passed until the focused workflow artifact
  has `passed=true`, `runtime_mode=remote_dcom_runtime`,
  `remote_dcom_activation_claimed=true`, and GPT tool-call/tool-result proof.

Workflow quality evaluation:
- `gm_control_quality`: score 3. Evidence: full E2E now fails if required
  Remote DCOM evidence is missing. Strongest risk: focused artifact download
  layout varies. Next correction: normalize downloaded DCOM directory in the
  workflow.
- `context_pressure_result`: score 3. Evidence: Ghidra remains excluded and the
  proof path is bounded to Remote DCOM. Strongest risk: older campaign docs may
  mention binary recovery. Next correction: keep this campaign canonical for
  non-Ghidra closeout.
- `delegation_effectiveness`: score 2. Evidence: no subagents authorized.
  Strongest risk: Azure permission failure may need operator review. Next
  correction: use focused workflow logs as role-scope evidence.
- `operator_reviewability`: score 3. Evidence: tests lock workflow mode,
  cleanup artifacts, and final summary requirement behavior. Strongest risk:
  Azure cleanup status is coarse. Next correction: inspect cleanup artifact after
  focused run.

Dispatch accountability:
- `roles_considered`: Azure workflow verifier, report contract reviewer.
- `roles_dispatched`: none.
- `why_not_dispatched`: authorization_absent.
