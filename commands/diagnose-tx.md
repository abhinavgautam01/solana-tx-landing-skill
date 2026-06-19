# /diagnose-tx

Diagnose a failed, expired, slow, or dropped Solana transaction.

## Inputs

Accept any of:

- Transaction signature or explorer URL
- Simulation log file
- Error string
- Source file or repository path
- Natural-language symptom

## Workflow

1. Use the `solana-tx-landing` skill.
2. Classify the symptom with `skill/references/triage-matrix.md`.
3. If logs are provided, run:

   ```bash
   python3 scripts/parse_simulation_logs.py <log-file> --format md
   ```

   If installed into `.agents`, use `.agents/skills/solana-tx-landing/scripts/parse_simulation_logs.py`.

4. If source is provided, run:

   ```bash
   python3 scripts/scan_ts_transactions.py <path> --format md
   python3 scripts/scan_anchor_compute.py <path> --format md
   ```

   If installed into `.agents`, use the copies under `.agents/skills/solana-tx-landing/scripts/`.

5. Reconstruct the transaction lifecycle:
   - blockhash fetch
   - message construction
   - simulation
   - wallet signing
   - send/rebroadcast
   - confirmation or expiry
6. Return likely cause, evidence, smallest fix, verification plan, and residual risk.

## Do Not

- Ask for private keys.
- Treat `sendTransaction` success as final confirmation.
- Recommend `skipPreflight: true` as a first-line fix.
- Recommend indefinite retries after blockhash expiry.
