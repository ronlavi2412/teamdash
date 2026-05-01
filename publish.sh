#!/usr/bin/env bash
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: ./publish.sh <dashboard.html> [dashboard2.html ...]"
    echo "Publishes the specified HTML files to GitHub Pages (gh-pages branch)."
    exit 1
fi

for f in "$@"; do
    if [ ! -f "$f" ]; then
        echo "Error: file not found: $f"
        exit 1
    fi
done

orig_branch=$(git rev-parse --abbrev-ref HEAD)
stash_needed=false
if ! git diff --quiet || ! git diff --cached --quiet; then
    stash_needed=true
    git stash push -q -m "publish.sh auto-stash"
fi

tmpdir=$(mktemp -d)
for f in "$@"; do
    cp "$f" "$tmpdir/"
done
# preserve git-ignored files/dirs that would be lost during branch switch
backup_dir="$tmpdir/_backup"
mkdir -p "$backup_dir"
if [ -d config ]; then cp -a config "$backup_dir/"; fi
for html in *.html; do [ -f "$html" ] && cp "$html" "$backup_dir/"; done 2>/dev/null || true

cleanup() {
    git checkout -q "$orig_branch" 2>/dev/null || true
    # restore git-ignored files
    if [ -d "$backup_dir/config" ]; then
        cp -a "$backup_dir/config" . 2>/dev/null || true
    fi
    cp "$backup_dir"/*.html . 2>/dev/null || true
    rm -rf "$tmpdir"
    if [ "$stash_needed" = true ]; then
        git stash pop -q 2>/dev/null || true
    fi
}
trap cleanup EXIT

if git rev-parse --verify gh-pages >/dev/null 2>&1; then
    git checkout -q gh-pages
    for f in "$@"; do
        cp "$tmpdir/$(basename "$f")" .
    done
else
    git checkout -q --orphan gh-pages
    git rm -rf -q .
    for f in "$@"; do
        cp "$tmpdir/$(basename "$f")" .
    done
fi

# Build index.html listing all dashboards
dashboards=$(find . -maxdepth 1 -name '*.html' ! -name 'index.html' -printf '%f\n' | sort)
cat > index.html <<'HEADER'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Team Dashboards</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 600px; margin: 60px auto; padding: 0 20px; }
  h1 { margin-bottom: 8px; }
  p { color: #666; margin-top: 0; }
  ul { list-style: none; padding: 0; }
  li { margin: 12px 0; }
  a { color: #0969da; text-decoration: none; font-size: 1.1em; }
  a:hover { text-decoration: underline; }
</style>
</head>
<body>
<h1>Team Dashboards</h1>
<p>Published reports</p>
<ul>
HEADER

for d in $dashboards; do
    label=$(echo "$d" | sed 's/\.html$//' | sed 's/dashboard-//' | sed 's/-/ /g')
    echo "  <li><a href=\"$d\">$label</a></li>" >> index.html
done

cat >> index.html <<'FOOTER'
</ul>
</body>
</html>
FOOTER

git add -A
git commit -q -m "Publish dashboards: $(echo "$@" | xargs -n1 basename | tr '\n' ' ')"
git push -u origin gh-pages

echo ""
echo "Published to GitHub Pages."
echo "Dashboards will be available at: https://$(gh api repos/:owner/:repo --jq '.full_name' 2>/dev/null | sed 's|/|.github.io/|')/."
