# 005 Remote DCOM Runtime

Class: `bounded_fix`

Status: pending.

Goal: prove controlled remote DCOM activation/invocation from a distinct remote
context.

Required artifacts:
- COM registration proof with CLSID/AppID/ProgID
- DCOM launch/access permission proof
- `ci_artifacts/demo/windows/dcom/remote-activation-transcript.json`
- method invocation output
- VM/client logs
- GPT transcript

Gate:
- Remote activation and invocation succeed from a distinct machine or remote
  context.
- GPT calls a generated DCOM proof tool.
- Final summary reports `runtime_mode=remote_dcom_runtime`.

