#!/usr/bin/env python3
"""Diagnose a Solana transaction signature or saved getTransaction JSON."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import parse_simulation_logs  # noqa: E402


def rpc_call(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = urllib.request.Request(rpc_url, data=payload, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"RPC request failed: {exc}") from exc
    if "error" in data:
        raise RuntimeError(f"RPC error from {method}: {data['error']}")
    return data.get("result")


def load_transaction(args: argparse.Namespace) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    context: dict[str, Any] = {"source": "json" if args.from_json else "rpc"}
    if args.from_json:
        raw = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        result = raw.get("result", raw)
        signatures = (((result or {}).get("transaction") or {}).get("signatures") or []) if isinstance(result, dict) else []
        context["signature"] = args.signature or raw.get("signature") or (signatures[0] if signatures else None)
        return result, context

    if not args.rpc:
        raise SystemExit("Provide --from-json for offline diagnosis or --rpc for live read-only RPC diagnosis.")

    context["signature"] = args.signature
    tx = rpc_call(
        args.rpc,
        "getTransaction",
        [
            args.signature,
            {
                "encoding": "json",
                "commitment": args.commitment,
                "maxSupportedTransactionVersion": 0,
            },
        ],
    )
    status = rpc_call(args.rpc, "getSignatureStatuses", [[args.signature], {"searchTransactionHistory": True}])
    context["signature_status"] = (status or {}).get("value", [None])[0]
    try:
        context["current_block_height"] = rpc_call(args.rpc, "getBlockHeight", [{"commitment": args.commitment}])
    except RuntimeError:
        context["current_block_height"] = None
    return tx, context


def extract_message(transaction: dict[str, Any]) -> dict[str, Any]:
    tx = transaction.get("transaction") or {}
    if isinstance(tx, list):
        return {}
    message = tx.get("message") or {}
    if isinstance(message, dict):
        return message
    return {}


def diagnose(transaction: dict[str, Any] | None, context: dict[str, Any]) -> dict[str, Any]:
    if not transaction:
        return {
            "verdict": "Transaction not found",
            "confidence": "medium",
            "context": context,
            "evidence": [],
            "log_findings": [],
            "recommendations": [
                "Check the cluster/RPC endpoint and whether the signature is too old for the provider history window.",
                "If the app returned a signature but RPC cannot find it, inspect resend behavior, priority fees, and blockhash expiry.",
            ],
        }

    meta = transaction.get("meta") or {}
    message = extract_message(transaction)
    logs = meta.get("logMessages") or []
    err = meta.get("err")
    units = meta.get("computeUnitsConsumed")
    evidence: list[str] = [
        f"slot={transaction.get('slot')}",
        f"blockTime={transaction.get('blockTime')}",
        f"err={json.dumps(err)}",
    ]
    if units is not None:
        evidence.append(f"computeUnitsConsumed={units}")
    if message.get("recentBlockhash"):
        evidence.append(f"recentBlockhash={message.get('recentBlockhash')}")

    log_text = "\n".join(str(item) for item in logs)
    if err is not None:
        log_text += "\n" + json.dumps(err)
    if units is not None:
        log_text += f"\nunitsConsumed: {units}"
    findings = parse_simulation_logs.classify(log_text)

    if err is None:
        verdict = "Confirmed successfully"
        confidence = "high"
    elif findings:
        categories = ", ".join(sorted({item.category for item in findings if item.severity in {"high", "medium"}}))
        verdict = f"Runtime failure with {categories or 'classified'} evidence"
        confidence = "high"
    else:
        verdict = "Runtime failure; inspect program-specific error"
        confidence = "medium"

    recommendations = [
        "Do not change landing settings until program/runtime errors are separated from relay or expiry failures.",
        "Compare this signature with the client send path: blockhash fetch, simulation, wallet signing, send, resend, confirmation.",
    ]
    if any(item.category == "compute" for item in findings):
        recommendations.append("Set compute unit limit from simulation units plus margin and inspect CPI/loop-heavy paths.")
    if any(item.category == "blockhash" for item in findings):
        recommendations.append("Refresh blockhash close to signing and align preflight commitment with blockhash commitment.")
    if err is None:
        recommendations = ["Use this successful transaction as a baseline for CU, fee, writable accounts, and timing comparisons."]

    return {
        "verdict": verdict,
        "confidence": confidence,
        "context": context,
        "evidence": evidence,
        "log_findings": [asdict(item) for item in findings],
        "recommendations": recommendations,
    }


def render_markdown(report: dict[str, Any]) -> str:
    out = [
        "# Signature Diagnosis",
        "",
        f"Verdict: {report['verdict']}",
        f"Confidence: {report['confidence']}",
        "",
        "## Evidence",
        "",
    ]
    out.extend(f"- `{item}`" for item in report["evidence"])
    out.extend(["", "## Log Findings", ""])
    if report["log_findings"]:
        for finding in report["log_findings"]:
            out.extend(
                [
                    f"### {finding['severity'].upper()} - {finding['category']}",
                    "",
                    f"- Evidence: `{finding['evidence']}`",
                    f"- Recommendation: {finding['recommendation']}",
                    "",
                ]
            )
    else:
        out.append("No known log pattern matched.")
    out.extend(["", "## Recommendations", ""])
    out.extend(f"- {item}" for item in report["recommendations"])
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("signature", nargs="?", help="Transaction signature for live RPC diagnosis")
    parser.add_argument("--rpc", help="RPC URL for read-only live diagnosis")
    parser.add_argument("--from-json", help="Offline getTransaction JSON fixture")
    parser.add_argument("--commitment", default="confirmed", choices=["processed", "confirmed", "finalized"])
    parser.add_argument("--format", choices=["json", "md"], default="md")
    args = parser.parse_args()

    tx, context = load_transaction(args)
    report = diagnose(tx, context)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
