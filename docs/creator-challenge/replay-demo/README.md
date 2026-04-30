# MCP Factory Creator Challenge Replay Demo

This folder is a static GitHub Pages demo. It replays sanitized data derived
from real MCP Factory artifacts; it does not run the backend, call a model API,
connect to the bridge, or execute binaries in the browser.

## Generate Data

From the repository root:

```powershell
python scripts/creator_challenge/build_replay_bundle.py
```

The generator writes:

```text
docs/creator-challenge/replay-demo/data/index.json
docs/creator-challenge/replay-demo/data/runs/<run-id>/run.json
docs/creator-challenge/replay-demo/data/runs/<run-id>/run-trace.json
docs/creator-challenge/replay-demo/data/runs/<run-id>/run-metrics.json
docs/creator-challenge/replay-demo/data/runs/<run-id>/run-trace.md
```

## Serve Locally

```powershell
python -m http.server 8088 --directory docs/creator-challenge/replay-demo
```

Open:

```text
http://127.0.0.1:8088/
```

## Claim Ceiling

This demo can claim:

- static replay of real run artifacts
- sanitized product-route evidence display
- OpenTelemetry-shaped diagnostic metrics
- local reproduction instructions

It cannot claim:

- live hosted product execution
- browser-side binary analysis
- product green from telemetry alone
- arbitrary user-upload execution

## Public Deployment

The public copy should be mirrored into `mcp-factory-public` after local
validation. GitHub Pages should publish only this static folder.
