#!/usr/bin/env python3
"""Validate the Solana Tx Landing skill repository."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REFERENCES = {
    "triage-matrix.md",
    "blockhash-and-confirmation.md",
    "priority-fees-and-compute.md",
    "rpc-and-retry.md",
    "simulation-logs.md",
    "wallet-and-versioned-tx.md",
    "jito-bundles.md",
    "mainnet-readiness.md",
    "report-template.md",
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def run(args: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        fail(f"Command failed: {' '.join(args)}")
    return result


def validate_skill_frontmatter() -> None:
    skill = ROOT / "skill" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("skill/SKILL.md must start with YAML frontmatter")
    try:
        _, frontmatter, _ = text.split("---", 2)
    except ValueError:
        fail("skill/SKILL.md frontmatter is not closed")

    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()

    if fields.get("name") != "solana-tx-landing":
        fail("skill/SKILL.md name must be solana-tx-landing")
    description = fields.get("description", "")
    required_terms = ["failed", "expired", "priority fee", "compute budget", "Jito"]
    missing = [term for term in required_terms if term.lower() not in description.lower()]
    if missing:
        fail(f"skill description is missing trigger terms: {', '.join(missing)}")
    ok("Skill frontmatter is valid")


def validate_references() -> None:
    reference_dir = ROOT / "skill" / "references"
    refs = {path.name for path in reference_dir.glob("*.md")}
    missing = EXPECTED_REFERENCES - refs
    if missing:
        fail(f"Missing reference files: {', '.join(sorted(missing))}")

    skill_text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    unlinked = [name for name in EXPECTED_REFERENCES if name not in skill_text]
    if unlinked:
        fail(f"SKILL.md does not route to references: {', '.join(sorted(unlinked))}")
    ok("Reference routing is complete")


def validate_python_sources() -> None:
    for path in sorted((ROOT / "scripts").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    ok("Python scripts compile without bytecode artifacts")


def validate_scanners() -> None:
    ts = run(["python3", "scripts/scan_ts_transactions.py", "tests/fixtures/typescript", "--format", "json"])
    ts_report = json.loads(ts.stdout)
    ts_rules = {finding["rule"] for finding in ts_report["findings"]}
    for rule in {"signature-only-confirmation", "skip-preflight-true", "discarded-last-valid-block-height"}:
        if rule not in ts_rules:
            fail(f"TypeScript scanner did not emit expected rule: {rule}")

    hardened = run(["python3", "scripts/scan_ts_transactions.py", "tests/fixtures/typescript/hardened.ts", "--format", "json"])
    hardened_report = json.loads(hardened.stdout)
    if hardened_report["summary"]["total"] != 0:
        fail("Hardened TypeScript fixture should have no static findings")

    kit = run(["python3", "scripts/scan_ts_transactions.py", "tests/fixtures/typescript/kit_v2.ts", "--format", "json"])
    kit_report = json.loads(kit.stdout)
    if kit_report["summary"]["total"] != 0:
        fail("@solana/kit v2 fixture should have no static findings")

    fix_plan = run(["python3", "scripts/scan_ts_transactions.py", "tests/fixtures/typescript", "--fix-plan"])
    if "signature-only-confirmation" not in fix_plan.stdout or "lastValidBlockHeight" not in fix_plan.stdout:
        fail("TypeScript scanner fix plan did not include expected remediation steps")

    patch = run(["python3", "scripts/scan_ts_transactions.py", "tests/fixtures/typescript/risky.ts", "--patch"])
    if "preflightCommitment" not in patch.stdout or "latestBlockhash" not in patch.stdout:
        fail("TypeScript scanner patch preview did not include expected fixes")

    with tempfile.TemporaryDirectory(prefix="solana-tx-fix-") as tmp:
        target = Path(tmp) / "risky.ts"
        target.write_text((ROOT / "tests" / "fixtures" / "typescript" / "risky.ts").read_text(encoding="utf-8"), encoding="utf-8")
        run(["python3", "scripts/scan_ts_transactions.py", str(target), "--fix"])
        fixed = json.loads(run(["python3", "scripts/scan_ts_transactions.py", str(target), "--format", "json"]).stdout)
        if fixed["summary"]["counts"]["high"] != 0:
            fail("TypeScript scanner --fix should remove high-severity fixture findings")

    logs = run(["python3", "scripts/parse_simulation_logs.py", "tests/fixtures/logs/simulation.log", "--format", "json"])
    log_categories = {finding["category"] for finding in json.loads(logs.stdout)["findings"]}
    for category in {"blockhash", "custom-program-error", "units-consumed"}:
        if category not in log_categories:
            fail(f"Simulation log parser did not emit expected category: {category}")

    rust = run(["python3", "scripts/scan_anchor_compute.py", "tests/fixtures/rust", "--format", "json"])
    rust_rules = {finding["rule"] for finding in json.loads(rust.stdout)["findings"]}
    if "cpi-inside-loop" not in rust_rules:
        fail("Rust scanner did not emit expected cpi-inside-loop rule")

    combined = run(["python3", "scripts/tx_landing_report.py", "tests/fixtures", "--format", "json"])
    report = json.loads(combined.stdout)
    if report["verdict"] != "Not ready":
        fail("Combined fixture report should be Not ready")

    signature = run(["python3", "scripts/diagnose_signature.py", "--from-json", "tests/fixtures/rpc/get_transaction_failed.json", "--format", "json"])
    signature_report = json.loads(signature.stdout)
    if "compute" not in signature_report["verdict"]:
        fail("Signature diagnoser did not classify fixture as compute-related")

    mcp_tools = run(["python3", "scripts/mcp_server.py", "--list-tools"])
    if "scan_ts_transactions" not in mcp_tools.stdout or "diagnose_signature_json" not in mcp_tools.stdout:
        fail("MCP server did not list expected tools")

    mcp_call = run(
        [
            "bash",
            "-lc",
            "printf '%s\\n' '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"scan_ts_transactions\",\"arguments\":{\"path\":\"tests/fixtures/typescript/risky.ts\",\"format\":\"json\"}}}' | PYTHONDONTWRITEBYTECODE=1 python3 scripts/mcp_server.py --line-mode",
        ]
    )
    if "signature-only-confirmation" not in mcp_call.stdout:
        fail("MCP server scanner call did not return expected finding")
    ok("Scanner fixtures produce expected findings")


def validate_installer() -> None:
    run(["bash", "-n", "install.sh"])
    run(["bash", "-n", "scripts/publish_github.sh"])
    with tempfile.TemporaryDirectory(prefix="solana-tx-landing-install-") as tmp:
        run(["bash", "install.sh", "--agents", "--target", tmp, "-y"])
        skill_dir = Path(tmp) / ".agents" / "skills" / "solana-tx-landing"
        if not (skill_dir / "SKILL.md").exists():
            fail("Installer did not copy skill/SKILL.md into .agents")
        for script in {
            "diagnose_signature.py",
            "mcp_server.py",
            "parse_simulation_logs.py",
            "scan_anchor_compute.py",
            "scan_ts_transactions.py",
            "tx_landing_report.py",
        }:
            if not (skill_dir / "scripts" / script).exists():
                fail(f"Installer did not copy runtime script: {script}")
        installed_scan = run(
            [
                "python3",
                str(skill_dir / "scripts" / "scan_ts_transactions.py"),
                str(ROOT / "tests" / "fixtures" / "typescript" / "risky.ts"),
                "--format",
                "json",
            ]
        )
        if "signature-only-confirmation" not in installed_scan.stdout:
            fail("Installed TypeScript scanner did not run correctly")
    ok("Shell helper syntax and project-local install work")


def validate_no_generated_artifacts() -> None:
    generated = list(ROOT.rglob("__pycache__")) + list(ROOT.rglob("*.pyc"))
    if generated:
        fail("Generated Python cache artifacts found: " + ", ".join(str(path) for path in generated))
    ok("No generated Python artifacts found")


def main() -> int:
    validate_skill_frontmatter()
    validate_references()
    validate_python_sources()
    validate_scanners()
    validate_installer()
    validate_no_generated_artifacts()
    print("[OK] Repository validation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
