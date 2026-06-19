#!/usr/bin/env python3
"""Classify Solana simulation logs and RPC error text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Finding:
    severity: str
    category: str
    line: int
    evidence: str
    explanation: str
    recommendation: str


PATTERNS: list[tuple[str, str, str, str, str]] = [
    (
        "high",
        "blockhash",
        r"blockhash not found|BlockhashNotFound",
        "The simulation bank could not use the transaction blockhash, or the blockhash is stale.",
        "Use a fresh blockhash, align preflight commitment, and use replaceRecentBlockhash only for diagnosis.",
    ),
    (
        "high",
        "compute",
        r"ComputationalBudgetExceeded|exceeded CUs|exceeded maximum number of instructions|Program failed to complete",
        "The transaction likely exceeded its compute budget or hit an unbounded program path.",
        "Read unitsConsumed, set a compute unit limit from simulation plus margin, and inspect CPI/loop-heavy code.",
    ),
    (
        "medium",
        "account-lock",
        r"AccountInUse|account in use|would exceed max account cost limit",
        "The transaction is contending on writable accounts or account cost limits.",
        "Identify hot writable accounts, reduce lock contention, and price the local fee market.",
    ),
    (
        "medium",
        "funding",
        r"insufficient funds|InsufficientFunds|Attempt to debit an account",
        "The fee payer or token account may not cover fees, rent, or transfer amount.",
        "Check lamports for base fee, priority fee, rent exemption, and token balances.",
    ),
    (
        "medium",
        "missing-account",
        r"AccountNotFound|InvalidAccountData|could not find account",
        "An account is missing, wrong for this cluster, or has unexpected data.",
        "Verify cluster, PDA derivation, account creation order, and lookup table contents.",
    ),
    (
        "medium",
        "slippage",
        r"slippage|Slippage|price impact|ExceededSlippage",
        "The route or quote moved before execution.",
        "Requote, rebuild, and resign close to send time; do not keep stale swap transactions.",
    ),
    (
        "medium",
        "custom-program-error",
        r"custom program error:\s*(0x[0-9a-fA-F]+|\d+)",
        "A program returned a custom error.",
        "Decode the error with the Anchor IDL or program error map before changing landing settings.",
    ),
]


def read_input(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def classify(text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines() or [text]
    for line_no, line in enumerate(lines, 1):
        for severity, category, pattern, explanation, recommendation in PATTERNS:
            if re.search(pattern, line, flags=re.IGNORECASE):
                findings.append(Finding(severity, category, line_no, line.strip(), explanation, recommendation))

    units = re.search(r"unitsConsumed['\"]?\s*[:=]\s*(\d+)", text)
    if units:
        findings.append(
            Finding(
                "info",
                "units-consumed",
                1,
                f"unitsConsumed={units.group(1)}",
                "Simulation reported compute units consumed.",
                "Use this value to choose a compute unit limit with an explicit margin.",
            )
        )

    instruction = re.search(r"Instruction(?:Error)?\((\d+)", text)
    if instruction:
        findings.append(
            Finding(
                "info",
                "instruction-index",
                1,
                f"instruction index {instruction.group(1)}",
                "The error points to a specific instruction index.",
                "Map the index to the transaction instruction list before patching.",
            )
        )

    return findings


def summary(findings: list[Finding]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def render_markdown(findings: list[Finding]) -> str:
    out = ["# Simulation Log Diagnosis", "", f"Findings: {len(findings)}", ""]
    if not findings:
        out.append("No known simulation-log pattern matched. Inspect the full RPC error and program logs manually.")
        return "\n".join(out)

    for finding in findings:
        out.extend(
            [
                f"## {finding.severity.upper()} - {finding.category}",
                "",
                f"- Line: {finding.line}",
                f"- Evidence: `{finding.evidence}`",
                f"- Meaning: {finding.explanation}",
                f"- Recommendation: {finding.recommendation}",
                "",
            ]
        )
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Log file path, or '-' / omitted for stdin")
    parser.add_argument("--format", choices=["json", "md"], default="md")
    args = parser.parse_args()

    findings = classify(read_input(args.path))
    if args.format == "json":
        print(json.dumps({"summary": summary(findings), "findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print(render_markdown(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

