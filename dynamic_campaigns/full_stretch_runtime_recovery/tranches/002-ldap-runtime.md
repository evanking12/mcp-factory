# 002 LDAP/JNDI Real Runtime

Class: `bounded_fix`

Status: pending.

Goal: replace LDAP/JNDI-shaped proof with a real LDAP-compatible runtime proof.

Required artifacts:
- `ci_artifacts/demo/legacy/jndi_ldap/ldap-server-config.ldif`
- `ci_artifacts/demo/legacy/jndi_ldap/bind-result.json`
- `ci_artifacts/demo/legacy/jndi_ldap/search-result.json`
- `ci_artifacts/demo/gpt-format-matrix/jndi/transcript.json`

Gate:
- GPT calls a generated JNDI/LDAP tool.
- Backend returns a tool result from real LDAP bind/search/lookup.
- Final summary reports `runtime_mode=ldap_runtime`.

