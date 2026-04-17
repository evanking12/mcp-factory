# Legacy Provider Live Green Closeout

## Canonical Green Proof

- Sponsor Demo E2E run: https://github.com/evanking12/mcp-factory/actions/runs/24542583216
- Artifact name: `sponsor-demo-e2e`
- Commit: `6c60c51`

## Acceptance Results

- Final summary passed: `true`
- GPT matrix: `13/13` live execution format proofs
- Required provider-required cases: `0`
- Windows required targets: `6/6`
- `sponsor-report.html`: uploaded in the artifact
- UI proof bundle affordance: deployed through Deploy UI run `24542374460`
- Pipeline legacy providers: deployed through Deploy Pipeline run `24542374466`

## Evidence Paths

- `ci_artifacts/demo/final-summary.json`
- `ci_artifacts/demo/final-summary.md`
- `ci_artifacts/demo/sponsor-report.html`
- `ci_artifacts/demo/gpt-format-matrix/summary.json`
- `ci_artifacts/demo/windows/summary.json`
- `ci_artifacts/demo/gpt4o/transcript.json`

## Fast Iteration Paths

- `skip_windows_targets=true`
- `skip_gpt_matrix=true`
- `only_windows_target=<label>`
- `only_gpt_case=<case_id>`
- `report_only_run_id=<run_id>`
- `Sponsor Demo Report Only` workflow
- `Sponsor Report Fixture` workflow

## Remaining Risks

- Legacy CORBA/RPC/JNDI providers are adapter-backed deterministic services, not production protocol servers.
- Windows bridge health remains dependent on the VM launching the bridge in interactive Session 1.
- Slow target diagnostics still show `kernel32_dll` and `notepad_exe` as comparatively slow, but they now pass and are classified in the final report.
