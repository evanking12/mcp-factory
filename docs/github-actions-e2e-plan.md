# GitHub Actions E2E Plan

Purpose: keep the sponsor-scope verification plan explicit and close to the repo so the project can recover quickly after Azure or VM drift.

## Goals

- Verify the required project flow: binary or executable input -> discovery -> invocable selection -> MCP generation -> chat/tool execution -> downloadable artifact.
- Keep normal CI cheap.
- Run expensive Windows/GPT-4o checks only on demand, before demos, or on `main`.
- Keep the Windows bridge VM off by default and start it only when a workflow or cloud scan needs Windows-only analysis.

## Workflow Tiers

### Tier 1: Cheap Contract CI

Trigger:
- Pull requests.
- Pushes to `main`.

Runner:
- GitHub-hosted `ubuntu-latest` and/or `windows-latest`.

Coverage:
- Unit tests.
- Schema validation.
- Discovery for non-VM sponsor formats:
  - OpenAPI / Swagger.
  - JSON / JSON-RPC.
  - WSDL / SOAP.
  - CORBA IDL.
  - JNDI configs.
  - SQL files.
  - Python, JavaScript, Ruby, PHP, PowerShell, Batch/CMD fixture scripts where no GUI session is needed.
- MCP schema generation from fixture invocables.

Success criteria:
- Analyzer exits successfully.
- Invocable count is greater than zero for each required fixture.
- Generated MCP schema validates.
- Required fields exist: `name`, `kind`, `confidence`, `description`, `parameters`, `execution`.
- Artifacts are uploaded to the workflow run.

### Tier 2: Windows Bridge E2E

Trigger:
- `workflow_dispatch`.
- Optional scheduled demo-readiness run.
- Optional `main` only, never every PR.

Runner:
- Self-hosted Windows runner on the Azure VM, or GitHub workflow starts the VM and waits for bridge health.

Coverage:
- DLL scan.
- EXE scan.
- CMD/CLI scan.
- COM/DCOM scan.
- Registry scan.
- Installed path scan.
- GUI automation through pywinauto.
- Ghidra recovery if Ghidra is installed on the VM.

Success criteria:
- VM starts successfully.
- Bridge `/health` returns OK.
- Each Windows target produces invocables.
- Generated MCP schema exists and validates.
- For GUI targets, an external state check passes, not just a model response.

Recommended targets:
- `C:\Windows\System32\kernel32.dll` for DLL.
- `C:\Windows\System32\cmd.exe` for CMD/CLI.
- `C:\Windows\System32\notepad.exe` for EXE/GUI.
- `shell32.dll` or `stdole2.tlb` for COM/TLB.
- A small installed directory fixture for directory/repo scan.

### Tier 3: GPT-4o Tool-Call E2E

Trigger:
- Manual `workflow_dispatch`.
- Before sponsor demos.

Coverage:
- Full path: upload target -> analyze -> generate MCP -> chat prompt -> GPT-4o tool call -> verify tool result.

Deterministic prompts:
- CLI: "Run the help or version command and summarize the first line."
- Notepad: "Open Notepad and type MCP_FACTORY_E2E_<run_id>."
- Calculator: "Compute 12 + 30."

Success criteria:
- GPT emits at least one tool call.
- Tool execution returns success.
- External observable state matches the expected sentinel:
  - CLI stdout contains expected token or exit code is `0`.
  - Notepad text contains `MCP_FACTORY_E2E_<run_id>`.
  - Calculator result equals expected value.
- Blob artifacts exist.
- Transcript is stored as a workflow artifact.
- Logs contain no storage, bridge, or OpenAI error.

## Azure VM Cost Control

The Windows VM should not run continuously.

On-demand behavior:
- Start VM only when Windows-only analysis is required.
- Poll bridge `/health`.
- Run analysis or tests.
- Deallocate after workflow completion.
- For cloud app scans, deallocate after an idle window, for example 15 to 30 minutes.

Required Azure permission:
- The pipeline managed identity or GitHub OIDC identity needs VM start/deallocate permissions scoped to `mcpfactory-runner-vm`.
- Prefer narrow scope over resource-group-wide permissions.

## Proposed Workflow Files

- `.github/workflows/contract-ci.yml`
  - Cheap sponsor-format contract checks.
- `.github/workflows/windows-bridge-e2e.yml`
  - Manual Windows VM/bridge verification.
- `.github/workflows/gpt4o-tool-e2e.yml`
  - Manual full MCP + GPT-4o tool-call verification.

## Immediate Implementation Order

1. Add fixture-level contract tests for the sponsor formats.
2. Add `contract-ci.yml` for cheap checks.
3. Repair the Windows VM bridge and make bridge health deterministic.
4. Add manual `windows-bridge-e2e.yml`.
5. Add manual `gpt4o-tool-e2e.yml`.
6. Add VM on-demand start/deallocate logic to the cloud pipeline.

