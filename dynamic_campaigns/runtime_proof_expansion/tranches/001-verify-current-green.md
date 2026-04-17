# Tranche 001: Verify Current Green

## Objective

Verify the baseline after `73c8b80` and establish the current green proof gate.

## Required Work

- Confirm local static checks pass.
- Confirm sponsor fixture contract passes.
- Rerun or inspect full `Sponsor Demo E2E` on `73c8b80` or newer.
- Preserve run `24542583216` as historical fallback until a newer full green run
  exists.

## Passing Criteria

- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py ui/main.py`
- `python scripts/ci_verify.py run-sponsor-contract --out <tmp>`
- Contract CI green for the commit being promoted.
- Campaign writeback records the run URL, artifact name, status, and blockers.

## Writeback

Status: local gate passed.

- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py ui/main.py` passed.
- `python scripts/ci_verify.py run-sponsor-contract --out ci_artifacts\tmp-runtime-proof-contract` passed with 13 sponsor cases.
- `python -m pytest -q` passed with 34 passed, 5 skipped.
- Historical green fallback remains Sponsor Demo E2E run `24542583216` until the new full run is green.
