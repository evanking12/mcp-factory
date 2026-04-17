# 005 COM/DCOM Surface

Status: implemented in workflow and CI helper.

Gate:
- `windows-com-runtime-proof` runs PowerShell local COM automation on the
  Windows VM.
- Summary records `com_runtime`, `local_com_automation`, COM objects, sentinel,
  and `remote_dcom_activation_claimed=false`.
- Caveat remains: remote DCOM activation is not claimed.

