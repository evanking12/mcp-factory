# Architect Brief

The campaign closed the remaining caveat-heavy proof story without introducing
fragile production infrastructure.

The final architecture now frames:
- JSON-RPC, SOAP, and SQL as runtime-backed.
- REST/OpenAPI as validated runtime.
- JNDI as LDAP/JNDI-shaped runtime.
- RPC IDL as XML-RPC runtime.
- CORBA IDL as runtime-shaped object registry dispatch.
- COM/DCOM as COM/TLB discovery plus local COM automation proof.

The remaining boundary is intentional: production CORBA ORB/IIOP, DCE/MSRPC,
enterprise LDAP/JNDI infrastructure, remote DCOM activation, and arbitrary
closed-source binary semantic recovery are not claimed.
