# Tranche 001: Azure DCOM Unblock

Class: `blocker_localization`

Primary question: can GitHub OIDC create or use a same-subnet Windows client VM
for controlled remote DCOM?

Actions:

- Verify the workflow identity can read `mcpfactory-runner-vm`, its primary NIC,
  and the NIC subnet in `mcp-factory-rg`.
- Verify the identity can create a short-lived Windows client VM, NIC, OS disk,
  and Run Command operation in that subnet.
- Prefer a temporary client VM with no public IP and Standard_LRS disk.
- If permissions fail, record the exact failed Azure operation and required
  scope.

Passing criteria:

- Same-subnet client VM can be created or a pre-existing same-subnet client VM
  is supplied.
- Cleanup path can delete temporary VM, NIC, and disk.
- Campaign summary records permissions, subnet id, VM name strategy, and
  cleanup evidence.

Do not advance if this fails.
