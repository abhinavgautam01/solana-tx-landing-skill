# Publishing

The local repository is complete and validated. The only external requirement for the Superteam listing is a public GitHub URL.

## One-Command Publish

After authenticating GitHub CLI:

```bash
gh auth login -h github.com
bash scripts/publish_github.sh
```

The script:

- verifies `gh` authentication
- requires a clean working tree
- runs `bash scripts/validate.sh`
- creates a public GitHub repo named `solana-tx-landing-skill` when `origin` is missing
- pushes `main`
- updates `SUBMISSION.md` with the resulting GitHub URL

To use a different repo name:

```bash
bash scripts/publish_github.sh my-repo-name
```

To create a private repo for review before making it public:

```bash
VISIBILITY=private bash scripts/publish_github.sh
```

## Manual Publish

```bash
gh auth login -h github.com
gh repo create solana-tx-landing-skill --public --source . --remote origin --description "Claude Code / Codex skill for diagnosing and hardening Solana transaction landing flows." --push
git push -u origin main
```

Then paste the public repo URL into `SUBMISSION.md` and the Superteam listing questionnaire.

