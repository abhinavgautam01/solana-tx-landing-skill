#!/usr/bin/env python3
"""Scan Rust/Anchor programs for compute-heavy transaction risks."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {".git", "target", "node_modules"}
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}


@dataclass
class Finding:
    severity: str
    rule: str
    path: str
    line: int
    evidence: str
    recommendation: str


def iter_rust_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix == ".rs":
            yield root
        return
    for path in root.rglob("*.rs"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root if root.is_dir() else root.parent))
    except ValueError:
        return str(path)


def scan_file(path: Path, root: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    findings: list[Finding] = []
    label = rel(path, root)

    for index, line in enumerate(lines):
        line_no = index + 1
        stripped = line.strip()

        if "msg!(" in line:
            findings.append(
                Finding(
                    "low",
                    "runtime-logging",
                    label,
                    line_no,
                    stripped,
                    "Keep logs useful but sparse in hot paths; excessive msg! calls add compute.",
                )
            )

        if re.search(r"\brealloc\s*\(", line):
            findings.append(
                Finding(
                    "medium",
                    "account-realloc",
                    label,
                    line_no,
                    stripped,
                    "Large or frequent reallocations can spike compute and rent requirements; measure this path.",
                )
            )

        if re.search(r"\binvoke_signed?\s*\(", line):
            findings.append(
                Finding(
                    "medium",
                    "cpi-call",
                    label,
                    line_no,
                    stripped,
                    "CPI adds compute and account-lock complexity; simulate worst-case CPI paths.",
                )
            )

        if "find_program_address" in line:
            findings.append(
                Finding(
                    "low",
                    "pda-derivation",
                    label,
                    line_no,
                    stripped,
                    "Repeated PDA derivation can add compute; avoid doing it inside loops.",
                )
            )

        if re.search(r"\b(for|while)\b", line):
            block = "\n".join(lines[index : min(len(lines), index + 25)])
            if re.search(r"\binvoke_signed?\s*\(", block):
                findings.append(
                    Finding(
                        "high",
                        "cpi-inside-loop",
                        label,
                        line_no,
                        stripped,
                        "CPI inside loops is a common source of compute spikes; bound the loop and simulate max size.",
                    )
                )
            elif "msg!(" in block or "find_program_address" in block:
                findings.append(
                    Finding(
                        "medium",
                        "compute-work-inside-loop",
                        label,
                        line_no,
                        stripped,
                        "Logging or PDA work inside loops can make compute variable; simulate worst-case inputs.",
                    )
                )

    return findings


def summarize(findings: list[Finding]) -> dict[str, object]:
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        counts[finding.severity] += 1
    max_severity = "info"
    for finding in findings:
        if SEVERITY_ORDER[finding.severity] > SEVERITY_ORDER[max_severity]:
            max_severity = finding.severity
    return {"counts": counts, "max_severity": max_severity, "total": len(findings)}


def render_markdown(findings: list[Finding]) -> str:
    summary = summarize(findings)
    out = ["# Anchor/Rust Compute Scan", "", f"Total findings: {summary['total']} (max severity: {summary['max_severity']})", ""]
    if not findings:
        out.append("No compute-heavy Rust patterns found by static scan.")
        return "\n".join(out)

    for finding in sorted(findings, key=lambda item: (-SEVERITY_ORDER[item.severity], item.path, item.line)):
        out.extend(
            [
                f"## {finding.severity.upper()} - {finding.rule}",
                "",
                f"- Location: `{finding.path}:{finding.line}`",
                f"- Evidence: `{finding.evidence}`",
                f"- Recommendation: {finding.recommendation}",
                "",
            ]
        )
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--format", choices=["json", "md"], default="md")
    args = parser.parse_args()

    root = args.path.resolve()
    findings: list[Finding] = []
    for source_file in iter_rust_files(root):
        findings.extend(scan_file(source_file, root))

    if args.format == "json":
        print(json.dumps({"summary": summarize(findings), "findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print(render_markdown(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

