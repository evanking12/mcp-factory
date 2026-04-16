# Dynamic Campaign Template

Use this to create a governed campaign for multi-step work.

## Campaign Start Packet

- wider_goal: `[goal]`
- current_frontier: `[current repo/product boundary]`
- stop_gate: `[exact success or stop condition]`
- dominant_blocker: `[single strongest blocker or unknown]`
- expected_delivery_or_proving_target: `[target]`
- delegation_authorization: `[yes | no]`
- operator_constraints:
  - time_budget: `[budget]`
  - merge_or_push_expectation: `[expectation]`
  - allowed_risk_level: `[risk]`
- required_outputs:
  - prompts: `[yes | no]`
  - summaries: `[yes | no]`
  - closeout: `[yes | no]`
  - blocker_or_system_writeback: `[yes | no]`

## Campaign Shape

- campaign_slug: `[slug]`
- campaign_folder: `dynamic_campaigns/[slug]/`
- active_prompt: `dynamic_campaigns/[slug]/prompts/ACTIVE-PROMPT.md`
- campaign_log: `dynamic_campaigns/[slug]/outputs/evaluations/CAMPAIGN-LOG.md`

## Wider Goal

`[state the broader goal]`

## Current Frontier

`[state the current honest boundary]`

## Dominant Blocker

`[state the blocker]`

## Stop Gate

Stop when:

- `[success condition]`
- or six bounded cycles on the same blocker fail to improve it
- or contradictions grow
- or a human-required strategic gate is reached

Do not stop merely because one prompt finished.

## Preserved Foundations

- `[foundation or contract 1]`
- `[foundation or contract 2]`
- `[foundation or contract 3]`

## Active Systems

- `[system 1]`
- `[system 2]`

## Archived / Legacy Systems

For each archived system, classify:

- name: `[system]`
- status: `[reference_only | quarantined_experimental | deprecated_pending_delete | delete_candidate]`
- why kept: `[reason]`
- must not affect: `[default runtime | default tests | required CI | product path]`

## Default Tranche Classes

Every tranche must be one of:

- `trust_or_setup`
- `blocker_localization`
- `bounded_fix`
- `authoritative_validation`
- `closeout`

## Tranche Generation Law

For each tranche:

1. choose one owned seam
2. ask one primary question
3. choose the cheapest honest validation surface
4. update the active prompt
5. execute the tranche
6. update the tranche summary during execution when branch-shaping facts appear
7. finalize the summary at prompt close
8. rerank the blocker
9. either write the next prompt or record the stop owner

## Reviewability Contract

The campaign must leave:

- prompts
- compact tranche summaries
- campaign log
- closeout packet
- architect brief
- family-blocker or missing-system writeback when justified

