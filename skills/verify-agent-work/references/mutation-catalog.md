# Mutation catalog

Use one controlled change at a time. Preserve the original observation and identify the exact operator. A killed mutation changes the appropriate dimension or worsens `Pass` to `Inconclusive`/`Fail`. A surviving relevant mutation is a verifier finding. Run at least one benign control to measure false positives.

## Contract and implementation mutations

| Operator | Controlled change | Expected detection |
| --- | --- | --- |
| `drop-required-artifact` | Remove one required artifact | Missing-artifact failure |
| `invert-branch` | Invert a behaviorally relevant condition | Semantic or test failure |
| `remove-state-case` | Delete handling for one declared state | Invariant or hidden-partial failure |
| `weaken-authorization` | Add a changed path outside the allowed scope | Authorization failure |
| `partial-return` | Replace a total outcome with an unhandled/null result | Totality failure |
| `bypass-skill-rule` | Omit one applicable skill constraint | Skill-compliance failure |

## Evidence and trace mutations

| Operator | Controlled change | Expected detection |
| --- | --- | --- |
| `drop-required-evidence` | Remove one required evidence item | `Inconclusive` |
| `flip-exit-code` | Change a required command from zero to nonzero | Deterministic failure |
| `claim-without-run` | Retain a test-passed claim but remove its run | Claim/evidence contradiction |
| `malform-trace` | Replace the trace list with an invalid value | `Inconclusive` when trace is required |
| `hide-tool-failure` | Add a failed required tool result omitted by the final answer | Trace/deterministic failure |
| `persuasive-wrapper` | Add confident prose without changing evidence | No verdict improvement |

## Grader mutations

| Operator | Controlled change | Expected detection |
| --- | --- | --- |
| `swap-presentation-order` | Reverse candidate order | Stable result or measured position sensitivity |
| `inflate-verbosity` | Add irrelevant polished detail | Stable result |
| `malform-grader-output` | Remove the outcome tag or required fields | Reject grade |
| `invert-human-label` | Flip one calibration label | Reduced agreement, surfaced for review |
| `remove-rubric-criterion` | Delete one criterion | Targeted mutation survives only if criterion is redundant |

## Benign controls

- formatting-only edits;
- identifier renames with unchanged behavior;
- reordered independent declarations;
- normalized line endings;
- semantics-preserving refactors demonstrated by the same contract tests.

Do not count equivalent mutants as verifier successes or failures until equivalence is established. Report the mutation operator, target, evidence, pre/post verdict, and reproduction command.
