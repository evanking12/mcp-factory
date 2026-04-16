# Dynamic Tranche Summary

Use one summary per executed tranche. It should be readable without opening the
full prompt chain.

## Tranche Summary: `[prompt_id]`

- tranche_class: `[trust_or_setup | blocker_localization | bounded_fix | authoritative_validation | closeout]`
- created_at_prompt_start: `[yes | no]`
- updated_during_prompt_when_branch_changes: `[none | notes]`
- finalized_at_prompt_close: `[yes | no]`
- live_writeback_checkpoint_passed: `[yes | no]`
- broader_goal_served: `[goal]`
- owned_seam: `[seam]`
- primary_question: `[question]`
- blocker_before: `[blocker]`
- blocker_after: `[blocker]`
- systems_touched:
  - `[system]`
- contracts_touched:
  - `[contract]`
- cheapest_trusted_validation_surface: `[surface]`
- truth_authority_surface: `[surface]`
- downgraded_truth_surfaces:
  - `[surface or none]`
- validation_run:
  - `[command or review]`
- result: `[pass | fail | partial | blocked]`
- commit_sha: `[sha | none]`
- next_prompt: `[path | none]`
- continuation_justified_now: `[yes | no]`
- exact_stop_owner: `[none | wider_goal_met | contradiction_growth | human_required_gate | bounded_cycle_failure | strategic_fork]`
- role_candidate: `[none | candidate]`
- system_candidate: `[none | candidate]`
- writeback_required:
  - `[none | writeback]`

## Workflow Quality Evaluation

- gm_control_quality:
  - score: `[0 | 1 | 2 | 3]`
  - evidence: `[evidence]`
  - strongest_risk: `[risk]`
  - next_correction: `[correction]`
- context_pressure_result:
  - score: `[0 | 1 | 2 | 3]`
  - evidence: `[evidence]`
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
  - `[role]`
- roles_dispatched:
  - `[role | none]`
- why_not_dispatched:
  - `[role]: [reason]`

## Operator Readout

`[one short paragraph explaining what changed, what is trusted, what remains
unproven, and the next move]`

