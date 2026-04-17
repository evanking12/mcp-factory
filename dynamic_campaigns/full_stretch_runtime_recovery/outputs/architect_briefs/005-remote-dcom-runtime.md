# Architect Brief: 005 Remote DCOM Runtime

Decision:
- Prove remote DCOM with a temporary Azure Windows client VM in the same subnet
  as the existing bridge VM, using the built-in `WScript.Shell` COM server as a
  controlled fixture.

Why:
- Remote DCOM must be activated from a distinct context. Azure Run Command on
  the bridge VM is not enough because it is local execution. A temporary client
  VM gives a real remote Windows client while keeping the proof disposable and
  bounded.
- The workflow provisions and deletes the client VM in one run to limit cost and
  avoid leaving broad DCOM exposure around.

Trust boundary:
- Allowed claim after workflow proof: controlled remote DCOM activation and
  method invocation for a deterministic COM fixture between Azure Windows
  contexts.
- Disallowed claim: arbitrary enterprise DCOM estate support, migration of
  unknown COM servers, or broad DCOM security posture.

Next blocker:
- Validate whether Azure subnet rules, Windows firewall, local-account DCOM
  authentication, and WScript.Shell remote activation work together. If not,
  stop here and write a blocker with the exact failing layer.
