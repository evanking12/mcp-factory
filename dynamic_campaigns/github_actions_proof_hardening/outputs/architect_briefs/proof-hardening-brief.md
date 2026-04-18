# Architect Brief: Proof Hardening

The campaign hardens the current sponsor proof without expanding scope. The
main design choice is to reuse `scripts/ci_verify.py` for all CI assertions so
workflow behavior, report-only behavior, and local tests share one verifier.

The new checks are intentionally light: deployed smoke paths do not call GPT and
do not start the Windows bridge VM. Full authority still belongs to Sponsor Demo
E2E plus proof-integrity validation against its artifact.

