#!/usr/bin/env python3
"""Validate verify-agent-work JSONL cases without network access."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "case_id",
    "target_type",
    "prompt",
    "fixture",
    "contract",
    "invariants",
    "forbidden_actions",
    "required_evidence",
    "expected_outcome",
    "mutations",
    "tags",
)
TARGET_TYPES = {"skill", "agent_work", "grader"}
OUTCOME_FIELDS = {
    "Pass": {"type", "evidence"},
    "Fail": {"type", "finding_rules", "evidence"},
    "Inconclusive": {"type", "missing_evidence"},
}
MUTATION_FIELDS = {"mutation_id", "operator", "target", "expected_effect"}
EVIDENCE_FIELDS = {"evidence_id", "kind", "required"}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string_list(value: Any, path: str, *, unique: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{path}: expected array"]
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _is_nonempty_string(item):
            errors.append(f"{item_path}: expected nonempty string")
        elif unique and item in seen:
            errors.append(f"{item_path}: duplicate value {item!r}")
        else:
            seen.add(item)
    return errors


def validate_case(case: Any) -> list[str]:
    """Return stable schema errors for one decoded case."""
    if not isinstance(case, dict):
        return ["$: expected object"]

    errors = [
        f"$.{field}: missing required field"
        for field in REQUIRED_FIELDS
        if field not in case
    ]
    if errors:
        return errors

    if not _is_nonempty_string(case["case_id"]):
        errors.append("$.case_id: expected nonempty string")
    if (
        not isinstance(case["target_type"], str)
        or case["target_type"] not in TARGET_TYPES
    ):
        errors.append("$.target_type: expected one of agent_work, grader, skill")
    if not _is_nonempty_string(case["prompt"]):
        errors.append("$.prompt: expected nonempty string")
    if not isinstance(case["fixture"], (str, dict)) or case["fixture"] == "":
        errors.append("$.fixture: expected nonempty string or object")
    if not isinstance(case["contract"], dict):
        errors.append("$.contract: expected object")

    errors.extend(_validate_string_list(case["invariants"], "$.invariants"))
    errors.extend(
        _validate_string_list(case["forbidden_actions"], "$.forbidden_actions")
    )
    errors.extend(_validate_string_list(case["tags"], "$.tags", unique=True))

    evidence_ids: set[str] = set()
    evidence = case["required_evidence"]
    if not isinstance(evidence, list):
        errors.append("$.required_evidence: expected array")
    else:
        for index, declaration in enumerate(evidence):
            path = f"$.required_evidence[{index}]"
            if not isinstance(declaration, dict):
                errors.append(f"{path}: expected object")
                continue
            missing = sorted(EVIDENCE_FIELDS - declaration.keys())
            extra = sorted(declaration.keys() - EVIDENCE_FIELDS)
            for field in missing:
                errors.append(f"{path}.{field}: missing required field")
            if extra:
                errors.append(f"{path}: unexpected fields {', '.join(extra)}")
            evidence_id = declaration.get("evidence_id")
            if not _is_nonempty_string(evidence_id):
                errors.append(f"{path}.evidence_id: expected nonempty string")
            elif evidence_id in evidence_ids:
                errors.append(
                    f"{path}.evidence_id: duplicate identifier {evidence_id!r}"
                )
            else:
                evidence_ids.add(evidence_id)
            if not _is_nonempty_string(declaration.get("kind")):
                errors.append(f"{path}.kind: expected nonempty string")
            if not isinstance(declaration.get("required"), bool):
                errors.append(f"{path}.required: expected boolean")

    outcome = case["expected_outcome"]
    if not isinstance(outcome, dict):
        errors.append("$.expected_outcome: expected typed object")
    else:
        outcome_type = outcome.get("type")
        if not isinstance(outcome_type, str) or outcome_type not in OUTCOME_FIELDS:
            errors.append(
                "$.expected_outcome.type: expected one of Fail, Inconclusive, Pass"
            )
        else:
            expected_fields = OUTCOME_FIELDS[outcome_type]
            missing = sorted(expected_fields - outcome.keys())
            extra = sorted(outcome.keys() - expected_fields)
            for field in missing:
                errors.append(f"$.expected_outcome.{field}: missing required field")
            if extra:
                errors.append(
                    f"$.expected_outcome: unexpected fields {', '.join(extra)}"
                )
            list_field = {
                "Pass": "evidence",
                "Fail": "finding_rules",
                "Inconclusive": "missing_evidence",
            }[outcome_type]
            values = outcome.get(list_field)
            errors.extend(
                _validate_string_list(
                    values, f"$.expected_outcome.{list_field}", unique=True
                )
            )
            if isinstance(values, list) and not values:
                errors.append(
                    f"$.expected_outcome.{list_field}: expected at least one item"
                )
            if outcome_type == "Fail":
                outcome_evidence = outcome.get("evidence")
                errors.extend(
                    _validate_string_list(
                        outcome_evidence, "$.expected_outcome.evidence", unique=True
                    )
                )
                if isinstance(outcome_evidence, list) and not outcome_evidence:
                    errors.append(
                        "$.expected_outcome.evidence: expected at least one item"
                    )
            evidence_field = (
                "missing_evidence" if outcome_type == "Inconclusive" else "evidence"
            )
            declared_outcome_evidence = outcome.get(evidence_field)
            for index, evidence_id in enumerate(
                declared_outcome_evidence
                if isinstance(declared_outcome_evidence, list)
                else []
            ):
                if _is_nonempty_string(evidence_id) and evidence_id not in evidence_ids:
                    errors.append(
                        f"$.expected_outcome.{evidence_field}[{index}]: undeclared evidence identifier {evidence_id!r}"
                    )

    mutations = case["mutations"]
    mutation_ids: set[str] = set()
    if not isinstance(mutations, list):
        errors.append("$.mutations: expected array")
    else:
        for index, mutation in enumerate(mutations):
            path = f"$.mutations[{index}]"
            if not isinstance(mutation, dict):
                errors.append(f"{path}: expected object")
                continue
            missing = sorted(MUTATION_FIELDS - mutation.keys())
            extra = sorted(mutation.keys() - MUTATION_FIELDS)
            for field in missing:
                errors.append(f"{path}.{field}: missing required field")
            if extra:
                errors.append(f"{path}: unexpected fields {', '.join(extra)}")
            for field in sorted(MUTATION_FIELDS):
                if not _is_nonempty_string(mutation.get(field)):
                    errors.append(f"{path}.{field}: expected nonempty string")
            mutation_id = mutation.get("mutation_id")
            if _is_nonempty_string(mutation_id):
                if mutation_id in mutation_ids:
                    errors.append(
                        f"{path}.mutation_id: duplicate identifier {mutation_id!r}"
                    )
                mutation_ids.add(mutation_id)

    return errors


def _iter_lines(path: str) -> Iterable[tuple[int, str]]:
    if path == "-":
        yield from enumerate(sys.stdin, start=1)
        return
    with Path(path).open(encoding="utf-8") as handle:
        yield from enumerate(handle, start=1)


def validate_files(paths: list[str]) -> tuple[list[str], int]:
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    case_count = 0
    for path in paths:
        try:
            lines = list(_iter_lines(path))
        except OSError as exc:
            errors.append(f"{path}: cannot read: {exc.strerror or exc}")
            continue
        for line_number, raw in lines:
            if not raw.strip():
                continue
            location = f"{path}:{line_number}"
            try:
                case = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"{location}: invalid JSON: {exc.msg} at column {exc.colno}"
                )
                continue
            case_count += 1
            for error in validate_case(case):
                errors.append(f"{location}: {error}")
            if isinstance(case, dict) and _is_nonempty_string(case.get("case_id")):
                case_id = case["case_id"]
                if case_id in seen_ids:
                    errors.append(
                        f"{location}: $.case_id: duplicate identifier {case_id!r}; first at {seen_ids[case_id]}"
                    )
                else:
                    seen_ids[case_id] = location
    return errors, case_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files", nargs="+", help="JSONL files to validate, or - for stdin"
    )
    args = parser.parse_args(argv)
    errors, case_count = validate_files(args.files)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(
            f"INVALID: {len(errors)} error(s) across {case_count} case(s)",
            file=sys.stderr,
        )
        return 1
    print(f"VALID: {case_count} case(s) across {len(args.files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
