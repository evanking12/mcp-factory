# Architect Brief: Non-Ghidra Stretch Closeout

The campaign should not continue the full-stretch Ghidra branch. The practical
frontier is Remote DCOM, because LDAP/JNDI, CORBA ORB/IIOP, and controlled MSRPC
already have focused runtime proofs.

The prior public-client DCOM attempt is not a viable passing path. It reached
remote COM activation but failed with RPC transport unavailable. The next
truthful proof must run from a Windows client in the bridge VM VNet/subnet, or
from an explicitly supplied equivalent client VM.

The final sponsor claim is allowed only after the focused DCOM artifact and a
new full Sponsor Demo E2E artifact both pass.
