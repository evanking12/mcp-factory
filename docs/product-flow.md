# Product Flow (Sections 2–5)

## 2) Specify Target
Inputs supported:
- Path to binary file (e.g., `C:\...\app.exe`, `...\lib.dll`)
- Path to installed instance (e.g., `C:\Program Files\App\`)
- Free-text hints describing expected features

Outputs:
- Target registered as `target.json` with metadata (path/type/hints)

## 3) Display Invocables
System produces `inventory.json` showing:
- invocable feature list
- default: all selected
- each item includes provenance + confidence + risk level

User can deselect to produce:
- `selection.json`

## 4) Generate MCP Architecture
Inputs:
- `target.json`
- `selection.json`
- generated component name (suggested)

Outputs:
- MCP server/tool package (generated code/config)
- deployed verification instance endpoint

## 5) Verify Output
UI:
- chat interface to invoke tools
- displays stdout/stderr/results
- allows download of outputs/logs
