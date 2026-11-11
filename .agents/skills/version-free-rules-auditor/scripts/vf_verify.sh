#!/usr/bin/env bash
# vf_verify.sh — Version-Free Rules governance-PR gate.
#
# Gate A (living prose): zero UNLABELED binding-version hits; dated, explicitly labeled
#   drift evidence stays legal via --allow.
# Gate B (--base REF, semantics: BASE...HEAD): the accumulated diff must touch ONLY
#   prose/review-config paths. Manifest, lockfile, env, database, or source paths FAIL —
#   constraint changes belong in a separate dependency PR (conflict report carries them).
#
# Usage:  vf_verify.sh [REPO_ROOT] [--base REF] [--allow FILE] [--no-strict-diff]
#         --allow FILE : one 'file:line' key per line (vf_inventory.sh column 1); '#' comments.
# Exit:   0 PASS  ·  1 FAIL (violations listed)  ·  2 usage/precondition error
set -euo pipefail

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,16p' "$0"
  exit 0
fi

REPO=""
BASE=""
ALLOW=""
STRICT=1
while [ $# -gt 0 ]; do
  case "$1" in
    --base)
      [ $# -ge 2 ] || { echo "--base needs a REF argument" >&2; exit 2; }
      BASE="$2"; shift 2 ;;
    --allow)
      [ $# -ge 2 ] || { echo "--allow needs a FILE argument" >&2; exit 2; }
      ALLOW="$2"; shift 2 ;;
    --no-strict-diff) STRICT=0; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    --) shift; break ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *)
      if [ -z "$REPO" ]; then REPO="$1"; else
        echo "unexpected argument: $1" >&2; exit 2
      fi
      shift ;;
  esac
done

if [ -z "$REPO" ]; then
  REPO="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
fi
if [ -z "$REPO" ] || [ ! -d "$REPO" ]; then
  echo "error: REPO_ROOT required (pass a directory or run inside a git repo)" >&2
  exit 2
fi
# Normalize to an absolute path so results stay valid regardless of the caller's cwd.
REPO="$(cd "$REPO" && pwd)"

HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---- Gate A: living-prose drift scan (allowlist-filterable) -----------------------
if "$HERE/vf_inventory.sh" "$REPO" >"$TMP/inv.tsv" 2>"$TMP/inv.err"; then
  IRC=0
else
  IRC=$?
fi
if [ "$IRC" -eq 2 ]; then cat "$TMP/inv.err" >&2; exit 2; fi

if [ -n "$ALLOW" ]; then
  if [ ! -f "$ALLOW" ]; then echo "error: --allow is not a file: $ALLOW" >&2; exit 2; fi
  grep -Ev '^[[:space:]]*(#|$)' "$ALLOW" >"$TMP/allow.keys" || true
  # Allowlist matches the row KEY (column 1), not the whole row: compare on the
  # first TSV field so `path:line` keys filter rows regardless of the snippet.
  # FILENAME==ARGV[1], NOT FNR==NR: with an empty/comment-only allow file NR never
  # advances past the first file, so FNR==NR holds for EVERY inv.tsv row and all
  # violations are swallowed as "keys" — fail-open. The -s guard additionally fails
  # closed: an empty allowlist filters nothing.
  if [ -s "$TMP/allow.keys" ]; then
    awk -F'\t' 'FILENAME==ARGV[1] { keys[$1]; next } !($1 in keys) { print }' \
      "$TMP/allow.keys" "$TMP/inv.tsv" >"$TMP/viol.tsv"
  else
    cp "$TMP/inv.tsv" "$TMP/viol.tsv"
  fi
else
  cp "$TMP/inv.tsv" "$TMP/viol.tsv"
fi

N="$(awk 'END { print NR }' "$TMP/viol.tsv")"

# ---- Gate B: prose-only diff (BASE...HEAD) ---------------------------------------
DVIOL=""
if [ -n "$BASE" ] && [ "$STRICT" -eq 1 ]; then
  if ! (cd "$REPO" && git diff --name-only "${BASE}...HEAD" >"$TMP/files.txt" 2>/dev/null); then
    echo "error: --base REF not resolvable: $BASE" >&2
    exit 2
  fi
  while IFS= read -r f; do
    case "$f" in
      requirements*.txt|pyproject.toml|package.json|package-lock.json|yarn.lock|pnpm-lock.yaml|Cargo.toml|Cargo.lock|go.mod|go.sum|pom.xml|build.gradle*|Package.swift)
        DVIOL="$DVIOL  DENY $f — manifest/lockfile: belongs in a separate dependency PR
"
        ;;
      .env*|*.env|*.sqlite*|*.sqlite3|*.db|*.db-wal|*.db-shm)
        DVIOL="$DVIOL  DENY $f — protected artifact (env/db) never in a docs PR
"
        ;;
      .github/*)
        DVIOL="$DVIOL  DENY $f — GitHub config incl. executable workflows: never in a docs-only governance PR
"
        ;;
      *.md|*.mdc|README*|LICENSE*|.greptile/*|.agents/*|.cursor/*)
        : ;;  # prose / review-config: allowed by design
      *.yaml|*.yml)
        # YAML is allowed only for review-settings paths; other YAML (CI pipelines,
        # deploy manifests) is executable-adjacent and fails closed.
        case "$f" in
          .*.yaml|.*.yml) : ;;  # root dotfile review configs (.coderabbit.yaml, …)
          *) DVIOL="$DVIOL  DENY $f — YAML allowed only for review-config paths in a docs-only PR
" ;;
        esac
        ;;
      *)
        DVIOL="$DVIOL  DENY $f — not prose/review-config (docs-only governance PR policy)
"
        ;;
    esac
  done <"$TMP/files.txt"
fi

# ---- Verdict ---------------------------------------------------------------------
FAIL=0
if [ "$N" -gt 0 ]; then
  FAIL=1
  echo "FAIL living-prose gate: ${N} unlabeled binding-version hit(s)" >&2
  cat "$TMP/viol.tsv" >&2
else
  echo "PASS living-prose gate: zero unlabeled binding-version hits"
fi
if [ "$STRICT" -eq 1 ] && [ -n "$BASE" ] && [ -n "$DVIOL" ]; then
  FAIL=1
  echo "FAIL diff gate (--base ${BASE}): non-prose paths touched" >&2
  printf '%s' "$DVIOL" >&2
elif [ -n "$BASE" ] && [ "$STRICT" -eq 1 ] && [ -z "$DVIOL" ]; then
  echo "PASS diff gate (--base ${BASE}): prose/review-config paths only"
fi

if [ "$FAIL" -eq 0 ]; then
  echo "vf_verify: PASS (Version-Free Rules governance diff)"
  exit 0
fi
echo "vf_verify: FAIL" >&2
exit 1
