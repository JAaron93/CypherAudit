#!/usr/bin/env bash
# vf_inventory.sh — Version-Free Rules drift inventory (read-only).
#
# Scans living rule prose for constraint-BINDING versions — the kind that silently
# outlive vendor dependency metadata. Series/identity references ("ADK 2.x",
# "React 19") carry no binding operator and are never flagged.
#
# Usage:   vf_inventory.sh [REPO_ROOT]
# Output:  TSV lines on stdout:  file:line<TAB>ANCHORED|LOOSE<TAB>matched-snippet
#          ANCHORED = a package identifier immediately precedes the operator
#                     (the drift-prose signature); LOOSE = superset sweep hit.
# Excludes: docs/archive, any */archive*/ dir, CHANGELOG*, node_modules, .git.
# Exit:    0 clean (no hits)  ·  1 hits found  ·  2 usage/precondition error
# Deps:    rg (ripgrep)
set -euo pipefail

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,10p' "$0"
  exit 0
fi

command -v rg >/dev/null 2>&1 || { echo "error: ripgrep (rg) is required" >&2; exit 2; }

REPO=""
if [ $# -gt 0 ]; then REPO="$1"; else REPO="$(pwd)"; fi
if [ ! -d "$REPO" ]; then echo "error: not a directory: $REPO" >&2; exit 2; fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Anchored: identifier + binding operator + version.  Loose: operator + version only.
# Bare ~ / ^ REQUIRE a dotted version (estimates like "~8 seconds" are duration prose,
# not constraints) while >=,<=,==,~= keep single-component form (e.g. >=3.10).
ANCHOR_RE='([A-Za-z][A-Za-z0-9_.@/-]{1,60})[[:space:]]*(>=|<=|==|~=|~|\^)[[:space:]]*[vV]?[0-9]+'
LOOSE_RE='(>=|<=|==|~=|~|\^)[[:space:]]*[vV]?[0-9]+(\.[0-9]+)*'

G=()
for g in '*.md' '*.mdc' '!**/docs/archive/**' '!**/archive*/**' '!**/CHANGELOG*' \
         '!**/node_modules/**' '!**/.git/**' '!**/__pycache__/**'; do
  G+=(--glob "$g")
done

# Duration/estimate junk filter: drop rows whose text binds a number straight to a
# unit ("16s", "8ms", "~2-5 KB", ">= 80%"), estimate phrasing ("lines ~1542",
# "~10,000 requests", "~475 container-hours", "input tokens", "analyses / day"),
# JS strict equality ("=== 402" — the loose == matches from its 2nd '='), and
# Python `assert` snippets quoted inside walkthrough code blocks. NOTE: %/× use
# boundary-FREE forms — a trailing \b after a non-word char never matches.
# Deliberate tradeoff: acceptable false negatives (unit-suffixed constraints are
# rare in rule prose) against unusable noise.
U=(-e '[0-9]s\b'
   -e '[0-9][[:space:]]?(ms|KB|MB|GB|bytes|tokens?|frames?|chars?)\b'
   -e '[0-9][[:space:]]?%'
   -e '[0-9][[:space:]]?×'
   -e '[0-9]+[[:space:]](s|seconds?|minutes?|hours?|ms|KB|MB|GB|bytes|tokens?|chars?|lines?|requests?)\b'
   -e '\b(tokens?|hours?|days?|lines?|requests?|analyses)\b'
   -e '\bassert\b'
   -e '(===|!==)'
  )

(cd "$REPO" && rg -n -e "$ANCHOR_RE" "${G[@]}" .) 2>/dev/null \
  | rg -v "${U[@]}" 2>/dev/null >"$TMP/anchor.raw" || true
(cd "$REPO" && rg -n -e "$LOOSE_RE" "${G[@]}" .) 2>/dev/null \
  | rg -v "${U[@]}" 2>/dev/null >"$TMP/loose.raw" || true

# Normalize "path:NN:" prefixes into file:line<TAB>snippet rows (paths may contain ':').
# BSD sed cannot expand \t inside replacements — embed a literal TAB instead.
TAB="$(printf '\t')"
norm() { sed -E "s/^([^:]+):([0-9]+):/\1:\2${TAB}/"; }

# Because snippets may themselves contain tabs, split on the FIRST tab only and
# preserve everything after it: awk index(substr) keeps inner tabs intact.
norm <"$TMP/anchor.raw" | awk -F'\t' -v tag="ANCHORED" \
  'NF>=2 { print $1 "\t" tag "\t" substr($0, index($0, "\t") + 1) }' \
  | sort -u >"$TMP/a_rows"

norm <"$TMP/loose.raw" | awk -F'\t' -v tag="LOOSE" \
  'NF>=2 { print $1 "\t" tag "\t" substr($0, index($0, "\t") + 1) }' \
  | sort -u >"$TMP/l_rows"

# Report LOOSE hits only where no ANCHORED hit already covers the same file:line.
cut -f1 "$TMP/a_rows" | sort -u >"$TMP/a_keys"
cut -f1 "$TMP/l_rows" | sort -u >"$TMP/l_keys"
comm -13 "$TMP/a_keys" "$TMP/l_keys" >"$TMP/l_only_keys"
awk -F'\t' 'FNR==NR { want[$1]; next } ($1 in want) { print }' \
  "$TMP/l_only_keys" "$TMP/l_rows" >"$TMP/l_rows_only"

cat "$TMP/a_rows" "$TMP/l_rows_only" >"$TMP/rows"

N="$(awk 'END { print NR }' "$TMP/rows")"
cat "$TMP/rows"
printf 'vf_inventory: %s binding-version drift candidate(s) in living prose (%s)\n' \
  "$N" "$REPO" >&2
if [ "$N" -gt 0 ]; then
  exit 1
fi
exit 0
