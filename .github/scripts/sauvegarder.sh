#!/usr/bin/env bash
# Usage : sauvegarder.sh data/history_xxx.json
set -u
f="$1"
if [ ! -f "$f" ]; then
  echo "Rien à sauvegarder ($f absent)."
  exit 0
fi
cp "$f" /tmp/sauvegarde.json
git config user.name "veille-bot"
git config user.email "bot@users.noreply.github.com"
for i in 1 2 3 4; do
  git fetch origin main
  git reset --hard origin/main
  cp /tmp/sauvegarde.json "$f"
  git add "$f"
  if git diff --cached --quiet; then
    echo "Aucun changement."
    exit 0
  fi
  git commit -m "maj $f"
  if git push origin HEAD:main; then
    exit 0
  fi
  sleep $((i * 5))
done
echo "Échec de la sauvegarde après 4 essais."
exit 1
