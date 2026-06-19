# Priority Fees And Compute

Primary sources:

- Solana fees: https://solana.com/docs/core/fees
- `getRecentPrioritizationFees`: https://solana.com/docs/rpc/http/getrecentprioritizationfees
- `simulateTransaction`: https://solana.com/docs/rpc/http/simulatetransaction

## Core Facts

- Prioritization fee is based on compute unit price and compute unit limit.
- The default compute limit can be too low or too high depending on instruction count and program behavior.
- Overstating the CU limit can overpay priority fees because price applies to the requested limit, not only consumed units.
- Fee markets are local to writable account contention. Query priority samples for the accounts the transaction locks writable when possible.

## Tuning Procedure

1. Simulate the exact transaction on the target cluster state.
2. Read `unitsConsumed` when available.
3. Set `ComputeBudgetProgram.setComputeUnitLimit` to observed units plus a margin. Start with 10-20% for stable flows; use more only when logs show variable CPI paths.
4. Query recent prioritization fees for writable hot accounts.
5. Set `ComputeBudgetProgram.setComputeUnitPrice` from a percentile appropriate for urgency.
6. Verify total fee impact before shipping.

## TypeScript Pattern

```ts
import { ComputeBudgetProgram } from "@solana/web3.js";

const computeIxs = [
  ComputeBudgetProgram.setComputeUnitLimit({ units: 320_000 }),
  ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 25_000 }),
];

const instructions = [...computeIxs, ...appInstructions];
```

Place compute-budget instructions before app instructions.

## Percentile Guidance

- Background/non-urgent: p50 local fee sample.
- Normal user action: p60-p75.
- Time-sensitive swap/liquidation/mint: p75-p90 plus a Jito path if appropriate.
- Emergency admin action: manually approve fee cap and routing path.

Do not hardcode a single global micro-lamport price forever. Add caps, telemetry, and fallback behavior.

## Program-Side Compute Clues

Investigate these when simulation consumes unexpectedly high units:

- Repeated CPI inside loops
- Large account reallocations
- Excessive `msg!` logging in hot paths
- Deserializing large accounts repeatedly
- PDA derivation inside loops
- Avoidable token account creation in user-critical transactions

