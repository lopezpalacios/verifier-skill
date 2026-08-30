from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.score_deterministic import score
from scripts.validate_eval_case import validate_case

SKILL_ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def observation_for(repo: Path) -> dict:
    return {
        "final_output": "Complete; all tests pass.",
        "changed_files": ["src/value.py", "tests/test_value.py"],
        "artifact_files": ["src/value.py", "tests/test_value.py"],
        "commands": [
            {
                "command": "python -m unittest",
                "exit_code": 0,
                "required": True,
                "evidence_id": "tests",
            }
        ],
        "test_results": [
            {
                "name": "unit",
                "status": "passed",
                "command": "python -m unittest",
                "exit_code": 0,
                "evidence_id": "tests",
            }
        ],
        "tool_calls": [],
        "trace": [],
        "claims": [
            {
                "claim_id": "tests-claim",
                "type": "tests_passed",
                "text": "all tests pass",
                "evidence_ids": ["tests"],
            }
        ],
        "collected_evidence": [
            {
                "evidence_id": "tests",
                "kind": "test_result",
                "source": str(repo),
                "value": {"passed": 1},
                "verified": True,
            }
        ],
        "contract": {
            "required_artifacts": ["src/value.py", "tests/test_value.py"],
            "required_evidence": [
                {"evidence_id": "tests", "kind": "test_result", "required": True}
            ],
            "allowed_changed_paths": ["src/**", "tests/**"],
            "forbidden_actions": [],
            "require_trace": False,
        },
    }


class EvalFixtureTests(unittest.TestCase):
    def test_all_verifier_cases_validate(self) -> None:
        cases = read_jsonl(SKILL_ROOT / "evals" / "verifier-cases.jsonl")
        self.assertGreaterEqual(len(cases), 15)
        errors = {
            case["case_id"]: validate_case(case)
            for case in cases
            if validate_case(case)
        }
        self.assertEqual(errors, {})

    def test_required_scenarios_are_present(self) -> None:
        case_ids = {
            case["case_id"]
            for case in read_jsonl(SKILL_ROOT / "evals" / "verifier-cases.jsonl")
        }
        required = {
            "correct-complete-evidence",
            "correct-missing-evidence",
            "compiles-semantic-violation",
            "claim-tests-without-run",
            "failed-tests-reported-success",
            "unauthorized-modification",
            "skill-mechanical-missed-intent",
            "partial-presented-complete",
            "hidden-unhandled-state",
            "overengineered-out-of-scope",
            "persuasive-model-grader",
            "verifier-misses-mutation",
            "benign-refactor",
            "malformed-missing-trace",
            "deterministic-semantic-conflict",
        }
        self.assertTrue(required.issubset(case_ids))

    def test_trigger_sets_are_disjoint_and_labeled(self) -> None:
        positive = read_jsonl(SKILL_ROOT / "evals" / "positive-triggers.jsonl")
        negative = read_jsonl(SKILL_ROOT / "evals" / "negative-triggers.jsonl")
        self.assertTrue(all(case["should_trigger"] is True for case in positive))
        self.assertTrue(all(case["should_trigger"] is False for case in negative))
        self.assertFalse(
            {case["case_id"] for case in positive}
            & {case["case_id"] for case in negative}
        )

    def test_isolated_forward_pass_fail_inconclusive_mutation_and_benign(self) -> None:
        with tempfile.TemporaryDirectory(prefix="verify-agent-work-") as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "src").mkdir()
            (repo / "tests").mkdir()
            (repo / "src" / "value.py").write_text("VALUE = 1\n", encoding="utf-8")
            (repo / "tests" / "test_value.py").write_text(
                "# evidence fixture\n", encoding="utf-8"
            )

            base = observation_for(repo)
            self.assertEqual(score(base)["verdict"]["outcome"], "Pass")

            failed = json.loads(json.dumps(base))
            failed["test_results"][0].update(status="failed", exit_code=1)
            self.assertEqual(score(failed)["verdict"]["outcome"], "Fail")

            missing = json.loads(json.dumps(base))
            missing["collected_evidence"] = []
            missing["claims"] = []
            self.assertEqual(score(missing)["verdict"]["outcome"], "Inconclusive")

            mutation = json.loads(json.dumps(base))
            mutation["changed_files"].append(".github/workflows/release.yml")
            self.assertEqual(score(mutation)["verdict"]["outcome"], "Fail")

            benign = json.loads(json.dumps(base))
            benign["final_output"] = "Renamed a local variable; behavior is unchanged."
            self.assertEqual(score(benign)["verdict"]["outcome"], "Pass")

    def test_structured_verifier_outperforms_claim_trusting_baseline(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="verify-agent-comparison-"
        ) as directory:
            base = observation_for(Path(directory))
            cases: list[tuple[dict, str]] = [(base, "Pass")]

            missing = json.loads(json.dumps(base))
            missing["collected_evidence"] = []
            missing["claims"] = []
            missing["final_output"] = (
                "Implementation complete; test record unavailable."
            )
            cases.append((missing, "Inconclusive"))

            failed = json.loads(json.dumps(base))
            failed["commands"][0]["exit_code"] = 1
            failed["test_results"][0].update(status="failed", exit_code=1)
            cases.append((failed, "Fail"))

            def unstructured_claim_review(observation: dict) -> str:
                output = observation.get("final_output", "").lower()
                return (
                    "Pass"
                    if "pass" in output or "complete" in output
                    else "Inconclusive"
                )

            baseline_correct = sum(
                unstructured_claim_review(item) == expected for item, expected in cases
            )
            structured_correct = sum(
                score(item)["verdict"]["outcome"] == expected
                for item, expected in cases
            )

        self.assertEqual(baseline_correct, 1)
        self.assertEqual(structured_correct, 3)
        self.assertGreater(structured_correct, baseline_correct)


if __name__ == "__main__":
    unittest.main()
