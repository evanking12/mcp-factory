# Architect Brief: 002 LDAP Runtime

Decision:
- Treat LDAP/JNDI as a controlled LDAPv3-compatible runtime proof, not a full
  enterprise directory deployment.

Why:
- The sponsor requirement names JNDI as a technology to consider. The stretch
  goal is stronger than the previous shaped lookup proof because bind/search and
  lookup now cross an LDAP BER/TCP boundary and produce focused artifacts.
- Pulling in OpenLDAP in the application container would increase deployment
  and operations risk for little sponsor value at this tranche. The current
  runtime remains deterministic, cheap, and artifact-backed.

Trust boundary:
- Allowed claim: controlled LDAP-compatible runtime proof for deterministic
  Contoso bindings.
- Disallowed claim: enterprise LDAP/JNDI infrastructure migration or arbitrary
  directory integration.

Next blocker:
- Prove the deployed pipeline image exposes `provider_modes.jndi=ldap_runtime`
  and focused LDAP artifacts before moving to CORBA ORB/IIOP.
