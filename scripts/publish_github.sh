#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

REPO_NAME="${1:-solana-tx-landing-skill}"
VISIBILITY="${VISIBILITY:-public}"

if [[ "$VISIBILITY" != "public" && "$VISIBILITY" != "private" ]]; then
  echo "VISIBILITY must be public or private" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI is required. Install gh, then run this script again." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated." >&2
  echo "Run: gh auth login -h github.com" >&2
  exit 1
fi

if [[ -n "$(git status --short)" ]]; then
  echo "Working tree is not clean. Commit or stash changes before publishing." >&2
  git status --short >&2
  exit 1
fi

bash scripts/validate.sh

if git remote get-url origin >/dev/null 2>&1; then
  REMOTE_URL="$(git remote get-url origin)"
else
  gh repo create "$REPO_NAME" "--$VISIBILITY" --source . --remote origin --description "Claude Code / Codex skill for diagnosing and hardening Solana transaction landing flows." --push
  REMOTE_URL="$(git remote get-url origin)"
fi

git push -u origin main

OWNER_REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
PUBLIC_URL="https://github.com/${OWNER_REPO}"

python3 - "$PUBLIC_URL" <<'PY'
from pathlib import Path
import sys

url = sys.argv[1]
path = Path("SUBMISSION.md")
text = path.read_text(encoding="utf-8")
text = text.replace("TODO: Add the public GitHub URL after pushing this repository.", url)
path.write_text(text, encoding="utf-8")
PY

echo "Published: $PUBLIC_URL"
echo "Updated SUBMISSION.md with the repo URL. Review and commit that one-line update if desired."

