# 004 Runtime Downgrade And Caveat Guards

- Class: `bounded_fix`
- Primary question: can CI fail when a green-looking report silently weakens
  runtime proof or overclaims sponsor scope?
- Gate:
  - Runtime modes for JSON-RPC, SOAP, SQL, REST, JNDI, CORBA, RPC, and Remote
    DCOM are enforced when required.
  - README, proof index, caveats, and reports keep truthful boundaries.

