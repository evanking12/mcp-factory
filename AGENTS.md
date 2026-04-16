# Dynamic Prompt System

This section can be pasted into a repo-level `AGENTS.md`.

## Operating Model

Codex should treat long-running architecture, cleanup, migration, test-system,
or legacy-surface work as a governed dynamic campaign when the user explicitly
asks for a campaign, autonomous continuation, or multi-tranche work.

Codex owns:

- implementation sequencing
- local investigation
- next prompt drafting
- blocker narrowing
- durable writeback

The user owns:

- product intent
- acceptance criteria
- stop gates
- risk tolerance
- merge authority

## Dynamic Campaign Law

A dynamic campaign is not a static list of prompts.

The default shape is:

- one wider goal
- one current frontier
- one dominant blocker
- one active prompt
- one evaluation surface
- one next prompt derived from evidence

Only the active prompt is canonical.

The next prompt is provisional until the current prompt's evaluation confirms it.

Do not stop merely because one prompt completed if:

- the wider goal remains unmet
- the prompt produced a justified next branch
- no stop condition fired

## Campaign Start Packet

Before authoring a new campaign, make these explicit:

- `wider_goal`
- `current_frontier`
- `stop_gate`
- `dominant_blocker`
- `expected_delivery_or_proving_target`
- `delegation_authorization`
- `operator_constraints`
  - `time_budget`
  - `merge_or_push_expectation`
  - `allowed_risk_level`
- `required_outputs`
  - `prompts`
  - `summaries`
  - `closeout`
  - `blocker_or_system_writeback`

If fields are missing, Codex may derive reasonable defaults from repo state and
state those assumptions explicitly.

## Required Campaign Shape

Campaigns live under:

```text
dynamic_campaigns/<campaign_slug>/
```

Required files and folders:

```text
CAMPAIGN.md
README.md
prompts/
  ACTIVE-PROMPT.md
outputs/
  tranche_summaries/
  evaluations/
  reviews/
  closeout/
  architect_briefs/
```

## Tranche Law

Each tranche owns one bounded seam and one primary question.

Every tranche must declare exactly one class:

- `trust_or_setup`
- `blocker_localization`
- `bounded_fix`
- `authoritative_validation`
- `closeout`

Do not combine blocker localization, system design, code repair, and
authoritative validation in one prompt unless the prompt explains why a smaller
loop cannot answer the question honestly.

## Live Writeback Checkpoint

Before any commit, push, pause, closeout, or next-prompt activation, Codex must
verify that campaign surfaces are current:

- active prompt pointer
- current tranche summary
- campaign log
- workflow-quality evaluation
- dispatch-accountability block
- architect brief if blocker ranking or trust changed
- family-blocker or missing-system writeback if a recurring issue emerged

If a branch-shaping fact exists only in chat, forward execution must stop until
writeback is repaired.

## Workflow Quality Evaluation

Every executed tranche must record:

- `gm_control_quality`
- `context_pressure_result`
- `delegation_effectiveness`
- `operator_reviewability`

Score each:

- `0 = failed_or_unsafe`
- `1 = weak`
- `2 = acceptable`
- `3 = strong`

Each field must include:

- `score`
- `evidence`
- `strongest_risk`
- `next_correction`

## Dispatch Accountability

Even if no subagents are used, every tranche must record:

- `roles_considered`
- `roles_dispatched`
- `why_not_dispatched`

Allowed skip reasons:

- `authorization_absent`
- `not_decision_bearing_this_tranche`
- `coordination_cost_outweighed_value`
- `critical_path_better_kept_local`
- `known_role_failure_mode_matched_current_task`
- `tranche_too_small`

## Family-Blocker And Missing-System Law

When the same issue repeats across bounded cycles, classify it as one of:

- `local_bug`
- `family_blocker`
- `missing_system`

Write durable entries using:

```text
docs/architecture/agentic_workflow/FAMILY-BLOCKER-SYSTEM-WRITEBACK.md
```

Do not leave recurring blockers only in chat or commit history.

## Archived And Legacy Surfaces

Archived systems are not automatically dead.

For each archived or legacy surface, classify it as:

- `active_contract`
- `reference_only`
- `quarantined_experimental`
- `deprecated_pending_delete`
- `delete_candidate`

Do not let archived code silently remain in default tests, default imports, or
required workflows unless it still protects a current durable contract.

