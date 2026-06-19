# Blockhash And Confirmation

Primary sources:

- Solana confirmation guide: https://solana.com/developers/guides/advanced/confirmation
- `getLatestBlockhash`: https://solana.com/docs/rpc/http/getlatestblockhash
- `sendTransaction`: https://solana.com/docs/rpc/http/sendtransaction

## Invariants

- A Solana transaction uses a recent blockhash as a short-lived timestamp.
- The app must retain both `blockhash` and `lastValidBlockHeight` from `getLatestBlockhash`.
- Confirmation should use the blockheight strategy: signature, blockhash, and last valid block height.
- Fetch blockhashes with `confirmed` for most app flows unless the user has a specific reason to trade freshness against fork risk.
- Set `preflightCommitment` to the same commitment used to fetch the blockhash.
- Treat a `sendTransaction` signature as RPC relay acceptance only. It is not confirmation.

## Good Client Shape

```ts
const latest = await connection.getLatestBlockhash("confirmed");

const message = new TransactionMessage({
  payerKey: payer,
  recentBlockhash: latest.blockhash,
  instructions,
}).compileToV0Message(addressLookupTables);

const tx = new VersionedTransaction(message);
// sign or wallet.signTransaction(tx)

const signature = await connection.sendRawTransaction(tx.serialize(), {
  skipPreflight: false,
  preflightCommitment: "confirmed",
  maxRetries: 0,
});

await connection.confirmTransaction(
  {
    signature,
    blockhash: latest.blockhash,
    lastValidBlockHeight: latest.lastValidBlockHeight,
  },
  "confirmed",
);
```

`maxRetries: 0` is acceptable only if the app owns its own rebroadcast loop. If the app does not rebroadcast, let the RPC retry or implement a bounded resend loop.

## Blockhash Freshness Checklist

- Fetch blockhash after the user has chosen the action and all slow off-chain preparation is complete.
- Do not cache one blockhash globally for many user actions.
- If wallet signing can take more than a few seconds, refresh immediately before signing where wallet APIs allow it.
- On expiry, rebuild and resign. Do not mutate a signed transaction blockhash.
- If using multiple RPC endpoints, avoid fetching blockhash from a fast node and sending through a lagging node unless `minContextSlot` and health checks are in place.
- For offline signing or long approval flows, evaluate durable nonce instead of stretching recent blockhash assumptions.

## Common Bad Patterns

```ts
await connection.confirmTransaction(signature);
```

Signature-only confirmation hides expiry context and is fragile in modern apps.

```ts
const blockhash = (await connection.getLatestBlockhash()).blockhash;
// user takes 45 seconds to approve...
await wallet.signTransaction(tx);
```

The transaction may be close to expiry before it is even sent.

```ts
await connection.sendRawTransaction(raw, { skipPreflight: true });
```

Skipping preflight during diagnosis removes the fastest way to distinguish program failure from landing failure.

