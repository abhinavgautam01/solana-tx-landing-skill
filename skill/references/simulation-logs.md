# Simulation Logs

Use simulation logs to separate runtime/program failures from landing/transport failures.

## Classification

| Log/error pattern | Meaning | Action |
| --- | --- | --- |
| `Blockhash not found` | Simulation bank cannot see the transaction blockhash or it is stale | Align commitment; use fresh blockhash; try `replaceRecentBlockhash` for diagnosis |
| `ComputationalBudgetExceeded` | CU limit exceeded | Simulate for units, add CU limit, optimize program |
| `custom program error: 0x...` | Program returned a custom error | Decode against Anchor IDL or program error map |
| `insufficient funds` | Fee payer or token account lacks funds | Check lamports for base + priority fee and rent |
| `AccountNotFound` | Missing account or wrong cluster/address | Verify account derivation and cluster |
| `AccountInUse` | Writable account lock contention | Reduce hot writable locks or improve priority fee |
| `Program failed to complete` | Usually compute, panic, or unbounded path | Inspect preceding logs |
| `SlippageToleranceExceeded` / slippage text | App-level route moved | Requote and rebuild transaction |

## Evidence To Preserve

- Full `err` object
- `logs`
- `unitsConsumed`
- `replacementBlockhash` if used
- RPC endpoint and commitment
- Transaction message account list, especially writable accounts

## Response Pattern

When answering from logs:

1. Quote only short log fragments needed to identify the issue.
2. State whether the transaction reached runtime.
3. Identify the failing instruction index if visible.
4. Separate landing fix from program/app fix.
5. Provide the next command or code inspection needed.

