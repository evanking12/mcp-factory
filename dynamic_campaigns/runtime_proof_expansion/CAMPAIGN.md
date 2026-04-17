# Runtime Proof Expansion And Sponsor Demo Hardening

## Goal

Produce a latest canonical green `Sponsor Demo E2E` run that proves the capstone
requirements through discovery, MCP/OpenAI schema generation, GPT-4o
`tool_call`, backend `tool_result`, downloadable artifacts, Windows proof
summaries, repo-ingestion proof, and a requirement matrix.

## Sequential Rules

- Work strictly in tranche order.
- Do not advance while a tranche has failing focused tests or missing evidence.
- Write tranche status with the exact artifacts, tests, commits, and run URLs.
- Preserve the existing green sponsor path while adding incremental evidence.
- Every bug found during a tranche is either fixed before moving on or recorded
  as a blocker with evidence.

## Tranche Gates

1. `001-verify-current-green`: verify the current baseline and establish the
   canonical proof gate.
2. `002-soap-runtime`: promote SOAP to SOAP envelope/runtime proof.
3. `003-sql-runtime`: promote SQL to SQLite-backed deterministic runtime proof.
4. `004-rest-validation`: validate REST/OpenAPI path and method contracts.
5. `005-jndi-rpc-runtime`: add JNDI lookup runtime and XML-RPC-style RPC proof;
   keep CORBA adapter-backed unless a verified emulator is low risk.
6. `006-ui-demo-mode`: expose the CI-equivalent proof path in the UI.
7. `007-proof-portal-closeout`: update reports, docs, run focused workflows,
   run full E2E, and write closeout.

## Final Acceptance

- Full Sponsor Demo E2E is green.
- GPT format matrix is `13/13`.
- Repo ingestion proof passes.
- Windows GPT proof is `5/5`.
- SOAP and SQL are reported as runtime-backed.
- Final report separates `real_runtime`, `validated_runtime`,
  `lookup_runtime`, `xmlrpc_runtime`, `adapter_backed`,
  `repo_live_execution`, `tool_result_observed`, and manual/process proof.
- UI demo mode uses `/api/analyze`, `/api/analyze-path`, `/api/generate`,
  `/api/chat`, and `/api/download/{job_id}/{filename}`.
- Worktree is clean after commit and push.

