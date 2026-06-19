# /tx-landing-report

Generate a transaction landing readiness report for a Solana application.

## Workflow

1. Use the `solana-tx-landing` skill.
2. Run:

   ```bash
   python3 scripts/tx_landing_report.py <repo> --format md
   ```

   If installed into `.agents`, use `.agents/skills/solana-tx-landing/scripts/tx_landing_report.py`.

3. Read `skill/references/mainnet-readiness.md` and `skill/references/report-template.md`.
4. Inspect high-severity findings manually before finalizing the verdict.
5. Produce a concise report with:
   - verdict
   - top risks
   - evidence
   - recommended fixes
   - verification plan
   - residual risk

## Verdict Rules

- **Ready**: no high findings and monitoring/retry/fee policy are present.
- **Conditionally ready**: high finding has a contained mitigation or launch can proceed with reduced scope.
- **Not ready**: missing expiry handling, missing confirmation strategy, no observability, or critical flows cannot be inspected.
