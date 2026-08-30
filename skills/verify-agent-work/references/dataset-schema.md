# Dataset and observation schema

Use JSON Lines: one UTF-8 JSON object per nonblank line. `scripts/validate_eval_case.py` enforces the evaluation-case subset described here.

## EvalCase

Required fields:

- `case_id`: nonempty stable string.
- `target_type`: `skill`, `agent_work`, or `grader`.
- `prompt`: nonempty request presented to the target.
- `fixture`: string locator or object containing normalized inputs.
- `contract`: object containing the criteria for this case.
- `invariants`: array of nonempty strings.
- `forbidden_actions`: array of nonempty strings.
- `required_evidence`: array of declarations `{evidence_id, kind, required}`.
- `expected_outcome`: typed object described below.
- `mutations`: array of mutation declarations.
- `tags`: array of unique nonempty strings.

Expected outcomes are a tagged union:

```json
{"type":"Pass","evidence":["tests"]}
{"type":"Fail","finding_rules":["DET-003"],"evidence":["test-run"]}
{"type":"Inconclusive","missing_evidence":["test-run"]}
```

Mutation declarations contain `mutation_id`, `operator`, `target`, and `expected_effect`, all nonempty strings. `expected_effect` describes the observable worsening or invariant result, not an implementation instruction.

## EvalObservation

The deterministic scorer accepts an object with these fields. Unknown fields are preserved by the producer but ignored by the scorer.

```json
{
  "final_output": "Implemented and tested",
  "changed_files": ["src/parser.py", "tests/test_parser.py"],
  "artifact_files": ["src/parser.py", "tests/test_parser.py"],
  "diff": "durable locator or captured patch",
  "commands": [
    {"command":"python -m unittest","exit_code":0,"required":true,"evidence_id":"cmd-tests"}
  ],
  "exit_codes": {},
  "test_results": [
    {"name":"unit","status":"passed","command":"python -m unittest","exit_code":0,"evidence_id":"tests"}
  ],
  "tool_calls": [{"tool":"shell","action":"test","arguments":{},"result":"tests"}],
  "trace": [],
  "claims": [
    {"claim_id":"claim-tests","type":"tests_passed","text":"Tests pass","evidence_ids":["tests"]}
  ],
  "collected_evidence": [
    {"evidence_id":"tests","kind":"test_result","source":"local command","value":{"passed":12},"verified":true}
  ],
  "contract": {
    "required_artifacts":["src/parser.py"],
    "required_evidence":[{"evidence_id":"tests","kind":"test_result","required":true}],
    "allowed_changed_paths":["src/**","tests/**"],
    "forbidden_actions":[],
    "require_trace":false
  }
}
```

Status values for tests are `passed`, `failed`, `error`, `skipped`, and `not_run`. A skipped or not-run test is not passing evidence. Set `required` on commands explicitly; exploratory failures should not be mislabeled as required checks.

## Finding

Every deterministic or semantic failure uses:

```json
{
  "rule_id":"DET-003",
  "severity":"error",
  "summary":"Required test failed",
  "expected":"exit code 0",
  "observed":"exit code 1",
  "evidence":["tests"],
  "reproduction":"python -m unittest",
  "confidence":1.0
}
```

## Verdict

The final verdict is one of:

```json
{"outcome":"Pass","evidence":["..."]}
{"outcome":"Fail","findings":[{...}],"evidence":["..."]}
{"outcome":"Inconclusive","missing_evidence":["..."]}
```

The deterministic scorer also emits `scope: "deterministic"` to make its partial nature explicit.
