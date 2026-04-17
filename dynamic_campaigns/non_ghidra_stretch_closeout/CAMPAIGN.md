# Non-Ghidra Stretch Closeout

## Campaign Start Packet

- `wider_goal`: finish the non-Ghidra stretch path with a truthful
  artifact-backed final sponsor claim.
- `current_frontier`: controlled remote DCOM activation from a same-subnet Azure
  Windows client.
- `stop_gate`: latest full Sponsor Demo E2E green with remote DCOM promoted to
  `remote_dcom_runtime=passed` and UI/docs pointing at that run.
- `dominant_blocker`: public GitHub-hosted client DCOM fails at RPC transport;
  same-subnet client creation was previously blocked by OIDC network/VM
  permissions.
- `expected_delivery_or_proving_target`: focused
  `sponsor-remote-dcom-runtime` artifact followed by full `sponsor-demo-e2e`
  artifact.
- `delegation_authorization`: absent. Keep work local unless the user
  explicitly authorizes subagents.
- `operator_constraints`:
  - `time_budget`: use focused DCOM workflow before any full E2E rerun.
  - `merge_or_push_expectation`: commit/push only after campaign surfaces and
    checks are current.
  - `allowed_risk_level`: temporary Azure client VM is allowed; delete temporary
    resources after proof.
- `required_outputs`: active prompt, tranche summaries, evaluations, dispatch
  accountability, architect briefs, blocker/system writeback if permissions
  fail, and closeout after final green.

## Tranches

1. `001-azure-dcom-unblock` (`blocker_localization`): verify OIDC can read the
   bridge VM NIC/subnet and create/delete a temporary same-subnet Windows client
   VM. If not, stop with exact missing permission evidence.
2. `002-same-subnet-remote-dcom-proof` (`bounded_fix`): run the focused DCOM
   proof with `--client-mode azure-vm`, upload the remote activation transcript,
   generated schema, GPT transcript, and summary artifact.
3. `003-report-proof-promotion` (`bounded_fix`): promote DCOM from blocked to
   passed in final reports, proof index, README, and caveats only after tranche
   002 passes.
4. `004-ui-hard-legacy-polish` (`bounded_fix`): make the UI hard-legacy panel
   show LDAP, CORBA ORB/IIOP, MSRPC, and Remote DCOM runtime modes, while
   keeping app downloads separate from CI artifacts.
5. `005-final-sponsor-e2e` (`authoritative_validation`): run the full Sponsor
   Demo E2E, parse artifacts, and require all non-Ghidra stretch proofs.
6. `006-closeout-video-claim` (`closeout`): write the final claim, artifact
   paths, video walkthrough order, remaining truthful boundaries, and campaign
   closeout.

## Boundaries

- Do not silently downgrade remote DCOM to local COM automation.
- Do not use public-client DCOM as a passing proof.
- Do not touch Ghidra or binary recovery.
- Do not claim arbitrary enterprise estate migration.
- CI artifacts, not chat memory, determine progress.
