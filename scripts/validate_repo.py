#!/usr/bin/env python3
"""Validate the Solana Tx Landing skill repository."""

from __future__ import annotations

import json
import os
import re
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
    ok("Scanner fixtures produce expected findings")


def validate_installer() -> None:
    run(["bash", "-n", "install.sh"])
    with tempfile.TemporaryDirectory(prefix="solana-tx-landing-install-") as tmp:
        run(["bash", "install.sh", "--agents", "--target", tmp, "-y"])
        installed = Path(tmp) / ".agents" / "skills" / "solana-tx-landing" / "SKILL.md"
        if not installed.exists():
            fail("Installer did not copy skill/SKILL.md into .agents")
    ok("Installer syntax and project-local install work")


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

