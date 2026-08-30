# Grader design

Use this reference when implementing or calibrating deterministic, semantic, trace, or meta-graders.

## Layers

### Deterministic graders

Check objective observations: required artifacts, changed paths, command exit codes, test status, schema validity, missing evidence, trace shape, and explicit contradictions between claims and records. Keep these graders pure after observations are collected. Run them first and retain every finding.

`scripts/score_deterministic.py` is the offline reference implementation. Its `Pass` is a deterministic partial verdict, not permission for a semantic grader to skip applicable criteria.

### Semantic graders

Use only when behavior cannot be reduced to an objective rule. Give the grader the contract criterion, relevant evidence, explicit rubric, counterexamples, and this output union:

```json
{"type":"Pass","evidence":["evidence-id"]}
{"type":"Fail","findings":[{"rule_id":"SEM-001"}],"evidence":["evidence-id"]}
{"type":"Inconclusive","missing_evidence":["behavioral-demo"]}
```

Reject malformed output. Do not ask the model to infer evidence that was not collected. Configure the model, prompt version, sampling parameters, and combination rule outside the rubric so they are replaceable.

### Trace graders

Grade the process separately from the artifact and final answer. Check required tool execution, tool choice, ignored failures, unauthorized side effects, fabricated completion claims, missed handoffs, and instruction violations. A correct artifact does not erase an authorization or trace failure.

### Meta-graders

Evaluate graders against human-labeled calibration and holdout cases. Report confusion-matrix counts, false-positive rate, false-negative rate, agreement, invalid-output rate, and mutation sensitivity. Test presentation order and persuasive-language variants. One grader cannot certify its own reliability without independent labels or mechanical expectations.

## Combination rule

Use lattice order `Fail > Inconclusive > Pass` for final severity. Apply these constraints:

- deterministic failures are monotonic and cannot be overridden;
- missing required evidence prevents pass;
- a semantic pass without cited collected evidence is invalid;
- conflicting non-failure results remain inconclusive until reconciled;
- multi-grader aggregation must name its rule, such as unanimous pass with any-fail veto.

Do not average away failures across dimensions.

## Calibration protocol

1. Freeze a human-labeled calibration set and a separate holdout set.
2. Include positive, negative, inconclusive, adversarially persuasive, order-swapped, and malformed examples.
3. Tune rubrics only on calibration data.
4. Measure on the holdout without editing the grader.
5. Apply controlled mutations and benign transformations.
6. Investigate disagreements by returning to raw evidence; do not relabel solely to improve agreement.

OpenAI's current agent evaluation guidance recommends inspecting representative traces before formalizing graders, then moving stable criteria into datasets and repeatable eval runs. Hosted model graders are optional. The legacy Evals API/platform is deprecated for new work; keep any `openai/evals` integration in an adapter that translates this skill's cases and observations without changing the pure core.

## `openai/evals` adapter boundary

An optional adapter consumes validated `EvalCase` records plus normalized `EvalObservation` records and emits the typed grader result defined above. It may translate cases to registry data, a completion function, or custom local eval logic, but it must:

- keep collection and API calls outside `score_deterministic.py`;
- preserve case, evidence, finding, model, prompt-version, and run identifiers;
- reject invalid or missing adapter output as inconclusive;
- never reinterpret a deterministic failure as a numeric average;
- remain replaceable without changing the offline dataset or verdict schemas.

Do not import `openai/evals` from the deterministic scripts. Implement an adapter only when a local/custom framework run is actually requested.
