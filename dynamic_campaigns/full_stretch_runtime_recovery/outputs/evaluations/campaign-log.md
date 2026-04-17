# Campaign Log

## 004 MSRPC Runtime

Local implementation and authoritative workflow validation are complete.
Focused MSRPC runtime proof passed in run `24572152040`; focused
`rpc_idl_contract` GPT proof passed in run `24572186312`.

The active frontier advances to `005-remote-dcom-runtime`.

Baseline fallback remains Sponsor Demo E2E run `24568108685`.

## 005 Remote DCOM Runtime

Local implementation is ready, but authoritative workflow validation is blocked.
The current frontier remains `005-remote-dcom-runtime`; do not advance to Ghidra
or later tranches until a real remote DCOM path is available or the user
explicitly changes the stretch requirement.

Run `24572666172` failed before DCOM activation because the OIDC identity could
not read the bridge VM NIC for same-subnet client provisioning. The next attempt
uses a GitHub-hosted Windows client context instead of provisioning a temporary
Azure VM.

Run `24573214799` reached real remote COM activation from a distinct
GitHub-hosted Windows client and failed with `0x800706ba` RPC server unavailable
against `20.124.33.45`. This indicates the public DCOM/RPC transport is blocked
or unroutable. Same-subnet client provisioning remains blocked by missing
network-interface read permission for the GitHub OIDC identity.
