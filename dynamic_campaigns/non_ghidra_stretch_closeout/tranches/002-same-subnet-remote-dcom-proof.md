# Tranche 002: Same-Subnet Remote DCOM Proof

Class: `bounded_fix`

Primary question: can a distinct same-subnet Windows client remotely activate
and invoke the controlled DCOM fixture on the bridge VM?

Actions:

- Run `sponsor-remote-dcom-runtime.yml` with `--client-mode azure-vm`.
- Let `windows-remote-dcom-runtime-proof` resolve the bridge VM private IP.
- Generate a proof-only DCOM credential and deterministic sentinel.
- Upload DCOM summary, remote activation transcript, generated schema, and GPT
  transcript.

Passing criteria:

- `ci_artifacts/demo/windows/dcom/dcom.summary.json` has `passed=true`.
- `runtime_mode=remote_dcom_runtime`.
- `remote_dcom_activation_claimed=true`.
- Client and server computer names are distinct.
- Remote sentinel read matches the proof sentinel.
- GPT sees `tool_call` and backend `tool_result`.

Do not downgrade to local COM or public-client DCOM.
