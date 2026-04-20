# Sponsor Video Demo Walkthrough

This is the recommended recorded demo path for the capstone presentation. Use
SOAP/WSDL as the live UI target because it is technically rich enough to show
legacy contract discovery, generated MCP tooling, GPT tool selection, runtime
execution, and downloadable artifacts without depending on fragile Windows
infrastructure during the video.

## Demo URL

- Web UI: <https://mcp-factory-ui.icycoast-8ddfa278.eastus.azurecontainerapps.io>
- Canonical proof run: <https://github.com/evanking12/mcp-factory/actions/runs/24613173130>
- Hardening integrity proof: <https://github.com/evanking12/mcp-factory/actions/runs/24613434034>
- Demo readiness proof: <https://github.com/evanking12/mcp-factory/actions/runs/24673053993>
- Focused Remote DCOM source proof: <https://github.com/evanking12/mcp-factory/actions/runs/24577926238>
- Artifact name: `sponsor-demo-e2e`

## Video Methodology

Do not try to show every supported target live in the recording. Use one
technically rich target, SOAP/WSDL, to demonstrate the full user workflow on
screen. Then use diagrams and GitHub Actions artifacts to prove that the same
contract is verified across the broader target matrix.

Recommended video flow:

1. Show the requirement-to-demo framing slide or section.
2. Show the Azure infrastructure graph.
3. Show the binary/protocol routing graph.
4. Run one complete UI demo with SOAP/WSDL:
   upload/load, analyze, select, generate, chat, `tool_call`, backend
   `tool_result`, download.
5. Show the GitHub Actions proof bundle and explain that CI verifies the same
   evidence contract across the supported formats.
6. Close with truthful boundaries: controlled runtime-backed proof, not
   arbitrary enterprise migration or perfect undocumented binary recovery.

The key sentence:

```text
The live UI path shows one complete end-to-end MCP conversion. The GitHub Actions proof bundle verifies that the same discovery, schema generation, GPT tool_call, backend tool_result, and artifact contract is exercised across the broader sponsor-required target set.
```

## Requirement Mapping For The Video

Use this as the narration map when recording.

| Sponsor requirement | What to show in the video | Evidence to point at |
|---|---|---|
| Accept a binary/executable/source/contract target | Load the SOAP/WSDL showcase; mention file upload and installed path support | UI upload/path controls; GitHub Actions Windows/repo/protocol matrices |
| User can provide hints | Show the hints box populated for SOAP/WSDL | UI Step 1 |
| Display possible invocations | Show discovered `GetCustomer` / `SubmitTicket` invocables | UI Step 2 and final artifact invocable summaries |
| User can select invocables | Select one or two SOAP operations | UI Step 2 selected checkboxes |
| Generate MCP architecture/schema | Click `Generate`; show schema preview | UI Step 3; generated schema download |
| Verify through chatbot/LLM | Ask GPT to call `GetCustomer` | UI Step 4 chat |
| Backend returns executable/runtime output | Show `Live Proof Trace` `tool_result` with `real_runtime` | Trace panel and GPT transcript artifacts |
| User can download output | Click schema/server download buttons | `/api/download/{job_id}/{filename}` |
| Azure/GitHub infrastructure | Show Azure graph and GitHub Actions runs | Azure diagram, canonical run, proof bundle |
| Broad target coverage | Do not run every target live; show routing graph and proof matrix | `sponsor-demo-e2e` artifact, final summary, runtime matrix |

## Target To Use

Primary target:

- `tests/fixtures/sponsor/contoso_service.wsdl`

Fastest video path:

1. Open the deployed UI.
2. Click `Load SOAP/WSDL Showcase`.
3. Click `Analyze Binary`.

Manual upload path:

1. Open the deployed UI.
2. Upload `tests/fixtures/sponsor/contoso_service.wsdl`.
3. Use this hint:

```text
Video demo target: SOAP WSDL legacy customer service. Show discovery, generated MCP schema, GPT tool_call, and backend tool_result.
```

4. Click `Analyze Binary`.

## UI Walkthrough

1. Upload or load the SOAP/WSDL showcase.
2. Analyze the target and show that the UI discovers SOAP operations as invocables.
3. Select one or two operations. `GetCustomer` and `SubmitTicket` are the clearest.
4. Generate the MCP schema.
5. Show the generated schema preview and the download button.
6. Open the chat panel.
7. Point out the `Live Proof Trace` panel next to chat.
8. Ask GPT to call the generated tool with a deterministic sentinel.
9. Show the visible `tool_call`, backend route, runtime mode, and `tool_result` in the trace panel.
10. Download the generated schema or MCP artifacts through `/api/download/{job_id}/{filename}`.
11. Show the `CI Proof Bundle` link and explain that GitHub Actions artifacts are separate from app downloads.

## GPT Prompts

Use these prompts in the UI chat after generating the schema.

Prompt 1, direct proof:

```text
Call the generated SOAP customer lookup tool now. Use customerId CUST-001 and include this exact sentinel string in any available string argument: MCP_FACTORY_SOAP_VIDEO. Show me the tool_call and tool_result evidence.
```

Prompt 2, support-ticket proof:

```text
Create a Contoso support ticket for customer CUST-001. Subject: billing issue. Description: customer needs invoice help. Priority: high. Include sentinel MCP_FACTORY_SOAP_TICKET in any optional string argument, then summarize the tool_result.
```

Prompt 3, natural-language agent framing:

```text
A customer says: "I cannot find my invoice and need support." Use the available SOAP customer-service tool to create the right backend action. After the tool_result, explain what MCP Factory proved in one sentence.
```

Prompt 4, schema inspection:

```text
List the generated tools you can use from this SOAP/WSDL target, then call the safest customer lookup or ticket tool once.
```

## What To Say

Short claim:

```text
This project is complete because the UI demonstrates the user workflow, and the canonical GitHub Actions proof verifies the full requirement set: discovery, invocable selection, MCP schema generation, GPT tool calls, backend tool results, downloadable artifacts, Azure runtime infrastructure, Windows bridge evidence, repo ingestion, and hard legacy protocol proofs.
```

SOAP-specific framing:

```text
SOAP/WSDL is a good live target because the input is not source code for a chatbot. It is a legacy service contract. MCP Factory discovers operations from the WSDL, turns them into GPT-callable MCP tools, and routes the tool call to a controlled SOAP runtime that validates the envelope and returns a backend tool result.
```

Live trace framing:

```text
The Live Proof Trace panel makes the invisible MCP loop visible: GPT emits a tool_call, the backend routes it through the generated tool and SOAP runtime, and the runtime returns a tool_result with the customer-shaped proof payload.
```

Hard-legacy proof framing:

```text
The live video uses SOAP because it is stable and visually clear. The proof matrix then shows the broader runtime-backed evidence for JSON-RPC, SOAP, SQL, REST, LDAP/JNDI, CORBA ORB/IIOP, MSRPC, controlled Remote DCOM, Windows discovery, and repo ingestion.
```

Boundary:

```text
This capstone does not claim perfect arbitrary closed-source binary semantic recovery or arbitrary enterprise estate migration. The proof is controlled, runtime-backed, artifact-backed, and GPT-tool-call verified.
```

## Azure Infrastructure Diagram

Show this before the UI demo to explain where the system runs.

```mermaid
flowchart LR
  U["Browser / recorded UI"] --> UI["Azure Container App: mcp-factory-ui"]
  UI --> API["Azure Container App: pipeline API"]
  API --> ST["Azure Blob Storage: job artifacts"]
  API --> KV["Azure Key Vault: runtime secrets"]
  API --> AOAI["Azure OpenAI / GPT-4o tool calls"]
  API --> LP["Hosted legacy provider runtimes"]
  API --> VM["Windows bridge VM"]
  GHA["GitHub Actions"] --> API
  GHA --> VM
  GHA --> ST
  GHA --> REPORT["sponsor-demo-e2e proof bundle"]
  VM --> WPROOF["Windows discovery / COM / GUI proof summaries"]
  LP --> LPROOF["SOAP, JSON-RPC, SQL, REST, LDAP/JNDI, CORBA, RPC results"]
```

Narration:

```text
The UI and API run in Azure Container Apps. Storage holds generated job artifacts. GitHub Actions is the authoritative verification layer: it drives the deployed services, the Windows bridge VM, the hosted legacy runtimes, and then publishes the sponsor proof bundle.
```

## Target Routing Diagram

Show this after the Azure diagram and before or after the SOAP walkthrough. It
explains why SOAP is only one live example, not the whole proof surface.

```mermaid
flowchart LR
  T["User target"] --> A["Analyzer / discovery"]
  A --> K{"Target class"}
  K -->|"SOAP/WSDL"| SOAP["SOAP runtime /api/legacy/soap"]
  K -->|"OpenAPI / REST"| REST["REST route validator /api/legacy/rest"]
  K -->|"JSON-RPC"| JSONRPC["JSON-RPC runtime /api/legacy/jsonrpc"]
  K -->|"SQL"| SQL["SQLite-backed SQL runtime"]
  K -->|"LDAP/JNDI"| LDAP["LDAP/JNDI lookup runtime"]
  K -->|"CORBA IDL"| CORBA["CORBA ORB/IIOP proof runtime"]
  K -->|"RPC IDL"| RPC["MSRPC/RPC proof runtime"]
  K -->|"Python, JS, Ruby, PHP, PowerShell, CMD"| LOCAL["Local/script runtime"]
  K -->|"EXE, DLL, TLB, registry, GUI"| WIN["Windows bridge VM"]
  K -->|"Repo/folder"| REPO["Repo ingestion / source scanners"]
  SOAP --> S["Generated MCP/OpenAI tool schema"]
  REST --> S
  JSONRPC --> S
  SQL --> S
  LDAP --> S
  CORBA --> S
  RPC --> S
  LOCAL --> S
  WIN --> S
  REPO --> S
  S --> GPT["GPT tool_call"]
  GPT --> EXEC["Backend executor"]
  EXEC --> RESULT["tool_result + artifacts"]
```

Narration:

```text
Different targets route to different proof backends. SOAP goes to the SOAP runtime, scripts can execute locally, Windows GUI or metadata targets go through the Windows bridge VM, and legacy protocol contracts route to hosted protocol runtimes. The generated MCP tool interface is the common layer.
```

## End-To-End Proof Diagram

```mermaid
flowchart LR
  A["User target: file, path, repo, WSDL, SQL, protocol contract"] --> B["Analyzer / discovery"]
  B --> C["Invocable list"]
  C --> D["User selection"]
  D --> E["MCP/OpenAI tool schema generation"]
  E --> F["Chat with GPT"]
  F --> G["tool_call"]
  G --> H["Backend executor / hosted runtime / Windows bridge"]
  H --> I["tool_result"]
  I --> F
  E --> J["App downloads via /api/download/{job_id}/{filename}"]
  H --> K["GitHub Actions CI proof artifacts"]
```

## GitHub Actions Proof Framing

After the SOAP UI walkthrough, show the canonical proof run and artifact. The
video claim should be:

```text
The SOAP UI path is the human walkthrough. GitHub Actions is the proof that this is not a one-off: the pipeline verifies generated schemas, GPT tool_call events, backend tool_result events, transcripts, runtime modes, Windows bridge summaries, repo-ingestion proof, and downloadable artifacts.
```

What to point at in the artifact:

- `ci_artifacts/demo/final-summary.md`
- `ci_artifacts/demo/final-summary.json`
- `ci_artifacts/demo/sponsor-report.html`
- GPT matrix transcripts and summaries
- Windows summaries and Windows GPT matrix
- repo-ingestion summary
- runtime-mode matrix

Use this sentence if time is short:

```text
We only record one live UI target because the full target matrix is verified in CI. The CI artifact is the evidence contract: if discovery, schema generation, GPT tool_call, backend tool_result, or required artifacts are missing, the sponsor proof fails.
```

## Teammate Commit Assessment

Commit `ab44a3457b5c8c805afa42183ae65fd26c971be7` in
`TheNgith/mcp-factory` is a useful error-output improvement, not merely a
formatting refactor. It adds the idea of structured failure diagnostics for tool
calls:

- `tool_result` events can include an `error` object.
- failures are classified as sentinel, HRESULT, Win32, timeout, bridge
  unreachable, unknown tool, schema mismatch, or exception.
- the UI can render a failure badge, human-readable suggestion, attempted
  probes, and known-good arguments.
- generated MCP servers can return richer human-plus-JSON error messages.
- a synthetic `explain_failure` tool lets the model ask for diagnostics instead
  of retrying blindly.

Do not cherry-pick the commit directly into this repo. The local chat and
executor contracts are currently simpler: `api.chat.stream_chat` calls
`api.executor._execute_tool` and expects a plain string result, while that
commit expects traced execution hooks such as `_execute_tool_traced` and a
larger generated-server error-enrichment surface. A direct port would be
merge-risky.

Clean incorporation path:

1. Add `api/error_enrichment.py` as a pure classifier module.
2. Add a backward-compatible `_execute_tool_traced(inv, args)` wrapper that
   returns `{result_str, trace, error}` while keeping `_execute_tool(inv, args)`
   as the plain-string API.
3. Update `api/chat.py` so every `tool_result` SSE event includes
   `error: null` on success or a structured error payload on failure.
4. Update `ui/main.py` to render `evt.error` in a compact diagnostic block.
5. Add tests for success `error: null`, unknown-tool errors, timeout errors,
   bridge errors, and generated-server error payloads.
6. Vendor the enrichment module into generated MCP server artifacts only after
   the internal chat path is stable.

Recommendation: extract the principles and implement them as a small
`structured-tool-errors` tranche. That gives the professor-facing output
improvement without destabilizing the already-green sponsor proof contract.
