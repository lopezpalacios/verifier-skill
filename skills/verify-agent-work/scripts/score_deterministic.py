#!/usr/bin/env python3
"""Apply offline deterministic rules to a normalized agent-work observation."""

from __future__ import annotations

import argparse
import fnmatch
import json
import shlex
import sys
from pathlib import Path
from typing import Any

FAILURE_SEVERITIES = {"error", "critical"}
FAILED_TEST_STATUSES = {"failed", "error"}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _evidence_id(value: Any) -> str:
    return _text(value).strip()


def _finding(
    rule_id: str,
    severity: str,
    summary: str,
    expected: str,
    observed: str,
    evidence: list[str],
    reproduction: str,
    confidence: float = 1.0,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "summary": summary,
        "expected": expected,
        "observed": observed,
        "evidence": sorted(set(filter(None, evidence))),
        "reproduction": reproduction,
        "confidence": confidence,
    }


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _verified_evidence(observation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in _list(observation.get("collected_evidence")):
        if not isinstance(item, dict) or item.get("verified") is not True:
            continue
        evidence_id = _evidence_id(item.get("evidence_id"))
        if evidence_id:
            result[evidence_id] = item
    return result


def score(observation: Any) -> dict[str, Any]:
    """Return a typed deterministic partial verdict for any decoded JSON value."""
    if not isinstance(observation, dict):
        return {
            "scope": "deterministic",
            "findings": [],
            "verdict": {
                "outcome": "Inconclusive",
                "missing_evidence": ["normalized_observation"],
            },
        }

    findings: list[dict[str, Any]] = []
    missing: set[str] = set()
    contract_value = observation.get("contract")
    if isinstance(contract_value, dict):
        contract = contract_value
    else:
        contract = {}
        missing.add("contract")

    required_list_fields = (
        "changed_files",
        "artifact_files",
        "commands",
        "test_results",
        "tool_calls",
        "trace",
        "claims",
        "collected_evidence",
    )
    for field in required_list_fields:
        if field in observation and not isinstance(observation.get(field), list):
            missing.add(
                "trace" if field == "trace" else f"normalized_observation.{field}"
            )

    evidence = _verified_evidence(observation)
    if not evidence:
        missing.add("verified_evidence")

    declarations = _list(contract.get("required_evidence"))
    for declaration in declarations:
        if isinstance(declaration, str):
            evidence_id = declaration.strip()
            required = True
        elif isinstance(declaration, dict):
            evidence_id = _evidence_id(declaration.get("evidence_id"))
            required = declaration.get("required", True) is True
        else:
            continue
        if required and evidence_id and evidence_id not in evidence:
            missing.add(evidence_id)

    artifacts = {
        _text(path) for path in _list(observation.get("artifact_files")) if _text(path)
    }
    for required in _list(contract.get("required_artifacts")):
        required_path = _text(required)
        if not required_path:
            continue
        if not any(fnmatch.fnmatchcase(path, required_path) for path in artifacts):
            findings.append(
                _finding(
                    "REP-001",
                    "error",
                    "Required artifact is absent",
                    required_path,
                    "not present in artifact_files",
                    ["artifact_files"],
                    f"test -e {shlex.quote(required_path)}",
                )
            )

    allowed_patterns = [
        _text(pattern)
        for pattern in _list(contract.get("allowed_changed_paths"))
        if _text(pattern)
    ]
    if allowed_patterns:
        for changed_path in sorted(
            {
                _text(path)
                for path in _list(observation.get("changed_files"))
                if _text(path)
            }
        ):
            if not _matches_any(changed_path, allowed_patterns):
                findings.append(
                    _finding(
                        "AUTH-001",
                        "critical",
                        "Changed path is outside the authorized scope",
                        f"one of {allowed_patterns}",
                        changed_path,
                        ["diff"],
                        f"git diff -- {shlex.quote(changed_path)}",
                    )
                )

    commands = [
        item for item in _list(observation.get("commands")) if isinstance(item, dict)
    ]
    for command in commands:
        if command.get("required") is not True:
            continue
        command_text = _text(command.get("command")) or "<unknown command>"
        evidence_id = _evidence_id(command.get("evidence_id"))
        exit_code = command.get("exit_code")
        if not isinstance(exit_code, int):
            missing.add(evidence_id or f"exit_status:{command_text}")
        elif exit_code != 0:
            findings.append(
                _finding(
                    "DET-002",
                    "error",
                    "Required command failed",
                    "exit code 0",
                    f"exit code {exit_code}",
                    [evidence_id or "commands"],
                    command_text,
                )
            )

    test_results = [
        item
        for item in _list(observation.get("test_results"))
        if isinstance(item, dict)
    ]
    tests_by_evidence = {
        _evidence_id(item.get("evidence_id")): item
        for item in test_results
        if _evidence_id(item.get("evidence_id"))
    }
    for test in test_results:
        status = _text(test.get("status")).lower()
        exit_code = test.get("exit_code")
        if status in FAILED_TEST_STATUSES or (
            isinstance(exit_code, int) and exit_code != 0
        ):
            evidence_id = _evidence_id(test.get("evidence_id"))
            findings.append(
                _finding(
                    "DET-003",
                    "error",
                    "Recorded test run failed",
                    "status passed and exit code 0",
                    f"status {status or '<missing>'}, exit code {exit_code!r}",
                    [evidence_id or "test_results"],
                    _text(test.get("command")) or "rerun the recorded test command",
                )
            )

    for claim in _list(observation.get("claims")):
        if not isinstance(claim, dict) or claim.get("type") != "tests_passed":
            continue
        claim_id = _evidence_id(claim.get("claim_id")) or "tests_passed claim"
        referenced_ids = [
            _evidence_id(item)
            for item in _list(claim.get("evidence_ids"))
            if _evidence_id(item)
        ]
        supported = False
        for referenced_id in referenced_ids:
            test = tests_by_evidence.get(referenced_id)
            evidence_item = evidence.get(referenced_id)
            if (
                test
                and _text(test.get("status")).lower() == "passed"
                and test.get("exit_code") == 0
                and evidence_item
                and evidence_item.get("kind") == "test_result"
            ):
                supported = True
                break
        if not supported:
            findings.append(
                _finding(
                    "DET-004",
                    "error",
                    "Test-passed claim lacks a verified successful run",
                    "a cited test_result with status passed and exit code 0",
                    f"unsupported claim {claim_id}",
                    referenced_ids or ["claims"],
                    "rerun the claimed test command and retain its exit status",
                )
            )

    forbidden = [
        _text(action).casefold()
        for action in _list(contract.get("forbidden_actions"))
        if _text(action)
    ]
    observed_actions: list[tuple[str, str, str]] = []
    for command in commands:
        observed_actions.append(
            (
                _text(command.get("command")).casefold(),
                _evidence_id(command.get("evidence_id")) or "commands",
                _text(command.get("command")) or "inspect command log",
            )
        )
    for tool_call in _list(observation.get("tool_calls")):
        if isinstance(tool_call, dict):
            action = _text(tool_call.get("action")).casefold()
            observed_actions.append(
                (
                    action,
                    _evidence_id(tool_call.get("evidence_id")) or "tool_calls",
                    "inspect recorded tool call",
                )
            )
    for forbidden_action in forbidden:
        for action, evidence_id, reproduction in observed_actions:
            if action and forbidden_action in action:
                findings.append(
                    _finding(
                        "AUTH-002",
                        "critical",
                        "Explicitly forbidden action was recorded",
                        f"no action matching {forbidden_action!r}",
                        action,
                        [evidence_id],
                        reproduction,
                    )
                )

    if contract.get("require_trace") is True:
        trace = observation.get("trace")
        if not isinstance(trace, list) or not trace:
            missing.add("trace")

    failure_findings = [
        finding for finding in findings if finding["severity"] in FAILURE_SEVERITIES
    ]
    verified_ids = sorted(evidence)
    if failure_findings:
        verdict: dict[str, Any] = {
            "outcome": "Fail",
            "findings": failure_findings,
            "evidence": verified_ids,
        }
    elif missing:
        verdict = {"outcome": "Inconclusive", "missing_evidence": sorted(missing)}
    else:
        verdict = {"outcome": "Pass", "evidence": verified_ids}
    return {"scope": "deterministic", "findings": findings, "verdict": verdict}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "observation", help="normalized observation JSON file, or - for stdin"
    )
    args = parser.parse_args(argv)
    try:
        if args.observation == "-":
            value = json.load(sys.stdin)
        else:
            with Path(args.observation).open(encoding="utf-8") as handle:
                value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read normalized observation: {exc}", file=sys.stderr)
        return 2
    json.dump(score(value), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
