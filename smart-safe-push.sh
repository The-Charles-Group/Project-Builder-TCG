#!/bin/bash
echo "🔄 Pulling latest from GitHub..."

# Temporarily save local uncommitted changes
git stash push -u -m "auto-stash before safe-push"

# Pull new commits safely
git pull origin main --rebase

# Restore your local changes
git stash pop || echo "✅ No local changes to restore"

echo "🚀 Pushing your new commits..."
git add -A
if ! git diff --cached --quiet; then
  git commit -m "auto: checkpoint $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
else
  echo "✅ No new commits to push."
fi
git push origin main



