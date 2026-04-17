# 003 CORBA ORB/IIOP Runtime

Class: `bounded_fix`

Status: pending.

Goal: replace CORBA IDL runtime-shaped proof with a real ORB/IIOP controlled
proof.

Required artifacts:
- `ci_artifacts/demo/legacy/corba_orb/contoso_support.idl`
- generated stub metadata
- `ci_artifacts/demo/legacy/corba_orb/orb-server.log`
- object reference or naming registration proof
- `ci_artifacts/demo/legacy/corba_orb/client-invocation.json`
- `ci_artifacts/demo/gpt-format-matrix/corba_idl/transcript.json`

Gate:
- GPT calls a generated CORBA tool.
- Backend returns a result from real ORB/IIOP invocation.
- Final summary reports `runtime_mode=corba_orb_runtime`.

