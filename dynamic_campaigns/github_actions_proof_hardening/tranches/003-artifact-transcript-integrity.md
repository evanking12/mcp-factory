# 003 Artifact Transcript Integrity

- Class: `bounded_fix`
- Primary question: can a downloaded sponsor artifact prove all required files
  and transcripts are present and internally consistent?
- Gate:
  - `validate-sponsor-artifact` checks final summaries, sponsor report, GPT
    transcripts, Windows summaries, repo summary, runtime matrix, and schemas.
  - `validate-transcript-integrity` requires prompt, tool call, tool result,
    sentinel, and no provider-required success path.

