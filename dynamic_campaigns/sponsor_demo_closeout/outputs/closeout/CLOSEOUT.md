# Sponsor Demo Closeout

Status: closed with canonical green run

## Canonical Run

- URL: `https://github.com/evanking12/mcp-factory/actions/runs/24541068734`
- Artifact: `sponsor-demo-e2e`
- Downloaded artifact path: `C:\Users\evanw\AppData\Local\Temp\sponsor-demo-e2e-24541068734`

## Required Artifact Paths

- `final-summary.md`
- `final-summary.json`
- `windows/summary.json`
- `gpt-format-matrix/summary.json`
- `gpt4o/transcript.json`
- `gpt4o/selected-invocable.json`
- `gpt4o/generated-mcp-schema.json`
- `gpt4o/downloaded-mcp-schema.json`

## Known Risks

- `cmd_exe` remains optional diagnostic because deterministic `.cmd` is the required CMD/BAT proof.
- Bridge VM recovery can still be slow when Azure Run Command or VM restart is involved.
- Process requirement 7 is documented as process evidence, not CI-verifiable runtime behavior.

## UI/Backend Verification

- Local/static route alignment passed.
- Final deployed proof passed in Sponsor Demo E2E run `24541068734`.
- Backend download proof passed through `gpt4o/downloaded-mcp-schema.json`.
- UI route alignment passed for upload, installed path, polling, generation, chat stream, and `/api/download/{job_id}/{filename}`.

## Final Artifact Verification

- `final-summary.json`: `passed=true`.
- Checks passed: non-VM formats, required Windows targets, GPT format matrix, GPT tool call, sentinel result, generated schema, downloaded schema, job history, VM deallocation.
- Requirement matrix rows: 16.
- Live execution cases: Python, JavaScript, Ruby, PHP, PowerShell, CMD/BAT.
- Provider-required cases: OpenAPI, JSON-RPC, SOAP/WSDL, CORBA IDL, RPC IDL, JNDI, SQL.
- MCP/LLM proof story: passed.
- Windows diagnostics:
  - `kernel32_dll`: slow because `session_check` dominated.
  - `notepad_exe`: slow because `analyzer` dominated.
  - `cmd_exe`: optional diagnostic, passed.
