# Jito Bundles

Primary source:

- Jito low latency transaction send: https://docs.jito.wtf/lowlatencytxnsend/

## When To Consider Jito

Use a Jito path for latency-sensitive, mainnet-only flows where ordinary RPC relay is insufficient:

- Liquidations
- High-value swaps
- Competitive mints
- Arbitrage or keeper flows
- Admin transactions that must land in a short window

Do not use Jito to paper over deterministic program failures. Simulate and fix those first.

## Operational Rules

- Use base64 encoding for submitted transactions.
- Budget both Solana priority fee and Jito tip. Jito documents a minimum tip for bundles, but high-demand periods may need more.
- Account for the fact that Jito's transaction send path can skip preflight. Run your own simulation before routing.
- Track bundle or transaction status separately from ordinary RPC submission.
- Rebuild and resign when the recent blockhash expires.
- Keep a non-Jito fallback unless the strategy explicitly depends on bundle semantics.

## Single Transaction Vs Bundle

- Single transaction path: useful when the transaction is independent but wants lower-latency leader forwarding.
- Bundle path: useful when multiple transactions must execute atomically or in order.
- `bundleOnly=true` can provide revert protection for a single transaction bundle, but it also changes routing assumptions. Confirm the product behavior before enabling.

## Failure Modes

- Tip too low for current auction
- Priority fee too low even with a tip
- Expired blockhash
- Bad base58/base64 encoding choice
- Bundle contains a transaction that fails simulation
- Bundle status monitoring missing

