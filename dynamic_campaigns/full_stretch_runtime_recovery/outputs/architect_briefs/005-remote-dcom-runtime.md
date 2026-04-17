# Architect Brief: 005 Remote DCOM Runtime

Decision:
- Prove remote DCOM from a distinct GitHub-hosted Windows client context against
  the existing bridge VM public endpoint, using the built-in `WScript.Shell` COM
  server as a controlled fixture.

Why:
- Remote DCOM must be activated from a distinct context. Azure Run Command on
  the bridge VM is not enough because it is local execution.
- The first temporary same-subnet client VM approach failed before DCOM because
  the OIDC identity lacks `Microsoft.Network/networkInterfaces/read` on the
  bridge VM NIC. A GitHub-hosted Windows runner is still a distinct remote
  Windows client and avoids provisioning extra Azure resources.
- The command configures proof-only server state, runs the remote client, then
  removes the proof-only user, firewall rules, and sentinel registry key.

Trust boundary:
- Allowed claim after workflow proof: controlled remote DCOM activation and
  method invocation for a deterministic COM fixture from a distinct Windows
  client context.
- Disallowed claim: arbitrary enterprise DCOM estate support, migration of
  unknown COM servers, or broad DCOM security posture.

Next blocker:
- Validate whether public endpoint routing, Windows firewall, local-account DCOM
  authentication, and WScript.Shell remote activation work together. If not,
  stop here and write a blocker with the exact failing layer.
