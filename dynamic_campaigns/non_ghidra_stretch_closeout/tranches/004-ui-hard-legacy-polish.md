# Tranche 004: UI Hard Legacy Polish

Class: `bounded_fix`

Primary question: does the UI make the hard legacy proof story clear enough for
the video demo?

Actions:

- Surface `ldap_runtime`, `corba_orb_runtime`, `msrpc_runtime`, and
  `remote_dcom_runtime` in the hard legacy proof panel.
- Keep app downloads on `/api/download/{job_id}/{filename}`.
- Keep GitHub Actions proof artifacts clearly labeled as the CI proof bundle.
- Preserve the recommended video order: SOAP/WSDL walkthrough, proof matrix,
  then one hard legacy card.

Passing criteria:

- Static UI tests find all runtime-mode labels and the CI/app artifact
  distinction.
- Deployed UI health is `200` after deploy.
- UI copy does not claim arbitrary enterprise migration or perfect binary
  recovery.
