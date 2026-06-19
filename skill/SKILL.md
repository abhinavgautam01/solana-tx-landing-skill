---
name: solana-tx-landing
description: Diagnose and harden Solana transaction landing flows. Use when Codex needs to investigate failed, expired, slow, dropped, or inconsistently confirmed Solana transactions; tune blockhash, commitment, preflight, retry, RPC failover, priority fee, compute budget, wallet signing, versioned transaction, address lookup table, Jito bundle, or simulation-log workflows; or generate a mainnet transaction landing readiness report for a Solana app.
---

# Solana Tx Landing

Diagnose transaction landing as a production workflow, not as a single RPC error. Preserve user funds and signatures: do not request private keys, do not sign transactions, and do not send live transactions unless the user explicitly asks and the local tool policy allows it.

## Fast Route

1. Classify the input.
   - Failed signature or explorer link: inspect status, logs, slot timing, and whether the client has matching source.
   - Simulation logs: read `references/simulation-logs.md`.
   - TypeScript/frontend/backend transaction code: run `scripts/scan_ts_transactions.py`, then read the relevant references.
   - Anchor/Rust program compute concern: run `scripts/scan_anchor_compute.py`, then read `references/priority-fees-and-compute.md`.
   - Launch readiness request: run `scripts/tx_landing_report.py`, then read `references/mainnet-readiness.md`.
2. Build a timeline: blockhash fetched, transaction built, simulated, signed, sent, resent, confirmed, expired.
3. Check the highest-risk causes first: stale blockhash, commitment mismatch, missing resend loop, poor priority fee, excessive compute, RPC pool lag, and wallet latency.
4. Recommend the smallest concrete change that improves landing without hiding program bugs.

## References

- `references/triage-matrix.md`: error-to-cause routing for common landing failures.
- `references/blockhash-and-confirmation.md`: recent blockhash, last valid block height, confirmation strategy, durable nonce.
- `references/priority-fees-and-compute.md`: compute budget and priority-fee tuning.
- `references/rpc-and-retry.md`: RPC health, pool lag, resend, failover, `minContextSlot`, `maxRetries`.
- `references/simulation-logs.md`: interpreting simulation logs and program errors.
- `references/wallet-and-versioned-tx.md`: wallet signing, versioned transactions, address lookup tables.
- `references/jito-bundles.md`: Jito single transaction and bundle routing.
- `references/mainnet-readiness.md`: pre-launch checklist and report rubric.
- `references/report-template.md`: concise report format.

## Scripts

Run scripts from the repository root or from the installed skill directory. If the skill was installed into `.agents`, the scripts live at `.agents/skills/solana-tx-landing/scripts/`.

```bash
python3 scripts/scan_ts_transactions.py <repo-or-file> --format md
python3 scripts/parse_simulation_logs.py <log-file> --format md
python3 scripts/scan_anchor_compute.py <repo-or-file> --format md
python3 scripts/tx_landing_report.py <repo> --format md
```

For CI gates, use `--fail-on` with the TypeScript scanner:

```bash
python3 scripts/scan_ts_transactions.py <repo> --fail-on high
```

Use script output as evidence, not as a final answer by itself. Confirm findings against the source code because static scans are intentionally conservative.

## Output Standard

Return:

- A short verdict: likely cause and confidence.
- Evidence: file paths, line numbers, log excerpts, or RPC fields.
- Fix: exact code/config changes or a patch plan.
- Verification: how to prove the fix, including local tests, devnet/surfpool checks, or observability.
- Residual risk: what remains uncertain, especially if live RPC data was unavailable.
