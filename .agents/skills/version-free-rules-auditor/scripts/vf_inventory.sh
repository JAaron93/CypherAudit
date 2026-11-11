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

# Anchored: identifier + binding operator + version, or identifier + suffix floor
# ("uAgents 0.26+", "Python 3.11+" — trailing + glues directly to the version).
# Loose: operator + version only, or a dotted suffix floor ("3.11+").
# Bare ~ / ^ REQUIRE a dotted version (estimates like "~8 seconds" are duration prose,
# not constraints) while >=,<=,==,~= keep single-component form (e.g. >=3.10).
ANCHOR_RE='([A-Za-z][A-Za-z0-9_.@/-]{1,60})[[:space:]]*(>=|<=|==|~=|~|\^)[[:space:]]*[vV]?[0-9]+|([A-Za-z][A-Za-z0-9_.@/-]{1,60})[[:space:]]*[vV]?[0-9]+(\.[0-9]+)*[+]'
LOOSE_RE='(>=|<=|==|~=|~|\^)[[:space:]]*[vV]?[0-9]+(\.[0-9]+)*|[0-9]+\.[0-9]+[+]'

# --hidden: hidden rulebooks (.greptile/rules.md, .cursor/rules/**) are explicitly
# governed prose and MUST be scanned; venvs/package dirt stay excluded.
G=()
for g in '*.md' '*.mdc' '!**/docs/archive/**' '!**/archive*/**' '!**/CHANGELOG*' \
         '!**/node_modules/**' '!**/.git/**' '!**/.venv/**' '!**/__pycache__/**'; do
  G+=(--glob "$g")
done

# Duration/estimate junk is classified PER MATCH, not per line: a candidate row
# is dropped only when EVERY match of the scan regex on that line is
# number-and-unit noise. A line with at least one genuine version match ("Use
# requests>=2.31 for HTTP calls", "tabulate>=0.10.0 (95% coverage)") is KEPT,
# even when the same line also contains durations or unit words — the previous
# line-level `rg -v` filter discarded such real constraints wholesale (false
# negatives). Residual tradeoff: estimate prose without an attached unit word
# may survive as a false-positive candidate; never a false negative.
scan() { # $1 = regex, $2 = junk-filtered output rows
  local rc=0
  # Run rg unpiped so its exit code cannot be masked: with `pipefail`, a
  # downstream filter exiting 1 would supersede rg's fatal exit 2 and a
  # partially-scanned corpus would masquerade as a clean sweep.
  (cd "$REPO" && rg -n --hidden -e "$1" "${G[@]}" .) >"$TMP/raw.tsv" 2>"$TMP/scan.err" || rc=$?
  if [ "$rc" -ge 2 ]; then
    echo "error: inventory scan failed (rg exit $rc — unreadable file or bad glob):" >&2
    cat "$TMP/scan.err" >&2
    exit 2
  fi
  # The scan regex arrives via the environment (not `awk -v`) because -v
  # assignment values undergo backslash-escape processing that would corrupt
  # the `\.` / `\^` operators in the pattern.
  VF_RE="$1" awk '
    function junk(tok, after, before) {
      if (tok ~ /===|!==/) return 1                             # JS strict equality
      if (before ~ /=$/ && tok ~ /^==/) return 1                # === seen via its 2nd =
      if (before ~ /(^|[^A-Za-z])assert([^A-Za-z]|$)/) return 1 # quoted assert snippet
      if (before ~ /(lines?|requests?|tokens?|analyses|hours?|days?)[[:space:]]+$/ && tok ~ /^[~^]/) return 1
      #                                ^ estimate phrasing: "lines ~1542"
      if (tok ~ /[0-9]$/ && after ~ /^([,][0-9]+)*[[:space:]]?(seconds?|minutes?|hours?|days?|ms|s|KB|MB|GB|bytes|tokens?|frames?|chars?|lines?|requests?|analyses)([^A-Za-z]|$)/) return 1
      #                                ^ number binds a unit: "16s", "~10,000 requests"
      if (tok ~ /[0-9]$/ && after ~ /^[[:space:]]?(%|×)/) return 1
      #                                ^ ">= 80%"
      if (tok ~ /[0-9]$/ && after ~ /^[[:space:]]?[-][0-9]+([,][0-9]+)*[[:space:]]?(seconds?|minutes?|hours?|days?|ms|s|KB|MB|GB|bytes|tokens?|frames?|chars?|lines?|requests?|analyses)([^A-Za-z]|$)/) return 1
      #                                ^ range with unit: "~2-5 KB"
      return 0
    }
    {
      if (match($0, /^[^:]+:[0-9]+:/)) {
        content = substr($0, RLENGTH + 1)   # strip the path:line: prefix
      } else { content = $0 }
      kept = 0; t = content
      while (match(t, ENVIRON["VF_RE"])) {
        tok   = substr(t, RSTART, RLENGTH)
        after = substr(t, RSTART + RLENGTH, 16)
        before = substr(content, 1, length(content) - length(t) + RSTART - 1)
        if (!junk(tok, after, before)) { kept = 1; break }
        t = substr(t, RSTART + RLENGTH)
      }
      if (kept) print $0
    }
  ' "$TMP/raw.tsv" >"$2"
}
scan "$ANCHOR_RE" "$TMP/anchor.raw"
scan "$LOOSE_RE" "$TMP/loose.raw"

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
