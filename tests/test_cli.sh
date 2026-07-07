#!/bin/bash
# CLI smoke test — drives the tabrot script against a throwaway TABROT_HOME.
# No browser, session files, or network involved; safe anywhere (CI included).
#
# TABROT_BIN overrides which executable is tested (default: the checkout
# script next to this tests/ directory) so the same suite verifies both the
# checkout layout and an installed bin+share layout.
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TABROT_BIN="${TABROT_BIN:-$TESTS_DIR/../tabrot}"

TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT
export TABROT_HOME="$TMP_HOME"
# A TABROT_SHARE leaked from the caller's environment would bypass the
# layout resolution this suite exists to verify — drop it.
unset TABROT_SHARE

fail() { echo "FAIL: $1" >&2; exit 1; }

# --- version ---------------------------------------------------------------
out="$("$TABROT_BIN" version)"
case "$out" in
  "tabrot "*.*.*) : ;;
  *) fail "unexpected version output: $out" ;;
esac
out2="$("$TABROT_BIN" --version)"
[ "$out" = "$out2" ] || fail "--version output differs from version"
out3="$("$TABROT_BIN" -v)"
[ "$out" = "$out3" ] || fail "-v output differs from version"

# version must not create the data home's contents
[ ! -e "$TMP_HOME/manifests" ] || fail "version created data dirs"

# --- paths -----------------------------------------------------------------
paths="$("$TABROT_BIN" paths)"
for key in home manifests snapshots parked share parser triage templates; do
  echo "$paths" | grep -q "^$key=" || fail "paths output missing key: $key"
done
echo "$paths" | grep -qxF "home=$TMP_HOME" || fail "paths home != TABROT_HOME"
[ ! -e "$TMP_HOME/manifests" ] || fail "paths created data dirs"

# every asset path printed by paths must exist on disk
parser="$(echo "$paths" | sed -n 's/^parser=//p')"
triage="$(echo "$paths" | sed -n 's/^triage=//p')"
templates="$(echo "$paths" | sed -n 's/^templates=//p')"
[ -f "$parser" ] || fail "parser not found at $parser"
[ -f "$triage" ] || fail "TRIAGE.md not found at $triage"
[ -f "$templates/PARKED.template.md" ] || fail "template not found in $templates"

# --- init / list / ledger seeding -------------------------------------------
"$TABROT_BIN" init demo >/dev/null
[ -f "$TMP_HOME/manifests/demo.urls" ] || fail "init did not create manifest"
[ -f "$TMP_HOME/PARKED.md" ] || fail "first data command did not seed PARKED.md"
"$TABROT_BIN" init demo >/dev/null 2>&1 && fail "second init should refuse to overwrite"
list="$("$TABROT_BIN" list)"
echo "$list" | grep -qx "demo" || fail "list does not show demo"

# --- project-name guard -------------------------------------------------------
# '../evil' must be rejected before any path is built; nothing may land in
# the parent of $TMP_HOME/manifests (which is $TMP_HOME itself).
"$TABROT_BIN" init ../evil >/dev/null 2>&1 && fail "init ../evil should exit nonzero"
"$TABROT_BIN" open ../evil >/dev/null 2>&1 && fail "open ../evil should exit nonzero"
[ ! -e "$TMP_HOME/evil.urls" ] || fail "traversal created evil.urls outside manifests/"

# --- help / unknown command --------------------------------------------------
"$TABROT_BIN" help >/dev/null || fail "help exited nonzero"
"$TABROT_BIN" bogus >/dev/null 2>&1 && fail "unknown command should exit nonzero"

echo "ok: CLI smoke passed ($TABROT_BIN)"
