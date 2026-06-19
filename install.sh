#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BASE="${HOME}/.claude"
INSTALL_COMMANDS=1
INSTALL_AGENTS=1
INSTALL_RULES=1
AGENTS_MODE=0
YES=0
RUNTIME_SCRIPTS=(
  diagnose_signature.py
  mcp_server.py
  parse_simulation_logs.py
  scan_anchor_compute.py
  scan_ts_transactions.py
  tx_landing_report.py
)

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Options:
  --target PATH    Install into PATH instead of ~/.claude
  --agents         Install into TARGET/.agents when TARGET is a project root
  --skill-only     Install only the skill folder
  -y, --yes        Do not prompt
  -h, --help       Show this help

Examples:
  ./install.sh
  ./install.sh --target /path/to/project/.agents
  ./install.sh --agents --target /path/to/project
  ./install.sh --skill-only --target /path/to/project/.agents
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_BASE="$2"
      shift 2
      ;;
    --agents)
      AGENTS_MODE=1
      shift
      ;;
    --skill-only)
      INSTALL_COMMANDS=0
      INSTALL_AGENTS=0
      INSTALL_RULES=0
      shift
      ;;
    -y|--yes)
      YES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$AGENTS_MODE" -eq 1 && "$TARGET_BASE" != */.agents ]]; then
  TARGET_BASE="${TARGET_BASE%/}/.agents"
fi

if [[ ! -f "$ROOT_DIR/skill/SKILL.md" ]]; then
  echo "Cannot find skill/SKILL.md. Run installer from the repository root." >&2
  exit 1
fi

echo "Installing Solana Tx Landing skill into: $TARGET_BASE"
if [[ "$YES" -ne 1 ]]; then
  read -r -p "Continue? [y/N] " answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

mkdir -p "$TARGET_BASE/skills/solana-tx-landing"
cp -R "$ROOT_DIR/skill/." "$TARGET_BASE/skills/solana-tx-landing/"
mkdir -p "$TARGET_BASE/skills/solana-tx-landing/scripts"
for script in "${RUNTIME_SCRIPTS[@]}"; do
  cp "$ROOT_DIR/scripts/$script" "$TARGET_BASE/skills/solana-tx-landing/scripts/$script"
done

if [[ "$INSTALL_COMMANDS" -eq 1 ]]; then
  mkdir -p "$TARGET_BASE/commands"
  cp -R "$ROOT_DIR/commands/." "$TARGET_BASE/commands/"
fi

if [[ "$INSTALL_AGENTS" -eq 1 ]]; then
  mkdir -p "$TARGET_BASE/agents"
  cp -R "$ROOT_DIR/agents/." "$TARGET_BASE/agents/"
fi

if [[ "$INSTALL_RULES" -eq 1 ]]; then
  mkdir -p "$TARGET_BASE/rules"
  cp -R "$ROOT_DIR/rules/." "$TARGET_BASE/rules/"
fi

echo "Installed."
echo "Skill: $TARGET_BASE/skills/solana-tx-landing"
echo "Scripts: $TARGET_BASE/skills/solana-tx-landing/scripts"
