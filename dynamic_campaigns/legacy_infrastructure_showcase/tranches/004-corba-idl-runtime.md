# 004 CORBA IDL Runtime-Shaped Proof

Status: implemented.

Gate:
- Provider health reports `corba_idl_runtime`.
- Known IDL interface operations return repository ID, object reference, and
  `NO_EXCEPTION` response metadata.
- Unknown operations are rejected.
- Caveat remains: this is not production CORBA ORB/IIOP.

