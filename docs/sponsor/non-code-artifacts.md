# Sponsor Non-Code Artifacts

## Azure Cost Posture

The project is designed to stay under the sponsor budget of `$150/month`.
Cost controls include small Azure Container Apps, on-demand Windows bridge VM
startup, sponsor-demo VM deallocation after CI proof, and the budget alert
script at `scripts/setup_budget_alert.ps1`.

## FERPA And Access Control

The project stores only demo artifacts and CI proof data needed for the
capstone. Team members should not upload FERPA-regulated student records or
unapproved sponsor data. Azure resources are restricted to the project team;
broader access is only for approved USF user acceptance testing.

## Architecture Diagram

Architecture references live in:

- `README.md`
- `docs/github-actions-e2e-plan.md`
- `infra/`
- `aspire/AppHost/Program.cs`

The sponsor demo path is: target upload or installed path, discovery, invocable
selection, MCP schema generation, GPT tool call, tool result, and downloadable
artifact.

## Rerunning Sponsor Demo E2E

Run [Sponsor Demo E2E](https://github.com/evanking12/mcp-factory/actions/workflows/sponsor-demo-e2e.yml)
from GitHub Actions. Use the fast iteration inputs when validating a narrow
change:

- `skip_windows_targets`: avoid VM time for report or GPT-only changes.
- `skip_gpt_matrix`: avoid GPT cost/time for Windows-only changes.
- `only_windows_target`: run one Windows bridge target.
- `only_gpt_case`: run one non-VM GPT matrix case.
- `report_only_run_id`: re-render reports from an existing artifact.

## Runtime-Shaped Provider Proof

Runtime-shaped proof means GPT-4o called a generated tool and the backend
returned a live hosted result from a deterministic provider endpoint that
validates the relevant request shape. JSON-RPC, SOAP, SQL, controlled
LDAP/JNDI bind/search/lookup, and controlled CORBA ORB/IIOP are
runtime-backed; RPC remains XML-RPC runtime proof; COM/DCOM uses Windows local
COM proof. This is not a claim that generalized CORBA estate migration,
DCE/MSRPC, enterprise LDAP migration, or remote DCOM infrastructure has been
deployed unless the report explicitly says so.
