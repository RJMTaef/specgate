#!/usr/bin/env bash
set -euo pipefail
repo="${1:?Usage: scripts/protect-main.sh OWNER/REPO}"
gh api --method PUT "repos/$repo/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Spec Ready", "PR Ready", "Deploy + PIV"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
