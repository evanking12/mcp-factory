# Family Blocker Writebacks

## Unstable broad analyzer on `cmd.exe`

- Symptom: broad `C:\Windows\System32\cmd.exe` analysis previously ran for minutes, produced zero invocables, and could reset the bridge connection.
- Root issue: broad binary introspection of `cmd.exe` is not the deterministic proof required for CMD/BAT support.
- Policy: keep `cmd_exe` as optional diagnostic. Use the deterministic `.cmd` fixture and GPT CMD proof as required CMD/BAT evidence.
- Guardrail: final summary must distinguish required Windows failures from optional diagnostic failures.

## Bridge recovery and Azure Run Command conflict risk

- Symptom: bridge health/session checks can incur Azure Run Command overhead, especially when validating SessionId or recovering from Session 0.
- Root issue: Session 1 is mandatory for GUI/tool discovery, but Azure VM operations and scheduled task restarts are slow and can conflict.
- Policy: require SessionId `1`, cache proof by bridge URL + PID + creation date, and keep post-grace health/session verification.
- Guardrail: target summaries must record health wait, session check, restart, VM restart, retry, post-grace, and dominant time source.

## Fragmented requirement evidence

- Symptom: sponsor evidence was split across README, workflow logs, artifacts, GPT transcripts, and manual notes.
- Root issue: no single canonical artifact mapped requirement to proof and pass/fail.
- Policy: final summary JSON/markdown must include a requirement-to-proof matrix and proof semantics.
- Guardrail: every listed requirement needs evidence paths or an explicit process note.
