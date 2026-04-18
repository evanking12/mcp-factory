# Local Review

- The hardening workflows add gates rather than changing existing sponsor
  claims.
- Provider smoke requires the pipeline API key and therefore belongs in GitHub
  Actions with Key Vault fetch.
- Transcript integrity now requires prompt metadata in newly generated
  transcripts; legacy artifacts may need report-only regeneration or a new full
  run before strict integrity can pass.

