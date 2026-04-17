# Tranche 005: Installed Path Proof

Status: local gate passed

## Blocker

Installed path and directory support is proven by `system32_directory`, but it needs to be visible in the final matrix, README, and UI with the correct caveat that the path must be accessible to the execution context.

## Fix Intent

Keep `system32_directory` as required proof for requirement `2.a` and align README/UI wording.

## Evidence To Fill

- Test results:
  - `python -m py_compile scripts\ci_verify.py scripts\gui_bridge.py ui\main.py` passed.
  - `python -m pytest tests\test_ci_verify_sponsor_summary.py tests\test_ci_verify_bridge_cache.py -q` passed: 14 tests.
- README wording: Sponsor Demo E2E section states uploaded files and installed paths/directories are supported, and installed paths must be accessible to the server or bridge VM context.
- UI wording: installed path field states the path must be accessible to the pipeline server or Windows bridge VM context.
- Status: local gate passed; final Actions artifact verification will occur on the next Sponsor Demo E2E rerun.
