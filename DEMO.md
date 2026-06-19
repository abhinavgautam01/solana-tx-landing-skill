# Demo

This demo is a complete offline walkthrough of the included fixtures. It does not require Solana RPC access, private keys, wallet signing, or network calls.

The story is intentionally simple: a transaction sender has common landing bugs, the skill diagnoses them, the scanner generates a conservative patch, and the after-scan shows which issues were fixed and which still need human configuration.

## 1. Validate The Repository

```bash
PYTHONDONTWRITEBYTECODE=1 bash scripts/validate.sh
```

Actual output:

```text
[OK] Skill frontmatter is valid
[OK] Reference routing is complete
[OK] Python scripts compile without bytecode artifacts
[OK] Scanner fixtures produce expected findings
[OK] Shell helper syntax and project-local install work
[OK] No generated Python artifacts found
[OK] Repository validation complete
```

## 2. Before: Diagnose A Risky Transaction Sender

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_ts_transactions.py tests/fixtures/typescript --format md
```

Actual output:

```md
# TypeScript Transaction Scan

Total findings: 10 (max severity: high)

## HIGH - missing-last-valid-block-height

- Location: `risky.ts:11`
- Evidence: `getLatestBlockhash is used but lastValidBlockHeight is not referenced in this file.`
- Recommendation: Retain blockhash and lastValidBlockHeight together and use blockheight-based confirmation.

## HIGH - discarded-last-valid-block-height

- Location: `risky.ts:11`
- Evidence: `tx.recentBlockhash = (await connection.getLatestBlockhash()).blockhash;`
- Recommendation: Do not keep only blockhash; preserve lastValidBlockHeight for expiry-aware confirmation.

## HIGH - skip-preflight-true

- Location: `risky.ts:15`
- Evidence: `const signature = await connection.sendRawTransaction(signed.serialize(), {`
- Recommendation: Keep preflight enabled during diagnosis; if skipping it, document the separate simulation path.

## HIGH - signature-only-confirmation

- Location: `risky.ts:20`
- Evidence: `return connection.confirmTransaction(signature);`
- Recommendation: Use confirmTransaction({ signature, blockhash, lastValidBlockHeight }, commitment).
```

The full scan also reports a public RPC endpoint, implicit blockhash commitment, missing preflight commitment, `maxRetries: 0` without a rebroadcast loop, no compute budget reference, and a legacy transaction note.

The hardened fixture is intentionally clean:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_ts_transactions.py tests/fixtures/typescript/hardened.ts --format json
```

Actual output:

```json
{
  "summary": {
    "counts": {
      "info": 0,
      "low": 0,
      "medium": 0,
      "high": 0
    },
    "max_severity": "info",
    "total": 0
  },
  "findings": []
}
```

## 3. Generate A Fix Plan

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_ts_transactions.py tests/fixtures/typescript --fix-plan
```

Actual output excerpt:

```md
# TypeScript Tx Landing Fix Plan

## HIGH - missing-last-valid-block-height

- Location: `risky.ts:11`
- Evidence: `getLatestBlockhash is used but lastValidBlockHeight is not referenced in this file.`
- Plan:
  - Thread `{ blockhash, lastValidBlockHeight }` through the send/confirm lifecycle.
  - Replace signature-only confirmation with `{ signature, blockhash, lastValidBlockHeight }`.

## HIGH - discarded-last-valid-block-height

- Location: `risky.ts:11`
- Evidence: `tx.recentBlockhash = (await connection.getLatestBlockhash()).blockhash;`
- Plan:
  - Store the full getLatestBlockhash response instead of only `.blockhash`.
  - Use `latest.blockhash` when building the transaction message.
  - Pass `latest.lastValidBlockHeight` into blockheight-based confirmation.

## HIGH - skip-preflight-true

- Plan:
  - Set `skipPreflight: false` while diagnosing and for normal user transactions.
  - If preflight must be skipped for a latency path, add an explicit simulation or Jito bundle validation path before send.
```

## 4. Preview The Patch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_ts_transactions.py tests/fixtures/typescript/risky.ts --patch
```

Actual output:

```diff
# TypeScript Tx Landing Patch

Preview only. Re-run with --fix to apply.

- risky.ts: Expanded getLatestBlockhash().blockhash into a latestBlockhash object with explicit confirmed commitment.
- risky.ts: Changed skipPreflight: true to skipPreflight: false.
- risky.ts: Added preflightCommitment: confirmed to send options.
- risky.ts: Replaced signature-only confirmation with blockheight-based confirmation.

--- a/risky.ts
+++ b/risky.ts
@@ -8,15 +8,24 @@
 export async function pay(wallet: any, ix: any) {
   const tx = new Transaction();
   tx.add(ix);
-  tx.recentBlockhash = (await connection.getLatestBlockhash()).blockhash;
+  const latestBlockhash = await connection.getLatestBlockhash("confirmed");
+  tx.recentBlockhash = latestBlockhash.blockhash;
   tx.feePayer = wallet.publicKey;

   const signed = await wallet.signTransaction(tx);
   const signature = await connection.sendRawTransaction(signed.serialize(), {
-    skipPreflight: true,
+    skipPreflight: false,
+    preflightCommitment: "confirmed",
     maxRetries: 0,
   });

-  return connection.confirmTransaction(signature);
+  return connection.confirmTransaction(
+    {
+      signature: signature,
+      blockhash: latestBlockhash.blockhash,
+      lastValidBlockHeight: latestBlockhash.lastValidBlockHeight,
+    },
+    "confirmed",
+  );
 }
```

## 5. Apply On A Temporary Copy And Re-Scan

This keeps the repository fixtures unchanged while proving the `--fix` path.

```bash
rm -rf /private/tmp/tx-demo-fix
mkdir -p /private/tmp/tx-demo-fix
cp tests/fixtures/typescript/risky.ts /private/tmp/tx-demo-fix/risky.ts
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_ts_transactions.py /private/tmp/tx-demo-fix/risky.ts --fix
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_ts_transactions.py /private/tmp/tx-demo-fix/risky.ts --format md
```

Actual after-scan output:

```md
# TypeScript Transaction Scan

Total findings: 4 (max severity: medium)

## MEDIUM - public-rpc-endpoint

- Location: `risky.ts:6`
- Evidence: `const connection = new Connection("https://api.mainnet-beta.solana.com");`
- Recommendation: Avoid relying on public RPC endpoints for production sends; configure provider health checks and failover.

## MEDIUM - max-retries-zero-without-loop

- Location: `risky.ts:16`
- Evidence: `const signature = await connection.sendRawTransaction(signed.serialize(), {`
- Recommendation: Only set maxRetries: 0 when the application owns a bounded rebroadcast loop until expiry.

## LOW - missing-compute-budget

- Location: `risky.ts:16`
- Evidence: `File sends transactions but does not reference ComputeBudgetProgram.`
- Recommendation: For production flows, simulate units consumed and set compute unit limit/price intentionally.

## INFO - legacy-transaction

- Location: `risky.ts:9`
- Evidence: `const tx = new Transaction();`
- Recommendation: Legacy transactions are valid, but check whether versioned transactions and ALTs are needed for account-heavy flows.
```

The patch resolves the high-severity blockhash, preflight, commitment, and confirmation bugs. It intentionally does not guess a production RPC provider, invent a rebroadcast loop, or add a compute budget without simulation data.

## 6. Parse Simulation Logs

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/parse_simulation_logs.py tests/fixtures/logs/simulation.log --format md
```

Actual output:

```md
# Simulation Log Diagnosis

Findings: 3

## MEDIUM - custom-program-error

- Line: 3
- Evidence: `Program log: custom program error: 0x1771`
- Meaning: A program returned a custom error.
- Recommendation: Decode the error with the Anchor IDL or program error map before changing landing settings.

## HIGH - blockhash

- Line: 5
- Evidence: `Error: Transaction simulation failed: Blockhash not found`
- Meaning: The simulation bank could not use the transaction blockhash, or the blockhash is stale.
- Recommendation: Use a fresh blockhash, align preflight commitment, and use replaceRecentBlockhash only for diagnosis.

## INFO - units-consumed

- Line: 1
- Evidence: `unitsConsumed=420000`
- Meaning: Simulation reported compute units consumed.
- Recommendation: Use this value to choose a compute unit limit with an explicit margin.
```

## 7. Scan Anchor/Rust Compute Risks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_anchor_compute.py tests/fixtures/rust --format md
```

Actual output:

```md
# Anchor/Rust Compute Scan

Total findings: 3 (max severity: high)

## HIGH - cpi-inside-loop

- Location: `lib.rs:5`
- Evidence: `for _ in 0..count {`
- Recommendation: CPI inside loops is a common source of compute spikes; bound the loop and simulate max size.

## MEDIUM - cpi-call

- Location: `lib.rs:7`
- Evidence: `invoke_signed(`
- Recommendation: CPI adds compute and account-lock complexity; simulate worst-case CPI paths.

## LOW - runtime-logging

- Location: `lib.rs:6`
- Evidence: `msg!("settling");`
- Recommendation: Keep logs useful but sparse in hot paths; excessive msg! calls add compute.
```

## 8. Generate A Combined Tx Landing Report

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tx_landing_report.py tests/fixtures --format md
```

Actual output excerpt:

```md
# Tx Landing Report

Verdict: Not ready
Total findings: 13 (high: 5, medium: 5)

## Top Findings

### HIGH - cpi-inside-loop

- Area: rust
- Location: `rust/lib.rs:5`
- Evidence: `for _ in 0..count {`
- Recommendation: CPI inside loops is a common source of compute spikes; bound the loop and simulate max size.

### HIGH - missing-last-valid-block-height

- Area: typescript
- Location: `typescript/risky.ts:11`
- Evidence: `getLatestBlockhash is used but lastValidBlockHeight is not referenced in this file.`
- Recommendation: Retain blockhash and lastValidBlockHeight together and use blockheight-based confirmation.

### HIGH - signature-only-confirmation

- Area: typescript
- Location: `typescript/risky.ts:20`
- Evidence: `return connection.confirmTransaction(signature);`
- Recommendation: Use confirmTransaction({ signature, blockhash, lastValidBlockHeight }, commitment).

## Manual Verification

- Confirm blockheight-based confirmation is used for every critical transaction.
- Simulate critical transactions on target cluster state and record units consumed.
- Verify priority-fee selection from recent writable-account fee samples.
- Verify RPC slot lag monitoring and bounded rebroadcast until expiry.
- Verify user-facing states for rejected, failed, pending, confirmed, and expired transactions.
```

## 9. Use The Scanner As A CI Gate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_ts_transactions.py tests/fixtures/typescript --fail-on high
```

Actual result: exits with code `2` because the risky fixture has high-severity findings. The command still prints the same markdown scan output shown in step 2, which makes the CI failure actionable.

## 10. Diagnose Saved Transaction JSON

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/diagnose_signature.py --from-json tests/fixtures/rpc/get_transaction_failed.json --format md
```

Actual output:

```md
# Signature Diagnosis

Verdict: Runtime failure with compute evidence
Confidence: high

## Evidence

- `slot=302000123`
- `blockTime=1781865600`
- `err={"InstructionError": [2, "ComputationalBudgetExceeded"]}`
- `computeUnitsConsumed=420000`
- `recentBlockhash=9xQeWvG816bUx9EPf9Q4vkF9jSU7J4Jf7s7Z7s7Z7s7Z`

## Log Findings

### HIGH - compute

- Evidence: `Program failed to complete: exceeded maximum number of instructions allowed (200000) at instruction #2`
- Recommendation: Read unitsConsumed, set a compute unit limit from simulation plus margin, and inspect CPI/loop-heavy code.

### INFO - units-consumed

- Evidence: `unitsConsumed=420000`
- Recommendation: Use this value to choose a compute unit limit with an explicit margin.

## Recommendations

- Do not change landing settings until program/runtime errors are separated from relay or expiry failures.
- Compare this signature with the client send path: blockhash fetch, simulation, wallet signing, send, resend, confirmation.
- Set compute unit limit from simulation units plus margin and inspect CPI/loop-heavy paths.
```

## 11. List MCP Tools

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mcp_server.py --list-tools
```

Actual tool names:

```text
scan_ts_transactions
parse_simulation_logs
scan_anchor_compute
tx_landing_report
diagnose_signature_json
```

The MCP server exposes the same offline scanners through stdio JSON-RPC for MCP-compatible agents.

## 12. Use As An Agent Skill

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

A truthful agent answer derived from the fixture outputs above would be:

```text
The main TypeScript landing bugs are discarded lastValidBlockHeight, signature-only confirmation, skipPreflight: true, and missing preflight commitment. The conservative patch can fix those high-severity issues by preserving latestBlockhash, using confirmed commitment, enabling preflight, and confirming with { signature, blockhash, lastValidBlockHeight }.

After that patch, the remaining risks are configuration or product-specific: replace the public RPC endpoint, either remove maxRetries: 0 or add a bounded rebroadcast loop, and add compute budget instructions only after simulation provides unitsConsumed.
```

The skill routes from `skill/SKILL.md` to only the needed reference files, so the agent does not load every transaction-landing detail for every task.
