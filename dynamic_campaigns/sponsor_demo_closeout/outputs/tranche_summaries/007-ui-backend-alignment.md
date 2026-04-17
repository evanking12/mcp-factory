# Tranche 007: UI Backend Alignment

Status: local gate passed

## Audit Result

Backend routes are present for upload, installed path, job polling, generation, chat streaming, and downloads:

- `/api/analyze`
- `/api/analyze-path`
- `/api/jobs/{job_id}`
- `/api/generate`
- `/api/chat`
- `/api/download/{job_id}/{filename}`

The UI proxies `/api/chat/stream` to backend `/api/chat` and uses the same download route shape as the backend.

## Fixes

- Invocable rows now display source type, execution method, confidence/tier, and proof status.
- Provider-required and live-execution status are shown from invocable metadata/source type.
- Installed-path wording matches the backend/VM execution context caveat.
- Download URL now derives the filename from the backend `schema_blob` when available and calls `/api/download/{job_id}/{filename}`.

## Evidence

- `python -m py_compile scripts\ci_verify.py scripts\gui_bridge.py ui\main.py api\main.py` passed.
- `python -m pytest tests\test_ci_verify_sponsor_summary.py tests\test_ci_verify_bridge_cache.py -q` passed: 16 tests.

Status: local gate passed; final deployed behavior remains covered by the Sponsor Demo E2E artifact rerun and backend download proof.
