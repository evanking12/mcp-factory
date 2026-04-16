# Dynamic Tranche Template

Use this for one bounded prompt inside a wider campaign.

# Prompt `[id]`: `[short title]`

## Prompt Status

- created_at_prompt_start: `[yes | no]`
- updated_during_prompt_when_branch_changes: `[none | notes]`
- finalized_at_prompt_close: `[yes | no]`
- completion_state: `[planned | in_progress | completed | blocked]`
- broader_goal_served: `[goal]`
- active_blocker_family: `[blocker]`
- owned_seam: `[one exact seam]`
- primary_question: `[one question]`
- tranche_class: `[trust_or_setup | blocker_localization | bounded_fix | authoritative_validation | closeout]`
- cheapest_trusted_validation_surface: `[test | artifact | route | manual review | none yet]`
- truth_authority_surface: `[code_truth | artifact_truth | status_truth | operator_truth | validation_truth]`
- harder_loop_deferred: `[larger loop not being spent yet]`

## Goal

`[bounded tranche goal]`

## Primary Decision

Answer this in one sentence:

- `[yes/no/bounded-choice decision]`

## Why This Comes Now

- `[reason 1]`
- `[reason 2]`

## In Scope

- `[work item 1]`
- `[work item 2]`
- `[work item 3 max unless validation/writeback support]`

## Out Of Scope

- `[explicit non-goal 1]`
- `[explicit non-goal 2]`

## Contracts Touched

- `[contract/schema/API/artifact]`

## Validation

Run:

- `[command or review surface]`

Validation law:

- prefer the cheapest trusted surface
- do not run expensive end-to-end validation to discover basic ownership
- if no trusted validation exists, the tranche outcome is observability or
  contract creation, not proof

## Done Means

- `[binary falsifiable condition]`
- `[artifact/test/review that proves it]`

## Failure Means

- `[failure condition]`
- `[condition that forces blocker rerank or split]`

## Live Writeback Gate

Before commit, push, pause, closeout, or next-prompt activation, update:

- active prompt
- tranche summary
- campaign log
- workflow-quality evaluation
- dispatch accountability
- family-blocker/missing-system writeback if justified

## Workflow Quality Evaluation

- gm_control_quality:
  - score: `[0 | 1 | 2 | 3]`
  - evidence: `[evidence]`
  - strongest_risk: `[risk]`
  - next_correction: `[correction]`
- context_pressure_result:
  - score: `[0 | 1 | 2 | 3]`
  - evidence: `[whether branch-shaping facts lived only in chat]`
  - strongest_risk: `[risk]`
  - next_correction: `[correction]`
- delegation_effectiveness:
  - score: `[0 | 1 | 2 | 3]`
  - evidence: `[evidence]`
  - strongest_risk: `[risk]`
  - next_correction: `[correction]`
- operator_reviewability:
  - score: `[0 | 1 | 2 | 3]`
  - evidence: `[evidence]`
  - strongest_risk: `[risk]`
  - next_correction: `[correction]`

## Dispatch Accountability

- roles_considered:
  - `[role or none]`
- roles_dispatched:
  - `[role or none]`
- why_not_dispatched:
  - `[role]: [reason]`

## Evaluation

### Primary Question Result

- answer: `[yes | no | not yet knowable]`
- deciding_surface: `[surface]`
- why_that_surface_is_honest_now: `[reason]`

### What This Proved

- `[result]`

### What Remains Unproven

- `[gap]`

### Blocker Reranking

- blocker_before: `[blocker]`
- blocker_after: `[blocker]`
- reranking_correct: `[yes | no]`
- why: `[reason]`

### Role Candidate Check

- candidate: `[none | possible role]`
- action: `[none | evaluate later | promote]`

### System Candidate Check

- candidate: `[none | possible system]`
- action: `[none | writeback | implement later]`

## Next Prompt

- `[next prompt path or none]`

