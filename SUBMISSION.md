# Superteam Brasil Submission Draft

## Repo / PR Link

TODO: Add the public GitHub URL after pushing this repository.

Suggested repo name:

```text
solana-tx-landing-skill
```

## Project Name

Solana Tx Landing Skill

## Short Description

A Claude Code / Codex skill that diagnoses and hardens Solana transaction landing flows: blockhash expiry, confirmation strategy, priority fees, compute budget, RPC retry/failover, wallet latency, versioned transactions, simulation logs, and Jito routing.

## Problem

Solana teams often reach mainnet with transactions that work locally but fail in production: signatures are returned but never land, blockhashes expire after wallet approval, `Blockhash not found` appears during simulation, fees are mispriced, compute limits are guessed, and RPC pool lag turns a normal user action into a support incident. These problems are recurring, high-impact, and not covered well by a generic code audit.

## Solution

This skill gives coding agents a transaction-landing operating model. It routes from a compact `SKILL.md` into focused references, provides commands for diagnosis and hardening, and includes deterministic local scanners that inspect TypeScript transaction code, Rust/Anchor compute risks, and simulation logs. The agent can produce a concrete landing-readiness report with evidence, fixes, and verification steps.

## Why It Is Useful

- Founders can run it before launch to catch transaction UX and reliability failures.
- Engineers can use it during incidents to separate program errors from relay, blockhash, fee, and RPC issues.
- It complements existing Solana AI Kit security, DeFi, infra, and core dev skills instead of duplicating them.
- It is safe by default: no private keys, no signing, no transaction sending.

## What Is Included

- `skill/SKILL.md` progressive entrypoint
- Focused references for blockhash, confirmation, priority fees, compute, RPC retry, simulation logs, wallet/versioned tx, Jito, and readiness reports
- Commands: `/diagnose-tx`, `/harden-tx-flow`, `/tx-landing-report`
- Agent and rule files
- Offline deterministic scripts:
  - `scan_ts_transactions.py`
  - `parse_simulation_logs.py`
  - `scan_anchor_compute.py`
  - `tx_landing_report.py`
- Test fixtures and `scripts/validate.sh`
- GitHub Actions validation workflow
- MIT license and installer

## Install

```bash
./install.sh --agents --target /path/to/project
```

## Validation

```bash
bash scripts/validate.sh
```

Expected result:

```text
[OK] Repository validation complete
```

## License

MIT

