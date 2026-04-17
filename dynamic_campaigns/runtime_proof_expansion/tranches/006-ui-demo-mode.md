# Tranche 006: UI Demo Mode

## Objective

Make the deployed UI support a clean sponsor walkthrough using the same backend
path that CI verifies.

## Required Work

- Add `Load Demo Target`.
- Add `Run Canonical Proof`.
- Show visible `tool_call:` and `tool_result:` transcript entries.
- Keep app downloads on `/api/download/{job_id}/{filename}`.
- Keep GitHub Actions proof artifacts clearly separate from app downloads.

## Passing Criteria

- Static UI tests confirm the demo controls, backend routes, and download path.
- Manual or deployed-route walkthrough confirms badges and transcript labels are
  readable.

## Writeback

Status: local static gate passed.

- UI now includes `Load Demo Target` and `Run Canonical Proof` controls.
- Demo mode uses a browser-generated Python fixture and the existing
  `/api/analyze`, `/api/generate`, `/api/chat`, and
  `/api/download/{job_id}/{filename}` routes.
- Chat transcript rendering labels visible proof events as `tool_call:` and
  `tool_result:`.
- Static UI tests assert the demo controls, proof labels, CI proof bundle copy,
  and backend download path.
