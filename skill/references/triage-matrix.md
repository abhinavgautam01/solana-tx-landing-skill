# Triage Matrix

Use this first when the user provides an error string, failed signature, or vague landing symptom.

| Symptom | Likely cause | First evidence to collect | First fix path |
| --- | --- | --- | --- |
| `Blockhash not found` during simulation | Simulating against an RPC bank older than the transaction blockhash, stale blockhash, or mismatched preflight commitment | `getLatestBlockhash` commitment, `simulateTransaction` config, RPC endpoint used for both calls | Match preflight commitment to blockhash commitment; use `replaceRecentBlockhash` for diagnosis; refresh blockhash before signing |
| `TransactionExpiredBlockheightExceededError` | Transaction was not confirmed before `lastValidBlockHeight` | Client confirmation call, resend loop, wallet signing delay, RPC lag | Use blockheight-based confirmation and rebroadcast until expiry |
| `sendTransaction` returned a signature but explorer never shows it | RPC accepted relay but cluster did not process it | RPC response, status polling, resend behavior, priority fee, blockhash age | Poll `getSignatureStatuses`; resend until expiry; tune fee and RPC path |
| Lands locally/devnet but fails on mainnet | Fee market, account locks, compute, or mainnet-only state differs | Simulation logs on mainnet fork, writable accounts, CU consumed, prioritization fee | Simulate against mainnet state; set CU limit/price; reduce lock contention |
| Slow landing under load | Insufficient priority fee, too many writable hot accounts, slow RPC path | `getRecentPrioritizationFees`, writable account set, RPC slot lag | Price by local writable accounts; add RPC failover/Jito path for critical txs |
| `ComputationalBudgetExceeded` or exceeded instructions | CU limit too low or program too expensive | Simulation `unitsConsumed`, logs around CPI/loops | Set CU limit from simulation plus margin; optimize program/CPI path |
| `AccountInUse` / account lock conflict | Hot writable account contention | Writable accounts and concurrent flow | Split state, reduce write locks, stagger sends, price local fee market |
| Wallet approval takes too long then tx expires | Blockhash fetched before slow user interaction | Timeline around transaction build/sign/send | Build transaction after approval intent; refresh blockhash immediately before signing |
| Versioned transaction rejected by wallet/RPC | Wallet/RPC does not support versioned tx or ALT lookup failed | Wallet capability, RPC max supported tx version, ALT state | Check support; pass max supported version; verify ALT activation/deactivation |
| Jito bundle not landing | Tip too low, bundle invalid, expired blockhash, or wrong endpoint/encoding | Bundle response, tip, priority fee, blockhash age | Use base64, set priority fee and Jito tip, monitor bundle status |

## Diagnostic Order

1. Determine whether the transaction reached the cluster, landed and failed, or never landed.
2. Separate program failure from transport/landing failure. Program logs imply landing/simulation reached runtime; missing status often implies relay/expiry.
3. Reconstruct blockhash lifecycle. Check commitment, `lastValidBlockHeight`, signing delay, and confirmation strategy.
4. Check fee/compute only after freshness and confirmation logic are sane.
5. Check RPC health and pool consistency before changing app semantics.

