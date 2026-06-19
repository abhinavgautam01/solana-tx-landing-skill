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

Most existing codebases still use `@solana/web3.js`, so examples show that API first. For new code using `@solana/kit`, preserve the same invariants: fetch a fresh latest blockhash with context, sign close to send time, send with explicit options, and confirm using the blockhash plus last valid block height.

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

## @solana/kit Shape

Use the v2 kit factories in new codebases, but keep the same lifecycle. Names vary slightly by installed kit version, so treat this as shape guidance and verify imports against the project lockfile.

```ts
import {
  appendTransactionMessageInstruction,
  createSolanaRpc,
  createTransactionMessage,
  pipe,
  setTransactionMessageFeePayerSigner,
  setTransactionMessageLifetimeUsingBlockhash,
  signTransactionMessageWithSigners,
} from "@solana/kit";

const rpc = createSolanaRpc(rpcUrl);
const latest = await rpc.getLatestBlockhash({ commitment: "confirmed" }).send();

const message = pipe(
  createTransactionMessage({ version: 0 }),
  (tx) => setTransactionMessageFeePayerSigner(feePayer, tx),
  (tx) => setTransactionMessageLifetimeUsingBlockhash(latest.value, tx),
  (tx) => appendTransactionMessageInstruction(appInstruction, tx),
);

const signed = await signTransactionMessageWithSigners(message);
const signature = await rpc.sendTransaction(signed, {
  encoding: "base64",
  preflightCommitment: "confirmed",
}).send();

await rpc
  .confirmTransaction({
    signature,
    blockhash: latest.value.blockhash,
    lastValidBlockHeight: latest.value.lastValidBlockHeight,
  })
  .send();
```

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
