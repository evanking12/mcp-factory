# Active Prompt

Implement live legacy providers and require all sponsor non-VM cases to pass a
GPT tool call with a real tool result. Work sequentially:

1. Add deterministic legacy provider API routes.
2. Wire executor fallback to the provider routes.
3. Convert manifest and final summaries to all-live semantics.
4. Add report-only and fast iteration workflow controls.
5. Add sponsor report HTML and UI proof-bundle affordance.
6. Run tests, push, run CI, inspect artifacts, and close out.
