# Campaign Start Summary

Status: initialized.

Baseline:
- Current canonical green Sponsor Demo E2E run:
  `24568108685`.
- Prior full stretch campaign reached the remote DCOM tranche and stopped
  truthfully because same-subnet client provisioning required additional Azure
  permissions.

Current blocker:
- Public-client DCOM reached remote COM activation but failed at RPC transport
  with `0x800706ba`.
- Same-subnet Azure client VM is the required next proof path.

Next prompt:
- Execute tranche `001-azure-dcom-unblock`.

Workflow quality evaluation:
- `gm_control_quality`: score 3. Evidence: this campaign narrows the blocker to
  one Azure permission/network frontier. Strongest risk: Azure permissions still
  missing. Next correction: stop with exact role/scope evidence if preflight
  fails.
- `context_pressure_result`: score 3. Evidence: Ghidra and unrelated stretch
  work are explicitly excluded. Strongest risk: old full-stretch campaign still
  mentions Ghidra. Next correction: use this campaign as canonical for the
  non-Ghidra path.
- `delegation_effectiveness`: score 2. Evidence: no subagents authorized or
  needed for campaign creation. Strongest risk: Azure proof may require focused
  operator review. Next correction: dispatch only if user authorizes.
- `operator_reviewability`: score 3. Evidence: tranche gates are artifact based
  and cite exact workflow/proof files. Strongest risk: cleanup failure could be
  hidden in workflow logs. Next correction: record cleanup artifact in tranche
  001/002 summaries.

Dispatch accountability:
- `roles_considered`: Azure workflow verifier, UI proof reviewer.
- `roles_dispatched`: none.
- `why_not_dispatched`: authorization_absent.
