# 003 LDAP/JNDI

Status: implemented.

Gate:
- Provider health reports `ldap_jndi_runtime`.
- `/api/legacy/jndi/bind` validates deterministic Contoso principals.
- `/api/legacy/jndi/search` returns deterministic LDAP-style entries.
- `/api/legacy/jndi/lookup` returns binding plus LDAP entry metadata.

