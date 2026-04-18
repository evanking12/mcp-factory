# 001 Deployed Smoke Gates

- Class: `bounded_fix`
- Primary question: can CI verify the public UI and deployed provider runtime
  surface without running full Sponsor Demo E2E?
- Gate:
  - `deployed-ui-smoke` passes against the public UI.
  - `deployed-provider-matrix-smoke` passes with the pipeline API key.
  - Mocked local tests cover success paths.

