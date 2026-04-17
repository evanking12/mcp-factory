# Workflow Quality Evaluation

## 001 Proof Contract

`gm_control_quality`: 2

Evidence: the report contract is being extended before any hard runtime is
claimed.

Strongest risk: future implementers could mark a hard stretch proof passed
without the required focused artifacts.

Next correction: final summary must fail stretch closeout unless required
runtime artifacts and GPT transcripts exist.

`context_pressure_result`: 2

Evidence: the campaign records baseline run `24568108685` and required artifact
paths.

Strongest risk: full runtime work spans Azure, Windows, and optional toolchains.

Next correction: each hard runtime must write its own focused artifact before
full E2E.

`delegation_effectiveness`: 2

Evidence: no subagents were used because delegation was not authorized in this
turn.

Strongest risk: hard runtime work may benefit from parallel exploration later.

Next correction: only dispatch subagents if explicitly authorized.

`operator_reviewability`: 3

Evidence: tranche gates and public claim boundaries are explicit.

Strongest risk: sponsors may conflate controlled fixtures with arbitrary
enterprise estate migration.

Next correction: keep caveat language in proof index and final report.

## 002 LDAP Runtime

`gm_control_quality`: 2

Evidence: the implementation changes only the JNDI proof path and adds a
focused proof command/workflow before any CORBA/MSRPC/DCOM work.

Strongest risk: the local LDAP-compatible server is controlled and minimal, so
copy must not imply enterprise LDAP infrastructure.

Next correction: focused workflow artifact must record the LDIF, bind result,
search result, lookup result, and runtime matrix before tranche completion.

`context_pressure_result`: 2

Evidence: baseline run `24568108685` remains the fallback and the new LDAP
proof writes under `ci_artifacts/demo/legacy/jndi_ldap`.

Strongest risk: deployed ACA may still be on the previous image until deploy
finishes.

Next correction: wait for deploy, then run `sponsor-ldap-runtime.yml` and a
focused JNDI GPT matrix run.

`delegation_effectiveness`: 2

Evidence: no subagents were dispatched because the user did not explicitly
authorize delegation for this implementation turn.

Strongest risk: later CORBA/MSRPC/DCOM tranches may benefit from parallel
toolchain exploration.

Next correction: keep the critical path local unless the user explicitly
authorizes subagents.

`operator_reviewability`: 3

Evidence: tests cover provider health, LDAP endpoint wire metadata, LDIF
exposure, sponsor manifest mode validation, and report summaries.

Strongest risk: runtime naming drift between manifest, provider health, GPT
matrix, and final summary.

Next correction: focused artifact parsing must confirm `runtime_mode=ldap_runtime`.

## 003 CORBA ORB Runtime

`gm_control_quality`: 2

Evidence: the implementation adds a distinct CORBA proof command and workflow
instead of relabeling the previous object-registry provider.

Strongest risk: local Windows cannot execute the Linux OmniORB wheel, so local
validation cannot prove the ORB path.

Next correction: deployed focused workflow must prove `corba_orb_runtime`,
`wire_protocol=IIOP`, IOR object reference, server log, and client invocation.

`context_pressure_result`: 2

Evidence: the tranche writes expected artifacts under
`ci_artifacts/demo/legacy/corba_orb`.

Strongest risk: generated IDL module names or OmniORB binary path may differ
inside the deployed container.

Next correction: if focused workflow fails, inspect logs and patch the actual
generated/import path rather than downgrading to `corba_idl_runtime`.

`delegation_effectiveness`: 2

Evidence: no subagents were dispatched because this turn did not authorize
delegation.

Strongest risk: ORB troubleshooting may benefit from parallel package/runtime
exploration if it fails in CI.

Next correction: keep local unless explicitly authorized or the blocker becomes
toolchain-specific.

`operator_reviewability`: 2

Evidence: provider health, final summary modes, focused command, and workflow
have one runtime mode target: `corba_orb_runtime`.

Strongest risk: fallback mode remains for local Windows, which could confuse
review unless final evidence records the deployed runtime.

Next correction: focused artifact parsing must record the deployed mode and
client result before tranche completion.

## 004 MSRPC Runtime

`gm_control_quality`: 2

Evidence: the implementation adds a distinct MSRPC proof command and workflow
instead of relabeling the previous XML-RPC fallback.

Strongest risk: the DCE/RPC server path uses Impacket APIs that local Windows
validation cannot execute authoritatively.

Next correction: deployed focused workflow must prove
`runtime_mode=msrpc_runtime`, `wire_protocol=DCE/RPC v5 over ncacn_ip_tcp`,
endpoint registration, server log, client invocation, and GPT transcript.

`context_pressure_result`: 2

Evidence: the tranche writes expected artifacts under
`ci_artifacts/demo/legacy/msrpc`.

Strongest risk: package import, callback registration, or dynamic port handling
may differ inside the Linux ACA.

Next correction: if focused workflow fails, inspect its logs and patch the
actual DCE/RPC runtime path rather than downgrading to `xmlrpc_runtime`.

`delegation_effectiveness`: 2

Evidence: no subagents were dispatched because this turn did not authorize
delegation.

Strongest risk: MSRPC troubleshooting could benefit from parallel API/package
research if the deployed proof fails.

Next correction: keep the tranche local unless explicit delegation
authorization appears.

`operator_reviewability`: 2

Evidence: provider health, manifest, final summary modes, focused command, and
workflow all target one runtime mode: `msrpc_runtime`.

Strongest risk: fallback XML-RPC remains for local disabled runtime mode and
could confuse review if final artifacts are not checked.

Next correction: require downloaded workflow artifacts to prove deployed
`msrpc_runtime` before tranche closeout.

## 005 Remote DCOM Runtime

`gm_control_quality`: 2

Evidence: the proof command requires a distinct client context and fails if the
remote sentinel is not read through the COM object.

Strongest risk: DCOM authentication, firewall, or Azure networking may block
remote activation even when local COM automation works.

Next correction: focused workflow must produce a transcript identifying the
failing layer; no local COM fallback is allowed for this tranche.

`context_pressure_result`: 2

Evidence: the proof writes under `ci_artifacts/demo/windows/dcom`; after the
same-subnet client VM approach hit an Azure permission blocker, the focused
workflow uses GitHub-hosted Windows to avoid creating temporary Azure resources.

Strongest risk: public DCOM activation may be blocked by Azure edge routing or
server firewall/NAT behavior.

Next correction: inspect the remote activation transcript and write a blocker
if the failure is DCOM transport/security rather than workflow code.

`delegation_effectiveness`: 2

Evidence: no subagents were dispatched because this turn did not authorize
delegation.

Strongest risk: DCOM-specific Windows troubleshooting could benefit from a
parallel verifier if the focused run fails.

Next correction: keep diagnosis local unless explicit delegation
authorization appears.

`operator_reviewability`: 2

Evidence: the command writes server setup, client invocation, cleanup payload,
checks, generated schema, GPT transcript, and summary artifacts.

Strongest risk: reviewers could confuse controlled WScript.Shell fixture proof
with arbitrary DCOM estate support.

Next correction: preserve caveat language in final report and proof index after
the focused proof passes.
