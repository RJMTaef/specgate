#!/usr/bin/env bash
set -euo pipefail
repo="${1:?Usage: scripts/protect-main.sh OWNER/REPO}"
# Task links bind full SHAs, so merges must retain the original implementation commits.
gh api --method PATCH "repos/$repo" -F allow_squash_merge=false \
  -F allow_rebase_merge=false -F allow_merge_commit=true -F delete_branch_on_merge=true \
  --silent
gh api --method PUT "repos/$repo/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {"context": "Spec Ready", "app_id": 15368},
      {"context": "PR Ready", "app_id": 15368},
      {"context": "Deploy + PIV", "app_id": 15368}
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
