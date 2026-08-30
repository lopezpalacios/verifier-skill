from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_eval_case import validate_case, validate_files


def valid_case() -> dict:
    return {
        "case_id": "case-1",
        "target_type": "agent_work",
        "prompt": "Verify the work.",
        "fixture": {"observation": {}},
        "contract": {"required_outcomes": ["done"]},
        "invariants": ["evidence is preserved"],
        "forbidden_actions": [],
        "required_evidence": [
            {"evidence_id": "tests", "kind": "test_result", "required": True}
        ],
        "expected_outcome": {"type": "Pass", "evidence": ["tests"]},
        "mutations": [
            {
                "mutation_id": "m-1",
                "operator": "drop-required-evidence",
                "target": "tests",
                "expected_effect": "Pass worsens to Inconclusive",
            }
        ],
        "tags": ["unit"],
    }


class ValidateEvalCaseTests(unittest.TestCase):
    def test_accepts_valid_case(self) -> None:
        self.assertEqual(validate_case(valid_case()), [])

    def test_rejects_missing_identifier_with_stable_message(self) -> None:
        case = valid_case()
        case["case_id"] = ""
        self.assertIn("$.case_id: expected nonempty string", validate_case(case))

    def test_rejects_malformed_typed_outcome(self) -> None:
        case = valid_case()
        case["expected_outcome"] = {"type": "Maybe", "evidence": []}
        self.assertEqual(
            validate_case(case),
            ["$.expected_outcome.type: expected one of Fail, Inconclusive, Pass"],
        )

    def test_malformed_union_tags_return_errors_instead_of_crashing(self) -> None:
        case = valid_case()
        case["target_type"] = []
        case["expected_outcome"] = {"type": []}
        errors = validate_case(case)
        self.assertIn(
            "$.target_type: expected one of agent_work, grader, skill", errors
        )
        self.assertIn(
            "$.expected_outcome.type: expected one of Fail, Inconclusive, Pass", errors
        )

    def test_rejects_incomplete_mutation_declaration(self) -> None:
        case = valid_case()
        case["mutations"] = [{"mutation_id": "m-1"}]
        errors = validate_case(case)
        self.assertIn("$.mutations[0].operator: missing required field", errors)
        self.assertIn(
            "$.mutations[0].expected_effect: expected nonempty string", errors
        )

    def test_rejects_undeclared_outcome_evidence(self) -> None:
        case = valid_case()
        case["expected_outcome"] = {"type": "Pass", "evidence": ["unknown"]}
        self.assertIn(
            "$.expected_outcome.evidence[0]: undeclared evidence identifier 'unknown'",
            validate_case(case),
        )

    def test_missing_union_payload_returns_error_instead_of_crashing(self) -> None:
        case = valid_case()
        case["expected_outcome"] = {"type": "Pass"}
        self.assertIn(
            "$.expected_outcome.evidence: missing required field", validate_case(case)
        )

    def test_rejects_duplicate_case_identifiers_across_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            encoded = json.dumps(valid_case())
            path.write_text(f"{encoded}\n{encoded}\n", encoding="utf-8")
            errors, count = validate_files([str(path)])
        self.assertEqual(count, 2)
        self.assertTrue(
            any("duplicate identifier 'case-1'" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
