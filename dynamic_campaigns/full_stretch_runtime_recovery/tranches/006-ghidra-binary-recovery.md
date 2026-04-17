# 006 Ghidra Binary Recovery Prototype

Class: `bounded_fix`

Status: pending.

Goal: add evidence-ranked recovery for undocumented compiled fixtures.

Required fixture corpus:
- stripped C EXE with no `--help`
- DLL with named exports
- DLL with ordinal exports
- EXE with deterministic stdout
- EXE with deterministic file/registry side effect

Required artifacts:
- `ci_artifacts/demo/ghidra/summary.json`
- `ci_artifacts/demo/ghidra/<fixture>/ghidra-functions.json`
- `ci_artifacts/demo/ghidra/<fixture>/decompile-summary.md`
- `ci_artifacts/demo/ghidra/<fixture>/dynamic-trace.json`
- `ci_artifacts/demo/ghidra/<fixture>/evidence-ranking.json`
- `ci_artifacts/demo/ghidra/<fixture>/generated-schema.json`
- `ci_artifacts/demo/ghidra/<fixture>/transcript.json`

Gate:
- At least one undocumented compiled fixture has recovered invocation evidence.
- GPT calls a generated recovered-binary tool.
- Tool result contains deterministic fixture output.
- Final summary reports `proof_level=evidence_ranked_binary_recovery`.

