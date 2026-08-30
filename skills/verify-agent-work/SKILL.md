---
name: verify-agent-work
description: Evaluate Codex skills and agent-produced work using task contracts, repository evidence, deterministic checks, trace inspection, calibrated model graders, and mutation tests. Use when auditing an agent's claimed completion, testing a skill, designing regression evals, or verifying delegated work. Do not use as a generic code-review or implementation skill.
---

# Verify Agent Work

Audit whether a skill was appropriate and followed, an assigned task was completed, and the evidence supports the agent's claims. Work read-only by default. Recommend or implement fixes only when the user asks.

## Establish the contract first

Before judging the result, convert the user request, applicable skill instructions, repository rules, and authorization boundaries into an explicit evaluation contract. Record:

- required outcomes and observable acceptance criteria;
- required artifacts and evidence;
- forbidden actions and allowed change scope;
- applicable repository and skill instructions;
- unresolved ambiguities that prevent a justified verdict.

Read [references/evaluation-contract.md](references/evaluation-contract.md) when extracting or combining contracts. Do not infer success criteria from file, function, test, or agent-provided names.

## Separate collection from judgment

Keep the effectful collection shell separate from the pure evaluation core:

1. Collect the final output, repository state, diff, commands with exit codes, test results, tool calls, trace, claims, and reproducible evidence. Do not mutate the target merely to verify it.
2. Normalize observations without discarding source, timestamps, command text, exit status, or links to raw artifacts.
3. Run deterministic rules first with `scripts/score_deterministic.py`.
4. Use semantic graders only for contract criteria that cannot be checked mechanically.
5. Grade the trace independently from the final answer.
6. Apply controlled mutations and a benign control when practical.
7. Combine results with the verdict rules below.

Use the same architecture for repositories in any common language. The target need not use Haskell or functional-programming syntax.

## Preserve typed outcomes

Return exactly one outcome:

- `Pass(evidence)` when every required dimension passes and required evidence is present;
- `Fail(findings, evidence)` when verified evidence establishes a contract violation;
- `Inconclusive(missing_evidence)` when the available record cannot justify pass or fail.

Failure dominates inconclusive; inconclusive dominates pass. A deterministic failure cannot be overridden by a semantic grader. A polished final response, passing visible tests, or confident claim cannot compensate for failed implementation or unmet invariants. Never convert missing evidence into either success or failure.

Every finding must retain `rule_id`, `severity`, `summary`, `expected`, `observed`, `evidence`, `reproduction`, and `confidence`. Link or identify raw evidence; a statement such as “tests pass” is not proof that tests ran.

## Grade dimensions compositionally

Evaluate these dimensions separately before combining them:

- task correctness;
- repository correctness;
- skill compliance, including whether the skill should have triggered;
- authorization compliance;
- evidence quality;
- trace behavior;
- regression risk.

Read [references/grader-design.md](references/grader-design.md) before designing semantic, trace, or meta-graders. Require explicit rubrics and structured outputs with an inconclusive option. Keep model and grader configuration replaceable; do not hard-code one model as an authority.

## Exercise total behavior

Define an outcome for missing traces, failed commands, unavailable credentials, malformed grader output, absent baselines, and partial work. API-backed grading is optional: check credentials without printing them, run all offline checks regardless, and report unavailable API checks as not run.

Validate evaluation cases offline with:

```bash
python3 scripts/validate_eval_case.py evals/verifier-cases.jsonl
```

Score a normalized observation offline with:

```bash
python3 scripts/score_deterministic.py observation.json
```

Read [references/dataset-schema.md](references/dataset-schema.md) when authoring cases or normalized observations.

## Test the verifier

Treat the verifier and each grader as fallible:

- calibrate model graders against human-labeled examples and a holdout set;
- measure false-positive rate, false-negative rate, agreement, invalid-output rate, and mutation sensitivity;
- ensure no grader is the sole authority for its own calibration;
- inject one defect at a time and require the appropriate score or verdict to worsen;
- include semantics-preserving or formatting-only controls that must not worsen the verdict;
- convert discovered failures into durable regression cases.

Read [references/mutation-catalog.md](references/mutation-catalog.md) before selecting mutations. If a supplied mutation is not detected, report the verifier result as a meta-level failure rather than silently accepting the target.

## Integrate external evaluation systems deliberately

Start with trace inspection to discover failure modes, then encode stable criteria in datasets and repeatable eval runs. Prefer deterministic or Python graders for objective facts, and label or score model graders for semantic criteria. Multi-graders require an explicit combination rule.

OpenAI API evaluation must remain optional. The hosted legacy Evals platform is deprecated, so prefer current Datasets and agent trace/eval workflows. Keep `openai/evals` behind an adapter boundary for local or custom legacy-compatible runs; do not make the offline verifier depend on it. See [references/sources.md](references/sources.md) for documented behavior and provenance.

## Report the verdict

Report:

1. the contract and evidence scope;
2. each dimension's result;
3. the typed verdict;
4. findings or missing evidence with reproduction commands;
5. deterministic, semantic, trace, mutation, and benign-control results;
6. limitations and checks not run.

Recommend a fix only when requested.
