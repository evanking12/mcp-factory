# Tranche 001: Stabilize Sponsor Report

Status: passed

## Blocker

Run `24538695310` reached the final summary with non-VM formats, GPT matrix, deterministic CMD/BAT execution, schema generation, chat tool call, download, and VM deallocation all passing. The final gate failed because broad scanning of `C:\Windows\System32\cmd.exe` was treated as required even though it produced zero invocables and is not the canonical CMD/BAT requirement proof.

## Fix Intent

Reclassify broad `cmd.exe` scanning as an optional diagnostic target. Keep deterministic `.cmd` fixture and GPT CMD proof required.

## Evidence To Fill

- Test results:
  - `python -m py_compile scripts\ci_verify.py scripts\gui_bridge.py` passed.
  - `python scripts\ci_verify.py bridge-target-e2e --help` passed.
  - `python scripts\ci_verify.py direct-bridge-e2e --help` passed.
  - `python -m pytest tests\test_ci_verify_sponsor_summary.py tests\test_ci_verify_bridge_cache.py -q` passed: 9 tests.
- Local proof:
  - Optional Windows diagnostic failure no longer fails `summarize-sponsor-demo`.
  - Required Windows failure still fails `summarize-sponsor-demo`.
  - `summarize-bridge-e2e` records optional failures separately without blocking required-target success.
- Rerun URL: `https://github.com/evanking12/mcp-factory/actions/runs/24539841674`
- Artifact path: GitHub Actions artifact `sponsor-demo-e2e`, downloaded locally to `C:\Users\evanw\AppData\Local\Temp\sponsor-demo-e2e-24539841674`
- Final status:
  - `final-summary.json` has `passed=true`.
  - Required Windows targets: 6/6 passed.
  - Optional diagnostics: 1/1 passed.
  - GPT matrix: 13/13 passed.
  - Real execution proofs: 6/6.
  - Provider-required tool-call proofs: 7/7.
