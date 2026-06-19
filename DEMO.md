# Demo

This demo uses the included offline fixtures. It does not require Solana RPC access, private keys, wallet signing, or network calls.

## 1. Validate The Repository

```bash
bash scripts/validate.sh
```

Expected result:

```text
[OK] Skill frontmatter is valid
[OK] Reference routing is complete
[OK] Python scripts compile without bytecode artifacts
[OK] Scanner fixtures produce expected findings
[OK] Shell helper syntax and project-local install work
[OK] No generated Python artifacts found
[OK] Repository validation complete
```

## 2. Diagnose Risky TypeScript Transaction Code

```bash
python3 scripts/scan_ts_transactions.py tests/fixtures/typescript --format md
```

What it catches:

- public RPC endpoint in a production-like sender
- `getLatestBlockhash()` without explicit commitment
- discarded `lastValidBlockHeight`
- `skipPreflight: true`
- `maxRetries: 0` without a rebroadcast loop
- signature-only confirmation

Example high finding:

```text
HIGH - signature-only-confirmation
Location: risky.ts:20
Recommendation: Use confirmTransaction({ signature, blockhash, lastValidBlockHeight }, commitment).
```

The hardened fixture is intentionally clean:

```bash
python3 scripts/scan_ts_transactions.py tests/fixtures/typescript/hardened.ts --format json
```

Expected summary:

```json
{
  "total": 0
}
```

## 3. Parse Simulation Logs

```bash
python3 scripts/parse_simulation_logs.py tests/fixtures/logs/simulation.log --format md
```

What it classifies:

- `Blockhash not found` as a blockhash/preflight/commitment issue
- `custom program error: 0x1771` as a program error that should be decoded before changing landing settings
- `unitsConsumed` as compute-budget evidence

## 4. Scan Anchor/Rust Compute Risks

```bash
python3 scripts/scan_anchor_compute.py tests/fixtures/rust --format md
```

What it catches:

- CPI inside a loop
- runtime logging in a hot loop
- CPI paths that need worst-case simulation

## 5. Generate A Combined Tx Landing Report

```bash
python3 scripts/tx_landing_report.py tests/fixtures --format md
```

Expected verdict for the intentionally risky fixture:

```text
Verdict: Not ready
Total findings: 13 (high: 5, medium: 5)
```

The report gives a launch-review style summary that an agent can turn into code fixes, verification steps, and residual-risk notes.

## 6. Use As An Agent Skill

Example prompts:

```text
Use solana-tx-landing to diagnose why this transaction expires after wallet approval.
```

```text
Run a tx landing report for this repo and propose the smallest safe changes.
```

```text
Parse these simulation logs and tell me whether this is compute, blockhash, account-lock, or program logic.
```

The skill routes from `skill/SKILL.md` to only the needed reference files, so the agent does not load every transaction-landing detail for every task.
