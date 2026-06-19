# /harden-tx-flow

Patch or design a production-grade Solana transaction send/confirm flow.

## Workflow

1. Use the `solana-tx-landing` skill.
2. Inspect the current transaction path and identify the SDK style: `@solana/web3.js`, `@solana/kit`, wallet adapter, backend sender, or custom RPC.
3. Run the TypeScript scanner:

   ```bash
   python3 scripts/scan_ts_transactions.py <repo> --format md
   python3 scripts/scan_ts_transactions.py <repo> --patch
   ```

   Use `--patch` to preview conservative automatic fixes. Use `--fix` only after reviewing the diff. If installed into `.agents`, use `.agents/skills/solana-tx-landing/scripts/scan_ts_transactions.py`.

4. Read only the references needed by the findings:
   - blockhash/confirmation issues: `skill/references/blockhash-and-confirmation.md`
   - RPC/retry issues: `skill/references/rpc-and-retry.md`
   - fee/compute issues: `skill/references/priority-fees-and-compute.md`
   - wallet/versioned transaction issues: `skill/references/wallet-and-versioned-tx.md`
   - Jito routing: `skill/references/jito-bundles.md`
5. Implement the smallest safe change consistent with the existing codebase.
6. Add or update tests around expiry, preflight error handling, and confirmation status where the repo has a test harness.

## Acceptance Criteria

- Fresh blockhash and `lastValidBlockHeight` are retained together.
- Confirmation uses blockheight strategy.
- Commitment/preflight commitment are explicit and aligned.
- The app has bounded resend or documented RPC retry behavior.
- Expiry rebuilds and resigns instead of mutating signed transactions.
- Priority fee and compute settings are intentional for production flows.
