# 002 Demo Readiness Workflow

- Class: `bounded_fix`
- Primary question: can GitHub Actions answer "can I record the video now?"
  with a lightweight workflow?
- Gate:
  - `demo-readiness.yml` runs UI smoke, provider smoke, operational proof, and
    uploads `demo-readiness-summary.json`.
  - The workflow does not start the bridge VM or call GPT.

