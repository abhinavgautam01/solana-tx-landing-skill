# Mainnet Readiness

Use this when the user asks whether a Solana app is ready to launch or when `tx_landing_report.py` finds multiple medium/high issues.

## Required Evidence

- Transaction construction code paths for every critical user action
- Confirmation and retry implementation
- Simulation or test evidence for common success and failure paths
- RPC provider and fallback configuration
- Priority-fee policy with caps
- Compute-unit policy based on simulation
- Wallet support matrix
- Monitoring and alerting plan

## Launch Checklist

- Blockhash fetched close to signing
- `lastValidBlockHeight` retained and used
- Commitment and preflight commitment aligned
- Preflight enabled for normal user transactions
- Bounded rebroadcast loop implemented or RPC retry behavior understood
- Expiry handled by rebuild/resign, not blind resend
- Priority fee selected from recent/local fee data
- Compute unit limit set from simulation with margin
- Hot writable accounts identified
- RPC slot lag monitored
- User-facing error states distinguish rejected, failed, expired, and pending
- Simulation logs collected for failed transactions
- Wallet adapters tested for versioned transaction support
- Jito path tested if used
- Dashboards track send attempts, confirmations, expiry, preflight failures, units consumed, and fees paid

## Report Rubric

- **Ready**: no high findings, medium findings have explicit owner/date, monitoring exists.
- **Conditionally ready**: one high finding with a contained mitigation, or multiple medium findings with workarounds.
- **Not ready**: missing blockheight confirmation, no expiry handling, no priority fee policy for critical flows, or no way to observe failures.

