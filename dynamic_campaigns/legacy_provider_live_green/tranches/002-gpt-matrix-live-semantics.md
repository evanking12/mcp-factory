# Tranche 002 - GPT Matrix Live Semantics

## Goal

Convert the sponsor non-VM matrix so all 13 cases are live execution proofs.
Each case must observe GPT `tool_call`, GPT `tool_result`, downloaded schema,
and sentinel/result output.

## Evidence To Write

- Manifest shows `proof_level=real_execution` for all non-VM cases.
- Final summary reports `13/13` live execution format proofs and provider
  required total `0`.
- Focused summary tests pass.

## Local Evidence

- Updated sponsor manifest so all 13 non-VM cases use `proof_level=real_execution`.
- Added `--only-case` for targeted GPT matrix iteration.
- Updated final summary semantics and tests for `13/13` live execution and provider-required total `0`.
- Passing:
  - `python scripts/ci_verify.py run-sponsor-contract --out ci_artifacts\local-live-green\non-vm`
  - `python -m pytest -q`

## Status

Complete locally; full cloud GPT matrix pending after deploy.
