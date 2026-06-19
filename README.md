# Solana Tx Landing Skill

Production-grade Claude Code / Codex skill for diagnosing and hardening Solana transaction landing flows.

Solana builders repeatedly hit the same mainnet failure modes: a transaction simulates but never lands, expires after wallet signing, gets dropped by an RPC, fails with `Blockhash not found`, burns too much compute, or needs priority-fee and Jito routing tuned under load. This skill turns an agent into a transaction-landing reviewer that can inspect a repo, parse simulation logs, identify risky client patterns, and generate a concrete remediation report.

## What It Solves

- Blockhash expiration and stale confirmation logic
- Commitment/preflight mismatches across `getLatestBlockhash`, simulation, send, and confirmation
- Missing or poorly tuned `ComputeBudgetProgram` instructions
- Priority fee selection using local fee markets and writable account sets
- RPC pool lag, retry, failover, `minContextSlot`, and `maxRetries` issues
- Wallet signing latency and blockhash refresh problems
- Versioned transaction and address lookup table pitfalls
- Jito bundle/tip routing for latency-sensitive transactions
- Anchor/Rust program patterns that contribute to compute spikes

## Why This Belongs In Solana AI Kit

The Solana AI Kit already covers broad development, security, DeFi, infra, and ecosystem routing. Tx landing is a narrower production problem that cuts across all of them. It is frequent enough that founders ask for it during launches, but specific enough that a dedicated skill can give sharper guidance than a generic audit.

This repo follows the reference skill shape:

```text
solana-tx-landing-skill/
├── skill/
│   ├── SKILL.md
│   └── references/
├── commands/
├── agents/
├── rules/
├── scripts/
├── tests/fixtures/
├── install.sh
├── README.md
└── LICENSE
```

## Install

Install the skill and optional commands into a Claude-style config directory:

```bash
./install.sh
```

Install into a project-local `.agents/` directory for Codex-compatible agent setups:

```bash
./install.sh --agents --target /path/to/project
```

Install only the skill:

```bash
./install.sh --skill-only --target /path/to/project/.agents
```

The installer copies plain text files only. It does not download dependencies, execute remote code, or modify shell profiles.

The runtime scanner scripts are installed into the skill folder at `skills/solana-tx-landing/scripts/`, so the installed skill remains usable without keeping a separate clone of this repository.

## Usage

Ask the agent natural questions:

```text
Use solana-tx-landing to diagnose why this payment transaction expires after wallet approval.
```

```text
Run a tx landing report for this repo and propose the smallest safe changes.
```

```text
Parse these simulation logs and tell me whether this is compute, blockhash, account-lock, or program logic.
```

Command workflows:

- `/diagnose-tx` - triage a failed signature, simulation log, or repo transaction flow
- `/harden-tx-flow` - patch risky client send/confirm/retry patterns
- `/tx-landing-report` - generate a launch-readiness report for transaction landing

Deterministic scripts:

```bash
python3 scripts/scan_ts_transactions.py path/to/app --format md
python3 scripts/parse_simulation_logs.py path/to/simulation.log --format md
python3 scripts/scan_anchor_compute.py path/to/programs --format md
python3 scripts/tx_landing_report.py path/to/repo --format md
```

For CI, the TypeScript scanner can fail builds when findings meet a severity threshold:

```bash
python3 scripts/scan_ts_transactions.py path/to/app --fail-on high
```

To turn known findings into a remediation checklist without rewriting source files:

```bash
python3 scripts/scan_ts_transactions.py path/to/app --fix-plan
```

For a quick offline walkthrough, see `DEMO.md`.

## Validate

Run the complete offline validation suite:

```bash
bash scripts/validate.sh
```

The validator checks skill frontmatter/routing, Python script syntax, scanner fixture behavior, installer syntax, project-local install behavior, and absence of generated artifacts. The GitHub Actions workflow runs the same command on pushes and pull requests.

## Current References

The references are grounded in primary docs current as of June 19, 2026:

- Solana transaction confirmation and expiration: https://solana.com/developers/guides/advanced/confirmation
- Solana fees and compute budget: https://solana.com/docs/core/fees
- Solana `sendTransaction`: https://solana.com/docs/rpc/http/sendtransaction
- Solana `simulateTransaction`: https://solana.com/docs/rpc/http/simulatetransaction
- Solana `getLatestBlockhash`: https://solana.com/docs/rpc/http/getlatestblockhash
- Solana `getRecentPrioritizationFees`: https://solana.com/docs/rpc/http/getrecentprioritizationfees
- Jito low latency transaction send: https://docs.jito.wtf/lowlatencytxnsend/

## Quality Bar

- Progressive loading: `SKILL.md` routes to focused references instead of loading all detail.
- Deterministic checks: scripts emit JSON or Markdown and do not require network access.
- Safe defaults: no private key handling, no signing, no sending transactions.
- Merge fit: MIT licensed, shell installer, plain Markdown commands/agents/rules.
