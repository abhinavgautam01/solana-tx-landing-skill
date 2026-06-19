#!/usr/bin/env python3
"""Generate a local Solana transaction landing readiness report."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import scan_anchor_compute  # noqa: E402
import scan_ts_transactions  # noqa: E402


SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}


def collect(root: Path) -> dict[str, object]:
    ts_findings = []
    for source_file in scan_ts_transactions.iter_source_files(root):
        ts_findings.extend(scan_ts_transactions.scan_file(source_file, root))

    rust_findings = []
    for source_file in scan_anchor_compute.iter_rust_files(root):
        rust_findings.extend(scan_anchor_compute.scan_file(source_file, root))

    all_findings = [("typescript", item) for item in ts_findings] + [("rust", item) for item in rust_findings]
    high = sum(1 for _, item in all_findings if item.severity == "high")
    medium = sum(1 for _, item in all_findings if item.severity == "medium")

    if high > 0:
        verdict = "Not ready"
    elif medium >= 3:
        verdict = "Conditionally ready"
    else:
        verdict = "Needs manual review" if all_findings else "No static blockers found"

    return {
        "verdict": verdict,
        "summary": {
            "typescript": scan_ts_transactions.summarize(ts_findings),
            "rust": scan_anchor_compute.summarize(rust_findings),
            "high": high,
            "medium": medium,
            "total": len(all_findings),
        },
        "findings": [
            {
                "area": area,
                **asdict(finding),
            }
            for area, finding in all_findings
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    summary = report["summary"]
    findings = report["findings"]
    out = [
        "# Tx Landing Report",
        "",
        f"Verdict: {report['verdict']}",
        f"Total findings: {summary['total']} (high: {summary['high']}, medium: {summary['medium']})",
        "",
        "## Top Findings",
        "",
    ]
    if not findings:
        out.extend(
            [
                "No static blockers found. This does not prove production readiness; verify runtime behavior, RPC health, priority fee policy, and monitoring.",
                "",
            ]
        )
    else:
        sorted_findings = sorted(
            findings,
            key=lambda item: (-SEVERITY_ORDER[item["severity"]], item["area"], item["path"], item["line"]),
        )
        for finding in sorted_findings[:20]:
            out.extend(
                [
                    f"### {finding['severity'].upper()} - {finding['rule']}",
                    "",
                    f"- Area: {finding['area']}",
                    f"- Location: `{finding['path']}:{finding['line']}`",
                    f"- Evidence: `{finding['evidence']}`",
                    f"- Recommendation: {finding['recommendation']}",
                    "",
                ]
            )

    out.extend(
        [
            "## Manual Verification",
            "",
            "- Confirm blockheight-based confirmation is used for every critical transaction.",
            "- Simulate critical transactions on target cluster state and record units consumed.",
            "- Verify priority-fee selection from recent writable-account fee samples.",
            "- Verify RPC slot lag monitoring and bounded rebroadcast until expiry.",
            "- Verify user-facing states for rejected, failed, pending, confirmed, and expired transactions.",
        ]
    )
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--format", choices=["json", "md"], default="md")
    args = parser.parse_args()

    report = collect(args.path.resolve())
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

