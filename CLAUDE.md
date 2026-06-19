# Solana Tx Landing Skill

Use this repository to maintain the Solana Tx Landing skill. Keep the skill progressive, current, and operationally useful.

Before changing transaction guidance, verify it against primary Solana, Anza, Jito, or provider documentation. Prefer narrow, concrete workflow guidance over broad launch advice. Scripts must remain offline-safe: they may inspect local source files and logs, but must not sign, send, or simulate live transactions.

Run these checks after edits:

```bash
python3 scripts/scan_ts_transactions.py tests/fixtures/typescript --format json
python3 scripts/parse_simulation_logs.py tests/fixtures/logs/simulation.log --format json
python3 scripts/scan_anchor_compute.py tests/fixtures/rust --format json
python3 scripts/tx_landing_report.py tests/fixtures --format md
```

