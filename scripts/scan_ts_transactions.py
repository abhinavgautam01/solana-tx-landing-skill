#!/usr/bin/env python3
"""Scan TypeScript/JavaScript Solana transaction code for landing risks."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {
    ".git",
    ".next",
    ".turbo",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}
EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}


@dataclass
class Finding:
    severity: str
    rule: str
    path: str
    line: int
    evidence: str
    recommendation: str


def iter_source_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix in EXTENSIONS:
            yield root
        return

    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in EXTENSIONS:
            yield path


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root if root.is_dir() else root.parent))
    except ValueError:
        return str(path)


def window(lines: list[str], index: int, size: int = 6) -> str:
    return "\n".join(lines[index : min(len(lines), index + size)])


def first_matching_line(lines: list[str], pattern: str) -> int:
    for index, line in enumerate(lines, 1):
        if re.search(pattern, line):
            return index
    return 1


def has_rebroadcast_logic(text: str) -> bool:
    patterns = [
        r"while\s*\(",
        r"setInterval\s*\(",
        r"setTimeout\s*\(",
        r"for\s*\(",
        r"getSignatureStatuses",
        r"lastValidBlockHeight",
        r"TransactionExpiredBlockheightExceededError",
    ]
    return sum(1 for pattern in patterns if re.search(pattern, text)) >= 2


def scan_file(path: Path, root: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    findings: list[Finding] = []
    file_label = rel(path, root)
    has_send = bool(re.search(r"\b(sendRawTransaction|sendTransaction|sendAndConfirmTransaction)\b", text))
    has_compute_budget = bool(re.search(r"ComputeBudgetProgram|setComputeUnit|getSetComputeUnit", text))
    has_simulation = "simulateTransaction" in text
    rebroadcast = has_rebroadcast_logic(text)

    if "https://api.mainnet-beta.solana.com" in text or "https://api.devnet.solana.com" in text:
        for i, line in enumerate(lines, 1):
            if "api.mainnet-beta.solana.com" in line or "api.devnet.solana.com" in line:
                findings.append(
                    Finding(
                        "medium",
                        "public-rpc-endpoint",
                        file_label,
                        i,
                        line.strip(),
                        "Avoid relying on public RPC endpoints for production sends; configure provider health checks and failover.",
                    )
                )

    if has_send and not has_compute_budget:
        findings.append(
            Finding(
                "low",
                "missing-compute-budget",
                file_label,
                first_matching_line(lines, r"\b(sendRawTransaction|sendTransaction|sendAndConfirmTransaction)\b"),
                "File sends transactions but does not reference ComputeBudgetProgram.",
                "For production flows, simulate units consumed and set compute unit limit/price intentionally.",
            )
        )

    if has_send and "getLatestBlockhash" in text and "lastValidBlockHeight" not in text:
        findings.append(
            Finding(
                "high",
                "missing-last-valid-block-height",
                file_label,
                first_matching_line(lines, r"getLatestBlockhash"),
                "getLatestBlockhash is used but lastValidBlockHeight is not referenced in this file.",
                "Retain blockhash and lastValidBlockHeight together and use blockheight-based confirmation.",
            )
        )

    for index, line in enumerate(lines):
        line_no = index + 1
        stripped = line.strip()

        if "getLatestBlockhash" in line:
            call = window(lines, index, 4)
            if not re.search(r"['\"](?:confirmed|processed|finalized)['\"]", call):
                findings.append(
                    Finding(
                        "medium",
                        "implicit-blockhash-commitment",
                        file_label,
                        line_no,
                        stripped,
                        "Pass an explicit commitment, usually 'confirmed', when fetching a blockhash.",
                    )
                )
            if re.search(r"getLatestBlockhash\s*\([^)]*\)\s*\)?\.blockhash", call):
                findings.append(
                    Finding(
                        "high",
                        "discarded-last-valid-block-height",
                        file_label,
                        line_no,
                        stripped,
                        "Do not keep only blockhash; preserve lastValidBlockHeight for expiry-aware confirmation.",
                    )
                )

        if re.search(r"\bconfirmTransaction\s*\(\s*[A-Za-z_$][\w$]*\s*[,)]", line):
            findings.append(
                Finding(
                    "high",
                    "signature-only-confirmation",
                    file_label,
                    line_no,
                    stripped,
                    "Use confirmTransaction({ signature, blockhash, lastValidBlockHeight }, commitment).",
                )
            )

        if "sendAndConfirmTransaction" in line:
            findings.append(
                Finding(
                    "medium",
                    "send-and-confirm-abstraction",
                    file_label,
                    line_no,
                    stripped,
                    "Review whether this abstraction exposes blockheight confirmation, preflight commitment, retries, and expiry handling.",
                )
            )

        if re.search(r"\b(sendRawTransaction|sendTransaction)\s*\(", line):
            call = window(lines, index, 8)
            if "skipPreflight" in call and re.search(r"skipPreflight\s*:\s*true", call):
                severity = "medium" if has_simulation else "high"
                findings.append(
                    Finding(
                        severity,
                        "skip-preflight-true",
                        file_label,
                        line_no,
                        stripped,
                        "Keep preflight enabled during diagnosis; if skipping it, document the separate simulation path.",
                    )
                )
            if "preflightCommitment" not in call:
                findings.append(
                    Finding(
                        "medium",
                        "missing-preflight-commitment",
                        file_label,
                        line_no,
                        stripped,
                        "Set preflightCommitment to match the commitment used for getLatestBlockhash.",
                    )
                )
            if re.search(r"maxRetries\s*:\s*0", call) and not rebroadcast:
                findings.append(
                    Finding(
                        "medium",
                        "max-retries-zero-without-loop",
                        file_label,
                        line_no,
                        stripped,
                        "Only set maxRetries: 0 when the application owns a bounded rebroadcast loop until expiry.",
                    )
                )

        if re.search(r"new\s+Transaction\s*\(", line):
            findings.append(
                Finding(
                    "info",
                    "legacy-transaction",
                    file_label,
                    line_no,
                    stripped,
                    "Legacy transactions are valid, but check whether versioned transactions and ALTs are needed for account-heavy flows.",
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
    out = [
        "# TypeScript Transaction Scan",
        "",
        f"Total findings: {summary['total']} (max severity: {summary['max_severity']})",
        "",
    ]
    if not findings:
        out.append("No transaction landing risks found by static scan.")
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


FIX_PLAN_BY_RULE = {
    "discarded-last-valid-block-height": [
        "Store the full getLatestBlockhash response instead of only `.blockhash`.",
        "Use `latest.blockhash` when building the transaction message.",
        "Pass `latest.lastValidBlockHeight` into blockheight-based confirmation.",
    ],
    "missing-last-valid-block-height": [
        "Thread `{ blockhash, lastValidBlockHeight }` through the send/confirm lifecycle.",
        "Replace signature-only confirmation with `{ signature, blockhash, lastValidBlockHeight }`.",
    ],
    "signature-only-confirmation": [
        "Replace `confirmTransaction(signature)` with `confirmTransaction({ signature, blockhash, lastValidBlockHeight }, commitment)`.",
        "Use the same commitment as blockhash fetch unless the code documents a different consistency policy.",
    ],
    "skip-preflight-true": [
        "Set `skipPreflight: false` while diagnosing and for normal user transactions.",
        "If preflight must be skipped for a latency path, add an explicit simulation or Jito bundle validation path before send.",
    ],
    "missing-preflight-commitment": [
        "Add `preflightCommitment` to send options.",
        "Match it to the commitment used by `getLatestBlockhash`, usually `confirmed`.",
    ],
    "max-retries-zero-without-loop": [
        "Either remove `maxRetries: 0` and let the RPC retry, or add a bounded rebroadcast loop.",
        "Stop rebroadcasting once the current block height exceeds `lastValidBlockHeight`.",
    ],
    "missing-compute-budget": [
        "Simulate the transaction to collect `unitsConsumed`.",
        "Prepend compute budget instructions with an explicit CU limit and CU price for production flows.",
    ],
    "public-rpc-endpoint": [
        "Move RPC URLs into environment/configuration.",
        "Use a production RPC provider with slot-lag monitoring and failover for sends.",
    ],
}


def render_fix_plan(findings: list[Finding]) -> str:
    actionable = [finding for finding in findings if finding.rule in FIX_PLAN_BY_RULE]
    out = ["# TypeScript Tx Landing Fix Plan", ""]
    if not actionable:
        out.append("No known fix-plan rules matched. Review findings manually.")
        return "\n".join(out)

    for finding in sorted(actionable, key=lambda item: (-SEVERITY_ORDER[item.severity], item.path, item.line)):
        out.extend(
            [
                f"## {finding.severity.upper()} - {finding.rule}",
                "",
                f"- Location: `{finding.path}:{finding.line}`",
                f"- Evidence: `{finding.evidence}`",
                "- Plan:",
            ]
        )
        out.extend(f"  - {step}" for step in FIX_PLAN_BY_RULE[finding.rule])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="File or directory to scan")
    parser.add_argument("--format", choices=["json", "md"], default="md")
    parser.add_argument("--fail-on", choices=["info", "low", "medium", "high"], help="Exit 2 if this severity or higher is found")
    parser.add_argument("--fix-plan", action="store_true", help="Print a remediation plan for known findings instead of the normal scan report")
    args = parser.parse_args()

    root = args.path.resolve()
    findings: list[Finding] = []
    for source_file in iter_source_files(root):
        findings.extend(scan_file(source_file, root))

    if args.fix_plan:
        print(render_fix_plan(findings))
    elif args.format == "json":
        print(json.dumps({"summary": summarize(findings), "findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print(render_markdown(findings))

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[item.severity] >= threshold for item in findings):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
