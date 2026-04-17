# Tranche 004 - UI Proof Bundle

## Goal

Add a UI affordance that points sponsors to the CI proof bundle while keeping
application downloads clearly bound to `/api/download/{job_id}/{filename}`.

## Evidence To Write

- Static UI/backend alignment test passes.
- UI copy distinguishes CI proof bundle from app artifact downloads.

## Local Evidence

- Added header-level `CI Proof Bundle` link in `ui/main.py`.
- Clarified provider-required as fallback only in UI badges.
- Kept application downloads on `/api/download/{job_id}/{filename}`.
- Static UI/backend alignment test passes.

## Status

Complete locally; deployed UI visual check pending after push/deploy.
