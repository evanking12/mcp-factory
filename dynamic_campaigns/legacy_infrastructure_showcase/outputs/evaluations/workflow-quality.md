# Workflow Quality Evaluation

## 007 Closeout

`gm_control_quality`: 3

Evidence: tranche order stayed bounded; focused protocol runs were used before
the full E2E gate.

Strongest risk: initial parallel dispatch caused two queued runs to be
cancelled by workflow scheduling behavior.

Next correction: dispatch focused sponsor workflows sequentially when they share
the bridge VM concurrency group.

`context_pressure_result`: 3

Evidence: artifact parsing used `final-summary.json` and `final-summary.md`
instead of relying on chat memory.

Strongest risk: older campaign closeouts still reference historical green runs.

Next correction: treat those as historical records and keep public proof links
in README/proof-index/current campaign aligned to the newest canonical run.

`delegation_effectiveness`: 2

Evidence: no subagents were used; the work was operationally sequential and
critical-path oriented.

Strongest risk: manual workflow monitoring can miss hidden artifact regressions.

Next correction: continue downloading and parsing canonical artifacts before
writing closeout.

`operator_reviewability`: 3

Evidence: closeout records the canonical run, focused workflow URLs, artifact
paths, proof levels, and caveat boundaries.

Strongest risk: sponsor readers may still need the caveat page when discussing
CORBA, RPC, JNDI, or DCOM.

Next correction: keep `docs/sponsor/caveats.md` linked from README and proof
index.
