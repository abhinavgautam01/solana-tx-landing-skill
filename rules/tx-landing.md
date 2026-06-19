# Transaction Landing Rules

- Fetch a fresh blockhash close to signing and keep the returned `lastValidBlockHeight`.
- Use matching commitment/preflight commitment across blockhash fetch, simulation, send, and confirmation unless there is a documented reason not to.
- Prefer explicit blockheight-based confirmation over signature-only confirmation.
- Treat `sendTransaction` success as relay acceptance, not cluster confirmation.
- Add compute-unit limit and compute-unit price intentionally for production transactions.
- Retry or rebroadcast until confirmation or expiry; do not retry indefinitely after `lastValidBlockHeight`.
- Monitor RPC slot lag and avoid mixing blockhash fetch/send across unhealthy pool members.
- Keep simulation enabled during diagnosis; only skip preflight when another simulation or bundle path covers that risk.

