# Tranche 007 Summary

Tranche class: `closeout`

Primary question: does the new legacy infrastructure showcase proof have a
single green canonical GitHub Actions artifact?

Answer: yes.

Evidence:
- Full Sponsor Demo E2E: https://github.com/evanking12/mcp-factory/actions/runs/24568108685
- Artifact: `sponsor-demo-e2e`
- `final-summary.json` reports `passed=true`.
- GPT matrix: `13/13`, provider-required required cases `0`.
- Runtime modes present: `real_runtime`, `validated_runtime`, `local_runtime`,
  `ldap_jndi_runtime`, `xmlrpc_runtime`, `corba_idl_runtime`.
- Windows GPT matrix: `5/5`.
- Repo ingestion proof passed.
- Local COM automation proof passed with `runtime_mode=com_runtime`.

Next correction: none for this campaign. Future maintenance should address the
GitHub Actions Node.js 20 deprecation warning before enforcement dates.
