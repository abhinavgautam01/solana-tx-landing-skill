# RPC And Retry

Primary sources:

- Solana confirmation guide: https://solana.com/developers/guides/advanced/confirmation
- `sendTransaction`: https://solana.com/docs/rpc/http/sendtransaction

## What To Verify

- Which RPC fetched the blockhash?
- Which RPC simulated the transaction?
- Which RPC sent or rebroadcast it?
- Which RPC checked signature status?
- Were all calls using compatible commitment?
- Was the sending node at or above the blockhash context slot?

## Healthy Send Loop

A production sender should:

1. Fetch a fresh blockhash and retain the response context when the SDK exposes it.
2. Sign once for that blockhash.
3. Send immediately.
4. Poll signature status.
5. Rebroadcast the same signed transaction until it confirms or the current block height exceeds `lastValidBlockHeight`.
6. On expiry, rebuild with a new blockhash and request a new signature.

Never change the blockhash after signing.

## RPC Pool Rules

- Prefer sticky routing for one transaction lifecycle when possible.
- If fetch and send endpoints differ, require send endpoint health checks.
- Use `minContextSlot` when the SDK path supports it to prevent sending through a node behind the blockhash context.
- Track slot lag with `getSlot` and `getMaxShredInsertSlot` where available.
- Avoid silently falling back from paid RPC to public RPC for production sends; public endpoints may be rate-limited or laggy.

## Retry Rules

- Retry transport errors with jitter until expiry.
- Do not retry program errors by resending the same failing transaction.
- Do not hide preflight errors by setting `skipPreflight: true` unless another simulation path is already protecting users.
- Use `maxRetries` intentionally. If set low or zero, own the rebroadcast loop.
- If using wallet adapter methods that send internally, verify whether the adapter exposes preflight, retries, and confirmation semantics.

