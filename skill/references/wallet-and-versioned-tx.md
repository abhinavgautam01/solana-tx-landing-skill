# Wallet And Versioned Transactions

## Wallet Signing

Wallet latency can consume most of a recent blockhash lifetime. For consumer flows:

- Build the final transaction as late as possible.
- Avoid doing slow quote, KYC, metadata, or backend work after blockhash fetch.
- If the wallet supports signing but not sending, send immediately after signing.
- If the wallet sends internally, understand whether it performs preflight, retries, and confirmation.
- On expiry after user approval, rebuild and request a new signature. Do not attempt to reuse the old signature.

## Versioned Transactions

Versioned transactions are useful for complex account lists and address lookup tables, but they add compatibility checks:

- Confirm the wallet supports signing `VersionedTransaction`.
- Confirm RPC calls that fetch transactions pass an appropriate max supported transaction version when required by the SDK.
- Verify address lookup tables are active, not deactivated, and contain every expected address.
- Keep compute budget instructions in the message before app instructions.

## Address Lookup Tables

ALT issues can look like landing failures when they are really message construction failures.

Check:

- The ALT account exists on the target cluster.
- The lookup table has propagated before production use.
- The indexes map to expected accounts.
- The transaction does not exceed account or packet size limits.
- The app has a legacy fallback if wallet support is incomplete.

