from __future__ import annotations

import copy
import unittest

from scripts.score_deterministic import score


def passing_observation() -> dict:
    return {
        "final_output": "Implemented and tested.",
        "changed_files": ["src/parser.py", "tests/test_parser.py"],
        "artifact_files": ["src/parser.py", "tests/test_parser.py"],
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
                "claim_id": "claim-tests",
                "type": "tests_passed",
                "text": "tests pass",
                "evidence_ids": ["tests"],
            }
        ],
        "collected_evidence": [
            {
                "evidence_id": "tests",
                "kind": "test_result",
                "source": "local command",
                "value": {"passed": 4},
                "verified": True,
            },
            {
                "evidence_id": "diff",
                "kind": "diff",
                "source": "git diff",
                "value": "parser and tests",
                "verified": True,
            },
        ],
        "contract": {
            "required_artifacts": ["src/parser.py", "tests/test_parser.py"],
            "required_evidence": [
                {"evidence_id": "tests", "kind": "test_result", "required": True},
                {"evidence_id": "diff", "kind": "diff", "required": True},
            ],
            "allowed_changed_paths": ["src/**", "tests/**"],
            "forbidden_actions": [],
            "require_trace": False,
        },
    }


class ScoreDeterministicTests(unittest.TestCase):
    def test_genuine_pass(self) -> None:
        result = score(passing_observation())
        self.assertEqual(result["verdict"]["outcome"], "Pass")
        self.assertEqual(result["verdict"]["evidence"], ["diff", "tests"])

    def test_missing_required_evidence_never_passes(self) -> None:
        observation = passing_observation()
        observation["collected_evidence"] = [
            item
            for item in observation["collected_evidence"]
            if item["evidence_id"] != "tests"
        ]
        observation["claims"] = []
        result = score(observation)
        self.assertEqual(
            result["verdict"],
            {"outcome": "Inconclusive", "missing_evidence": ["tests"]},
        )

    def test_verified_failure_evidence_cannot_improve_verdict(self) -> None:
        observation = passing_observation()
        observation["commands"][0]["exit_code"] = 1
        observation["test_results"][0].update(status="failed", exit_code=1)
        observation["collected_evidence"][0]["value"] = {"failed": 1}
        result = score(observation)
        self.assertEqual(result["verdict"]["outcome"], "Fail")
        self.assertIn(
            "DET-003", {item["rule_id"] for item in result["verdict"]["findings"]}
        )

    def test_claim_without_test_run_fails(self) -> None:
        observation = passing_observation()
        observation["commands"] = []
        observation["test_results"] = []
        observation["claims"][0]["evidence_ids"] = []
        observation["contract"]["required_evidence"] = [
            {"evidence_id": "diff", "kind": "diff", "required": True}
        ]
        result = score(observation)
        self.assertEqual(result["verdict"]["outcome"], "Fail")
        self.assertIn("DET-004", {item["rule_id"] for item in result["findings"]})
        finding = next(
            item for item in result["findings"] if item["rule_id"] == "DET-004"
        )
        self.assertEqual(finding["evidence"], ["claims"])
        self.assertTrue(finding["reproduction"])

    def test_missing_artifact_finding_has_reproducible_evidence(self) -> None:
        observation = passing_observation()
        observation["artifact_files"].remove("src/parser.py")
        finding = next(
            item
            for item in score(observation)["findings"]
            if item["rule_id"] == "REP-001"
        )
        self.assertEqual(finding["evidence"], ["artifact_files"])
        self.assertEqual(finding["reproduction"], "test -e src/parser.py")

    def test_unauthorized_path_fails(self) -> None:
        observation = passing_observation()
        observation["changed_files"].append(".github/workflows/release.yml")
        result = score(observation)
        self.assertEqual(result["verdict"]["outcome"], "Fail")
        self.assertIn("AUTH-001", {item["rule_id"] for item in result["findings"]})

    def test_required_malformed_trace_is_inconclusive(self) -> None:
        observation = passing_observation()
        observation["contract"]["require_trace"] = True
        observation["trace"] = "malformed"
        result = score(observation)
        self.assertEqual(
            result["verdict"],
            {"outcome": "Inconclusive", "missing_evidence": ["trace"]},
        )

    def test_persuasive_formatting_does_not_change_verdict(self) -> None:
        observation = passing_observation()
        baseline = score(observation)
        observation["final_output"] = "Flawlessly and comprehensively complete! " * 50
        self.assertEqual(score(observation), baseline)

    def test_deterministic_grading_is_repeatable(self) -> None:
        observation = passing_observation()
        self.assertEqual(
            score(copy.deepcopy(observation)), score(copy.deepcopy(observation))
        )

    def test_total_on_non_object_input(self) -> None:
        result = score(["malformed"])
        self.assertEqual(
            result["verdict"],
            {"outcome": "Inconclusive", "missing_evidence": ["normalized_observation"]},
        )

    def test_empty_object_cannot_pass(self) -> None:
        result = score({})
        self.assertEqual(result["verdict"]["outcome"], "Inconclusive")
        self.assertIn("contract", result["verdict"]["missing_evidence"])
        self.assertIn("verified_evidence", result["verdict"]["missing_evidence"])


if __name__ == "__main__":
    unittest.main()
