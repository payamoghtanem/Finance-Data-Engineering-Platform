#!/usr/bin/env bash
# Verify every relative Markdown link in the repo resolves to a real file.
# Used by .github/workflows/docs.yml and by pre-commit.
set -uo pipefail

fail=0
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

find . -name '*.md' -not -path './.git/*' -print0 > "$tmp"

while IFS= read -r -d '' f; do
  d=$(dirname "$f")
  grep -oE '\]\(([^)#]+\.md)[^)]*\)|`(\.\./|\./)[^`]*\.md`' "$f" 2>/dev/null \
    | sed -E 's/^\]\(//; s/\)$//; s/^`//; s/`$//; s/#.*//' \
    | while IFS= read -r link; do
        [ -z "$link" ] && continue
        case "$link" in
          http*|*'*'*) continue ;;   # skip URLs and glob references
        esac
        if [ ! -e "$d/$link" ]; then
          printf 'BROKEN %s -> %s\n' "$f" "$link"
        fi
      done
done < "$tmp" > "${tmp}.out"

if [ -s "${tmp}.out" ]; then
  cat "${tmp}.out"
  count=$(wc -l < "${tmp}.out")
  echo "FAIL: $count broken relative link(s)."
  fail=1
else
  echo "OK: all relative Markdown links resolve."
fi
rm -f "${tmp}.out"
exit $fail
