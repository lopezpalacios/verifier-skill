# Consulted sources and provenance

Consulted 2026-08-30. Links point to primary documentation, project documentation, or original research. The summaries below are paraphrases.

## Documented behavior

- [OpenAI: Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals) recommends beginning with representative traces to discover failure modes, then moving stable criteria into datasets and repeatable eval runs. It calls out tool choice, handoffs, instruction violations, and end-to-end changes as agent-evaluation questions.
- [OpenAI: Trace grading](https://developers.openai.com/api/docs/guides/trace-grading) defines trace grading over end-to-end decisions and tool calls, and describes trace evals for repeatable comparison and regression detection.
- [OpenAI: Working with evals](https://developers.openai.com/api/docs/guides/evals) documents schemas, testing criteria, JSONL data, and eval runs. It also states that the legacy Evals platform becomes read-only on 2026-10-31 and is scheduled to shut down on 2026-11-30, recommending Datasets for new evaluation work.
- [OpenAI: Graders](https://developers.openai.com/api/docs/guides/graders) documents string, similarity, score-model, and Python graders; it recommends evaluating model graders against ground-truth examples and warns about grader/reward hacking.
- [`openai/evals` README](https://github.com/openai/evals) describes the open-source framework, registry, custom/private evals, JSON data, and completion-function support for tool-using systems.
- [`openai/evals` eval templates](https://github.com/openai/evals/blob/main/docs/eval-templates.md) distinguishes basic deterministic matching, custom logic, and model-graded templates, and recommends inspecting completions before choosing a template.
- [`openai/evals` custom eval guide](https://github.com/openai/evals/blob/main/docs/custom-eval.md) identifies its sampling, recording, and metric interfaces and shows dataset/registry-based extension. The repository currently says it is not accepting custom-code eval contributions.

## Research findings used

- Zheng et al., [“Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena”](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html), NeurIPS 2023: strong judges can agree well with humans, but exhibit position, verbosity, self-enhancement, and reasoning biases.
- Liu et al., [“Calibrating LLM-Based Evaluator”](https://aclanthology.org/2024.lrec-main.237/), LREC-COLING 2024: human-labeled examples and explicit, refined criteria improve correlation with expert evaluation.
- Gao, Schulman, and Hilton, [“Scaling Laws for Reward Model Overoptimization”](https://proceedings.mlr.press/v202/gao23h.html), ICML 2023: optimizing an imperfect proxy can improve proxy score while degrading gold-standard performance.
- Papadakis et al., [“Mutation Testing Advances: An Analysis and Survey”](https://discovery.ucl.ac.uk/id/eprint/10056704/), 2019: artificial defects can assess test-suite adequacy, guide tests, and support controlled experiments; equivalent and costly mutants require care.
- Claessen and Hughes, [“QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs”](https://doi.org/10.1145/351240.351266), ICFP 2000: executable properties can be exercised over generated inputs, motivating law-based tests independent of implementation examples.
- Liu et al., [“AgentBench: Evaluating LLMs as Agents”](https://arxiv.org/abs/2308.03688), ICLR 2024: interactive multi-environment evaluation exposes failures in long-horizon reasoning, decisions, and instruction following.
- Yao et al., [“tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains”](https://arxiv.org/abs/2406.12045), ICLR 2025: final environment state and repeated-trial reliability reveal tool-agent failures that single outputs miss.

## Design decisions and inferences

These are this skill's design, not claims made verbatim by the sources:

- The `Pass | Fail | Inconclusive` union prevents absent evidence from being silently treated as success or failure.
- The pure-core/effectful-shell split makes deterministic verdict laws repeatable without a network or live agent.
- Failure-dominant composition prevents averages or persuasive model output from erasing mechanically verified violations.
- Required evidence identifiers, reproduction commands, benign controls, and mutation sensitivity preserve information needed to audit both agents and graders.
- The `openai/evals` integration is an optional adapter because the repository remains useful for local/custom evaluation, while current hosted guidance is moving toward Datasets and trace/eval workflows.
