# tabrot Packaging & Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make tabrot installable via `make install`, `brew install zcor/tabrot/tabrot`, and a `.deb` on GitHub Releases, with user data moved to `~/.tabrot`.

**Architecture:** The bash CLI gains two independent path concepts: user data always in `$TABROT_HOME` (default `~/.tabrot`), and code assets (Python parser, TRIAGE.md, templates) resolved automatically from either a checkout layout or an installed `<prefix>/share/tabrot` layout. A Makefile installs bin + share; a Homebrew formula template and a deb control template live in-repo and are rendered by a tag-driven release workflow.

**Tech Stack:** bash (3.2-compatible), Python 3 stdlib, GNU Make, dpkg-deb, Homebrew formula DSL, GitHub Actions.

**Authoritative spec:** `docs/superpowers/specs/2026-07-07-packaging-install-design.md`

## Global Constraints

- bash 3.2 compatible (macOS `/bin/bash`): no `readlink -f`, no `mapfile`, no `${var,,}`.
- Zero runtime dependencies beyond `bash` and `python3` (stdlib only). No pytest — tests are plain `python3 tests/test_parser.py` and plain bash.
- `make lint` (shellcheck on `tabrot` and `tests/test_cli.sh`) must pass with zero findings.
- All GitHub Actions pinned by full commit SHA. Verified 2026-07-07 via `git ls-remote`: `actions/checkout` v4.2.2 = `11bd71901bbe5b1630ceea73d27597364c9af683`.
- Version single source of truth: the line `TABROT_VERSION="X.Y.Z"` in `tabrot` (column 0, double quotes). Extraction pattern everywhere (Makefile, release workflow): `sed -n 's/^TABROT_VERSION="\(.*\)"/\1/p' tabrot`.
- First packaged release: `0.2.0`.
- Deb maintainer string: `zcor <zcor@users.noreply.github.com>` (privacy-safe noreply; maintainer may swap a real address before tagging).
- Privacy (from CONTRIBUTING.md): no real personal data in any fixture, example, or doc.
- User data lives only under `$TABROT_HOME`; nothing is ever written to the repo or install prefix at runtime.

---

### Task 1: CLI refactor — data home, share resolution, `version`/`paths`

**Files:**
- Create: `tests/test_cli.sh` (executable)
- Modify: `tabrot` (full rewrite of path handling; command surface grows by `version` and `paths`)

**Interfaces:**
- Consumes: nothing (first task).
- Produces (later tasks depend on these exact names/behaviors):
  - Env contract: `TABROT_HOME` (data home, default `~/.tabrot`), `TABROT_SHARE` (flat asset-dir override).
  - `TABROT_VERSION="0.2.0"` line at column 0 of `tabrot` (Tasks 2 and 6 sed it out).
  - `tabrot version` prints exactly `tabrot 0.2.0`; `--version`/`-v` aliases.
  - `tabrot paths` prints exactly these keys, one `key=value` per line: `home`, `manifests`, `snapshots`, `parked`, `share`, `parser`, `triage`, `templates`.
  - Installed-layout resolution: script at `<prefix>/bin/tabrot` finds assets at `<prefix>/share/tabrot/{snss_tabs.py,TRIAGE.md,templates/}` (Task 2's `make install` must produce exactly this layout).
  - `tests/test_cli.sh` honors `TABROT_BIN` (path to the tabrot executable under test; defaults to the repo checkout script). Tasks 2 and 5 run it against installed layouts.

- [ ] **Step 1: Write the failing CLI smoke test**

Create `tests/test_cli.sh` with exactly this content:

```bash
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

fail() { echo "FAIL: $1" >&2; exit 1; }

# --- version ---------------------------------------------------------------
out="$("$TABROT_BIN" version)"
case "$out" in
  "tabrot "*.*.*) : ;;
  *) fail "unexpected version output: $out" ;;
esac
out2="$("$TABROT_BIN" --version)"
[ "$out" = "$out2" ] || fail "--version output differs from version"

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

# --- help / unknown command --------------------------------------------------
"$TABROT_BIN" help >/dev/null || fail "help exited nonzero"
"$TABROT_BIN" bogus >/dev/null 2>&1 && fail "unknown command should exit nonzero"

echo "ok: CLI smoke passed ($TABROT_BIN)"
```

Then make it executable:

```bash
chmod +x tests/test_cli.sh
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `tests/test_cli.sh`
Expected: FAIL — current script has no `version` command; first failure is `tabrot: unknown command 'version'` and the script exits via `fail "unexpected version output: ..."` or the command substitution's nonzero exit under `set -e`. Any nonzero exit at this point is the correct red state.

- [ ] **Step 3: Rewrite `tabrot`**

Replace the entire contents of `tabrot` with:

```bash
#!/bin/bash
# tabrot — browser-tab triage/launcher CLI. See README.md for the protocol.
set -euo pipefail

TABROT_VERSION="0.2.0"

# Where this script lives. Symlinks are deliberately NOT resolved: Homebrew,
# dpkg, and `make install` all place bin/ and share/tabrot/ under the same
# prefix, so prefix-sibling resolution works through the bin symlink, and
# `readlink -f` is not portable to macOS bash 3.2 anyway. TABROT_SHARE is
# the escape hatch for layouts this cannot see.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# User data home — everything tabrot writes lives here, never in the repo
# or the install prefix.
TABROT_HOME="${TABROT_HOME:-$HOME/.tabrot}"
SNAPSHOTS="$TABROT_HOME/snapshots"
MANIFESTS="$TABROT_HOME/manifests"
PARKED="$TABROT_HOME/PARKED.md"

# Code assets (parser, protocol, templates) — set by resolve_share().
SHARE=""
PARSER=""
TRIAGE=""
TEMPLATES=""

usage() {
  cat <<EOF
usage: tabrot <command> [args]

commands:
  snapshot          exhume every window/tab from your browser's session file
  open <project>    open <project>'s manifest in a new browser window
  init <project>    create a new manifest from a commented template
  list              list available manifests
  paths             print every path tabrot uses (key=value, one per line)
  version           print tabrot's version

data lives in $TABROT_HOME (override with TABROT_HOME).
EOF
}

need_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "tabrot: python3 is required but was not found on PATH." >&2
    exit 1
  fi
}

# Locate the parser, TRIAGE.md, and templates. Three layouts, first match
# wins: an explicit $TABROT_SHARE (flat directory holding all three); a git
# checkout (this script sitting next to src/); an installed prefix (this
# script in <prefix>/bin, assets in <prefix>/share/tabrot).
resolve_share() {
  if [ -n "${TABROT_SHARE:-}" ]; then
    SHARE="$TABROT_SHARE"
    PARSER="$SHARE/snss_tabs.py"
    TRIAGE="$SHARE/TRIAGE.md"
    TEMPLATES="$SHARE/templates"
  elif [ -f "$DIR/src/snss_tabs.py" ]; then
    SHARE="$DIR"
    PARSER="$DIR/src/snss_tabs.py"
    TRIAGE="$DIR/TRIAGE.md"
    TEMPLATES="$DIR/templates"
  elif [ -f "$DIR/../share/tabrot/snss_tabs.py" ]; then
    SHARE="$(cd "$DIR/../share/tabrot" && pwd)"
    PARSER="$SHARE/snss_tabs.py"
    TRIAGE="$SHARE/TRIAGE.md"
    TEMPLATES="$SHARE/templates"
  fi
  if [ ! -f "$PARSER" ]; then
    echo "tabrot: cannot locate tabrot's code assets (snss_tabs.py)." >&2
    echo "  tried: \$TABROT_SHARE (${TABROT_SHARE:-unset}), $DIR/src/, $DIR/../share/tabrot/" >&2
    echo "  reinstall tabrot, or point TABROT_SHARE at a directory containing" >&2
    echo "  snss_tabs.py, TRIAGE.md, and templates/." >&2
    exit 1
  fi
}

# Create the data home on demand and seed the ledger from the template on
# first use. Runs only for data-touching commands (snapshot/open/init/list);
# version, paths, and help make no filesystem changes.
ensure_home() {
  mkdir -p "$SNAPSHOTS" "$MANIFESTS"
  if [ ! -f "$PARKED" ]; then
    if [ -f "$TEMPLATES/PARKED.template.md" ]; then
      cp "$TEMPLATES/PARKED.template.md" "$PARKED"
      echo "Seeded ledger: $PARKED"
    else
      echo "tabrot: warning: no PARKED template at $TEMPLATES/PARKED.template.md — ledger not seeded." >&2
    fi
  fi
}

cmd_version() {
  echo "tabrot $TABROT_VERSION"
}

cmd_paths() {
  cat <<EOF
home=$TABROT_HOME
manifests=$MANIFESTS
snapshots=$SNAPSHOTS
parked=$PARKED
share=$SHARE
parser=$PARSER
triage=$TRIAGE
templates=$TEMPLATES
EOF
}

cmd_snapshot() {
  need_python
  local out errfile count
  out="$SNAPSHOTS/$(date +%Y-%m-%d).txt"
  errfile="$(mktemp)"
  if ! python3 "$PARSER" > "$out" 2>"$errfile"; then
    cat "$errfile" >&2
    rm -f "$errfile" "$out"
    echo "tabrot: snapshot failed — could not read a browser session file." >&2
    exit 1
  fi
  cat "$errfile" >&2
  rm -f "$errfile"
  count=$(grep -c '|||' "$out" || true)
  echo "Snapshot: $out ($count tabs)"
}

# Find a Chromium-family browser binary to open windows with.
# Prints "kind:binary" on stdout: kind is "mac-app" (use `open -na "<name>"`)
# or "linux-bin" (invoke the binary directly).
detect_browser() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    local apps=(
      "Brave Browser"
      "Google Chrome"
      "Chromium"
      "Microsoft Edge"
      "Arc"
    )
    for app in "${apps[@]}"; do
      if [ -d "/Applications/$app.app" ]; then
        echo "mac-app:$app"
        return 0
      fi
    done
    return 1
  else
    local bins=(brave-browser brave google-chrome chromium chromium-browser microsoft-edge)
    for bin in "${bins[@]}"; do
      if command -v "$bin" >/dev/null 2>&1; then
        echo "linux-bin:$bin"
        return 0
      fi
    done
    return 1
  fi
}

cmd_open() {
  local project="${1:-}"
  if [ -z "$project" ]; then
    echo "usage: tabrot open <project>" >&2
    exit 1
  fi
  local manifest="$MANIFESTS/$project.urls"
  if [ ! -f "$manifest" ]; then
    echo "tabrot: no manifest at $manifest" >&2
    echo "tip: run 'tabrot init $project' to create one, or 'tabrot list' to see what exists." >&2
    exit 1
  fi

  local urls=()
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(echo "$line" | xargs || true)"
    [ -n "$line" ] && urls+=("$line")
  done < "$manifest"

  if [ "${#urls[@]}" -eq 0 ]; then
    echo "tabrot: manifest $manifest has no URLs (only comments/blank lines)." >&2
    exit 1
  fi

  local detected
  if ! detected="$(detect_browser)"; then
    echo "tabrot: could not find a Chromium-family browser installed." >&2
    exit 1
  fi
  local kind="${detected%%:*}"
  local target="${detected#*:}"

  if [ "$kind" = "mac-app" ]; then
    open -na "$target" --args --new-window "${urls[@]}"
  else
    "$target" --new-window "${urls[@]}" >/dev/null 2>&1 &
    disown || true
  fi

  echo "Opened ${#urls[@]} tabs for $project"
}

cmd_list() {
  local found=0
  for f in "$MANIFESTS"/*.urls; do
    [ -e "$f" ] || continue
    found=1
    basename "$f" .urls
  done
  if [ "$found" -eq 0 ]; then
    echo "No manifests yet. Create one with: tabrot init <project>"
  fi
}

cmd_init() {
  local project="${1:-}"
  if [ -z "$project" ]; then
    echo "usage: tabrot init <project>" >&2
    exit 1
  fi
  local manifest="$MANIFESTS/$project.urls"
  if [ -f "$manifest" ]; then
    echo "tabrot: manifest already exists at $manifest (not overwriting)" >&2
    exit 1
  fi
  cat > "$manifest" <<EOF
# manifest: $project
# One URL per line. Everything after # is a comment. Blank lines are ignored.
# 'tabrot open $project' opens every URL below in a fresh browser window.
#
# Tip: append /u/N to a Google URL to force a specific signed-in account,
# e.g. https://mail.google.com/mail/u/0/ instead of the ambiguous default.

# https://example.com/dashboard  # example — replace with your real links
EOF
  echo "Created manifest: $manifest"
  echo "Edit it, then run: tabrot open $project"
}

main() {
  local command="${1:-help}"
  [ $# -gt 0 ] && shift || true
  case "$command" in
    version|--version|-v)
      cmd_version
      ;;
    help|-h|--help)
      usage
      ;;
    paths)
      resolve_share
      cmd_paths
      ;;
    snapshot|open|list|init)
      resolve_share
      ensure_home
      "cmd_$command" "$@"
      ;;
    *)
      echo "tabrot: unknown command '$command'" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
```

Changes vs the old script, for the reviewer: `TABROT_VERSION` added; data paths moved from `$DIR/...` to `$TABROT_HOME/...`; `resolve_share()` + `ensure_home()` added; `cmd_version`/`cmd_paths` added; `cmd_snapshot` uses `mktemp` instead of the predictable `/tmp/tabrot_snapshot_err.$$` and no longer mkdirs; `cmd_list`/`cmd_init` no longer mkdir (ensure_home owns that); `usage` documents the new commands and the data home; `main` routes version/help before any resolution so they work even on a broken install. `detect_browser` and `cmd_open` behavior unchanged.

- [ ] **Step 4: Run the CLI test to verify it passes**

Run: `tests/test_cli.sh`
Expected: `ok: CLI smoke passed (.../tests/../tabrot)` and exit 0.

- [ ] **Step 5: Run the parser test to verify nothing else broke**

Run: `python3 tests/test_parser.py`
Expected: exit 0 (same output as before this task — the parser was not touched).

- [ ] **Step 6: shellcheck both scripts**

Run: `shellcheck tabrot tests/test_cli.sh` (if shellcheck is missing locally: `brew install shellcheck`)
Expected: no output, exit 0. If findings appear, fix them in place — do not add `# shellcheck disable` without a comment justifying why.

- [ ] **Step 7: Manual sanity check of real behavior (macOS, Brave installed)**

```bash
TABROT_HOME="$(mktemp -d)" ./tabrot snapshot
```
Expected: `Seeded ledger: /var/folders/.../PARKED.md` then `Snapshot: /var/folders/.../snapshots/<today>.txt (N tabs)` with N > 0. This exercises the real parser through the new path plumbing.

- [ ] **Step 8: Commit**

```bash
git add tabrot tests/test_cli.sh
git commit -m "feat: XDG-style data home (~/.tabrot), share resolution, version/paths commands"
```

---

### Task 2: Makefile (install/uninstall/test/lint/dist)

**Files:**
- Create: `Makefile`

**Interfaces:**
- Consumes: `TABROT_VERSION` sed pattern from Task 1; `tests/test_cli.sh` with `TABROT_BIN` override.
- Produces: `make install` layout `$(DESTDIR)$(PREFIX)/bin/tabrot` + `$(DESTDIR)$(PREFIX)/share/tabrot/{snss_tabs.py,TRIAGE.md,templates/PARKED.template.md}` (exactly what Task 1's installed-mode resolution and Task 3's deb staging expect); targets `install`, `uninstall`, `test`, `lint`, `dist`, `clean` (Task 3 adds `deb`; Tasks 5–6 call `make test`, `make lint`, `make dist`).

- [ ] **Step 1: Write the Makefile**

Create `Makefile` with exactly this content (recipe lines are TABS, not spaces):

```make
# tabrot — install, test, and package. See docs/superpowers/specs/ for design.
SHELL := /bin/bash

VERSION := $(shell sed -n 's/^TABROT_VERSION="\(.*\)"/\1/p' tabrot)

PREFIX  ?= /usr/local
BINDIR   = $(PREFIX)/bin
SHAREDIR = $(PREFIX)/share/tabrot

.PHONY: all test lint install uninstall dist clean

all: test

test:
	python3 tests/test_parser.py
	tests/test_cli.sh

lint:
	shellcheck tabrot tests/test_cli.sh

install:
	install -d "$(DESTDIR)$(BINDIR)" "$(DESTDIR)$(SHAREDIR)/templates"
	install -m 0755 tabrot "$(DESTDIR)$(BINDIR)/tabrot"
	install -m 0644 src/snss_tabs.py "$(DESTDIR)$(SHAREDIR)/snss_tabs.py"
	install -m 0644 TRIAGE.md "$(DESTDIR)$(SHAREDIR)/TRIAGE.md"
	install -m 0644 templates/PARKED.template.md "$(DESTDIR)$(SHAREDIR)/templates/PARKED.template.md"

uninstall:
	rm -f "$(DESTDIR)$(BINDIR)/tabrot"
	rm -rf "$(DESTDIR)$(SHAREDIR)"

dist:
	mkdir -p dist
	git archive --format=tar.gz --prefix=tabrot-$(VERSION)/ -o dist/tabrot-$(VERSION).tar.gz HEAD

clean:
	rm -rf build dist
```

- [ ] **Step 2: Run the test and lint targets**

Run: `make test && make lint`
Expected: parser test exits 0, `ok: CLI smoke passed`, shellcheck silent, overall exit 0.

- [ ] **Step 3: Verify install → installed-layout smoke → uninstall roundtrip**

```bash
make install DESTDIR="$PWD/build/fakeroot" PREFIX=/usr
test -x build/fakeroot/usr/bin/tabrot
test -f build/fakeroot/usr/share/tabrot/snss_tabs.py
test -f build/fakeroot/usr/share/tabrot/TRIAGE.md
test -f build/fakeroot/usr/share/tabrot/templates/PARKED.template.md
TABROT_BIN="$PWD/build/fakeroot/usr/bin/tabrot" tests/test_cli.sh
make uninstall DESTDIR="$PWD/build/fakeroot" PREFIX=/usr
test ! -e build/fakeroot/usr/bin/tabrot
test ! -e build/fakeroot/usr/share/tabrot
rm -rf build
```
Expected: every `test` succeeds; the smoke test prints `ok: CLI smoke passed (.../build/fakeroot/usr/bin/tabrot)` — proving the installed-mode `../share/tabrot` resolution works.

- [ ] **Step 4: Verify dist tarball**

```bash
make dist
tar -tzf dist/tabrot-0.2.0.tar.gz | grep -E 'tabrot-0.2.0/(tabrot|src/snss_tabs.py|TRIAGE.md|Makefile)$'
rm -rf dist
```
Expected: all four paths listed (git archive packs HEAD, so the tarball reflects the last commit — Task 1 must be committed first).

- [ ] **Step 5: Commit**

```bash
git add Makefile
git commit -m "build: Makefile with install/uninstall (PREFIX+DESTDIR), test, lint, dist"
```

---

### Task 3: Debian packaging (control, copyright, `make deb`)

**Files:**
- Create: `packaging/deb/control.in`
- Create: `packaging/deb/copyright`
- Modify: `Makefile` (add `deb` target and extend `.PHONY`)

**Interfaces:**
- Consumes: `make install DESTDIR=... PREFIX=/usr` from Task 2; `$(VERSION)` from the Makefile.
- Produces: `make deb` → `dist/tabrot_$(VERSION)_all.deb` (Task 6's release workflow builds and smoke-installs it).

- [ ] **Step 1: Write the control template**

Create `packaging/deb/control.in`:

```
Package: tabrot
Version: {{VERSION}}
Architecture: all
Section: utils
Priority: optional
Maintainer: zcor <zcor@users.noreply.github.com>
Depends: bash, python3
Homepage: https://github.com/zcor/tabrot
Description: browser-tab triage and launcher CLI
 Reads every open window and tab straight from a Chromium-family
 browser's session files on disk, supports a plain-markdown LLM triage
 protocol (JUNK/PARK/PIN/TODO), and reopens curated URL manifests in
 fresh browser windows. Plain text, local-only, no runtime dependencies
 beyond bash and python3.
```

(Format notes for the implementer: the extended description lines start with one space; there is no trailing blank line; `{{VERSION}}` is replaced by the Makefile at build time.)

- [ ] **Step 2: Write the DEP-5 copyright file**

Create `packaging/deb/copyright` (copyright holder matches `LICENSE`):

```
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: tabrot
Source: https://github.com/zcor/tabrot

Files: *
Copyright: 2026 Gerrit Hall
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
```

Verify the copyright line against `LICENSE` (currently `Copyright (c) 2026 Gerrit Hall`) — if LICENSE differs, match LICENSE.

- [ ] **Step 3: Add the `deb` target to the Makefile**

In `Makefile`, change the `.PHONY` line to:

```make
.PHONY: all test lint install uninstall dist deb clean
```

and append after the `dist:` target:

```make
deb:
	@command -v dpkg-deb >/dev/null 2>&1 || { echo "make deb requires dpkg-deb (run on Debian/Ubuntu or in CI)." >&2; exit 1; }
	rm -rf build/debroot
	$(MAKE) install DESTDIR=build/debroot PREFIX=/usr
	install -d build/debroot/DEBIAN build/debroot/usr/share/doc/tabrot
	sed 's/{{VERSION}}/$(VERSION)/' packaging/deb/control.in > build/debroot/DEBIAN/control
	install -m 0644 packaging/deb/copyright build/debroot/usr/share/doc/tabrot/copyright
	mkdir -p dist
	dpkg-deb --build --root-owner-group build/debroot dist/tabrot_$(VERSION)_all.deb
```

- [ ] **Step 4: Test what is testable locally**

On macOS (no dpkg-deb):
```bash
make deb; echo "exit=$?"
```
Expected: `make deb requires dpkg-deb (run on Debian/Ubuntu or in CI).` and `exit=2` (make's nonzero exit) — the guard works, no half-built artifacts.

Also verify the control rendering in isolation:
```bash
sed 's/{{VERSION}}/0.2.0/' packaging/deb/control.in | head -2
```
Expected output:
```
Package: tabrot
Version: 0.2.0
```

If Docker is available, optionally verify the full build: `docker run --rm -v "$PWD":/w -w /w ubuntu:24.04 bash -c 'apt-get update -qq && apt-get install -y -qq make dpkg-dev python3 >/dev/null && make deb && dpkg-deb --info dist/tabrot_0.2.0_all.deb'` — expected: `Package: tabrot`, `Architecture: all` in the info output. If Docker is not available, skip; the release workflow (Task 6) covers it.

- [ ] **Step 5: Commit**

```bash
git add packaging/deb/control.in packaging/deb/copyright Makefile
git commit -m "build: debian package metadata and make deb target"
```

---

### Task 4: Homebrew formula template

**Files:**
- Create: `packaging/homebrew/tabrot.rb.template`

**Interfaces:**
- Consumes: nothing at build time (placeholders only).
- Produces: template with `{{URL}}` and `{{SHA256}}` placeholders; Task 6's release workflow renders it with `sed -e "s|{{URL}}|...|" -e "s|{{SHA256}}|...|"` and pushes it to the tap as `Formula/tabrot.rb`. Install block must mirror Task 2's share layout.

- [ ] **Step 1: Write the formula template**

Create `packaging/homebrew/tabrot.rb.template`:

```ruby
class Tabrot < Formula
  desc "Browser-tab triage and launcher CLI"
  homepage "https://github.com/zcor/tabrot"
  url "{{URL}}"
  sha256 "{{SHA256}}"
  license "MIT"

  def install
    bin.install "tabrot"
    pkgshare.install "src/snss_tabs.py" => "snss_tabs.py"
    pkgshare.install "TRIAGE.md"
    pkgshare.install "templates"
  end

  test do
    assert_match "tabrot #{version}", shell_output("#{bin}/tabrot version")
  end
end
```

(Why no python dependency: macOS with Command Line Tools — a Homebrew prerequisite — always has `python3`, and the script's `need_python` check reports it politely otherwise. Per the spec, correctness must not depend on a brew python. `pkgshare` is `share/tabrot`, which the script's installed-mode resolution finds through the prefix symlinks. Deliberate deviation from the spec's placeholder list: no `{{VERSION}}` placeholder — brew derives the version from the tarball filename in `url`, so only `{{URL}}` and `{{SHA256}}` are rendered. Do not add one.)

- [ ] **Step 2: Verify the rendered formula is valid Ruby**

```bash
sed -e 's|{{URL}}|https://github.com/zcor/tabrot/releases/download/v0.2.0/tabrot-0.2.0.tar.gz|' \
    -e 's|{{SHA256}}|0000000000000000000000000000000000000000000000000000000000000000|' \
    packaging/homebrew/tabrot.rb.template > /tmp/tabrot-formula-check.rb
ruby -c /tmp/tabrot-formula-check.rb
rm /tmp/tabrot-formula-check.rb
```
Expected: `Syntax OK`.

- [ ] **Step 3: Commit**

```bash
git add packaging/homebrew/tabrot.rb.template
git commit -m "build: homebrew formula template (rendered by release CI)"
```

---

### Task 5: CI workflow (test + lint + installed-layout smoke on Linux and macOS)

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `make test`, `make lint`, `make install` from Task 2; `TABROT_BIN` from Task 1.
- Produces: green CI on push/PR; the pinned checkout SHA reused by Task 6.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: ensure shellcheck
        run: |
          if ! command -v shellcheck >/dev/null 2>&1; then
            if [ "$RUNNER_OS" = "macOS" ]; then
              brew install shellcheck
            else
              sudo apt-get update && sudo apt-get install -y shellcheck
            fi
          fi

      - name: lint
        run: make lint

      - name: test (checkout layout)
        run: make test

      - name: test (installed layout)
        run: |
          make install DESTDIR="$PWD/build/fakeroot" PREFIX=/usr
          TABROT_BIN="$PWD/build/fakeroot/usr/bin/tabrot" tests/test_cli.sh
```

- [ ] **Step 2: Validate the YAML parses**

Run: `ruby -ryaml -e 'YAML.load_file(".github/workflows/ci.yml"); puts "yaml ok"'`
Expected: `yaml ok`.

- [ ] **Step 3: Re-verify the pinned SHA is the tag it claims to be**

Run: `git ls-remote https://github.com/actions/checkout refs/tags/v4.2.2`
Expected: `11bd71901bbe5b1630ceea73d27597364c9af683	refs/tags/v4.2.2` — must match the SHA used in the workflow.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lint + tests + installed-layout smoke on ubuntu and macos"
```

---

### Task 6: Release workflow (tag → test → artifacts → GitHub Release → tap bump)

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `TABROT_VERSION` sed pattern (Task 1), `make lint test dist deb` (Tasks 2–3), formula template + render sed (Task 4), pinned checkout SHA (Task 5).
- Produces: on `v*` tags — GitHub Release with `tabrot-X.Y.Z.tar.gz` + `tabrot_X.Y.Z_all.deb`, and an updated `Formula/tabrot.rb` in `zcor/homebrew-tabrot`. Requires repo secret `TAP_GITHUB_TOKEN` (created in Task 8).

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/release.yml`:

```yaml
name: release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: verify tag matches script version
        run: |
          tag="${GITHUB_REF_NAME#v}"
          script="$(sed -n 's/^TABROT_VERSION="\(.*\)"/\1/p' tabrot)"
          if [ "$tag" != "$script" ]; then
            echo "tag v$tag does not match TABROT_VERSION=$script in tabrot" >&2
            exit 1
          fi

      - name: install build/test tooling
        run: sudo apt-get update && sudo apt-get install -y shellcheck lintian

      - name: lint and test
        run: make lint test

      - name: build artifacts
        run: make dist deb

      - name: lintian (advisory)
        run: lintian dist/tabrot_*_all.deb || echo "lintian findings above are advisory — triage, do not block"

      - name: smoke-test the installed deb
        run: |
          sudo apt install -y ./dist/tabrot_*_all.deb
          tabrot version
          tabrot paths

      - name: create GitHub release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create "$GITHUB_REF_NAME" dist/tabrot-*.tar.gz dist/tabrot_*_all.deb \
            --title "tabrot $GITHUB_REF_NAME" --generate-notes

      - name: check out the tap
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          repository: zcor/homebrew-tabrot
          token: ${{ secrets.TAP_GITHUB_TOKEN }}
          path: tap

      - name: render and push the formula
        run: |
          version="${GITHUB_REF_NAME#v}"
          url="https://github.com/zcor/tabrot/releases/download/${GITHUB_REF_NAME}/tabrot-${version}.tar.gz"
          sha256="$(sha256sum "dist/tabrot-${version}.tar.gz" | awk '{print $1}')"
          mkdir -p tap/Formula
          sed -e "s|{{URL}}|${url}|" -e "s|{{SHA256}}|${sha256}|" \
            packaging/homebrew/tabrot.rb.template > tap/Formula/tabrot.rb
          cd tap
          git config user.name "tabrot-release"
          git config user.email "zcor@users.noreply.github.com"
          git add Formula/tabrot.rb
          git commit -m "tabrot ${version}"
          git push
```

- [ ] **Step 2: Validate the YAML parses**

Run: `ruby -ryaml -e 'YAML.load_file(".github/workflows/release.yml"); puts "yaml ok"'`
Expected: `yaml ok`.

- [ ] **Step 3: Dry-run the version-check and render logic locally**

```bash
bash -c 'tag="0.2.0"; script="$(sed -n '"'"'s/^TABROT_VERSION="\(.*\)"/\1/p'"'"' tabrot)"; [ "$tag" = "$script" ] && echo "version check ok"'
sed -e "s|{{URL}}|https://github.com/zcor/tabrot/releases/download/v0.2.0/tabrot-0.2.0.tar.gz|" \
    -e "s|{{SHA256}}|1111111111111111111111111111111111111111111111111111111111111111|" \
    packaging/homebrew/tabrot.rb.template | ruby -c -
```
Expected: `version check ok` then `Syntax OK` — the exact sed invocations the workflow runs, proven against the real files.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: tag-driven release (artifacts, GitHub Release, tap formula bump)"
```

---

### Task 7: Documentation & integration updates

**Files:**
- Modify: `README.md` (Quickstart section, lines 77–87 of the current file)
- Modify: `CONTRIBUTING.md` (add test-running note in Ground rules)
- Modify: `templates/PARKED.template.md` (lines 8–11, the "copy this file" paragraph)
- Modify: `integrations/claude-code/SKILL.md` (steps 1, 2, 4 and the closing paragraph)
- Modify: `.gitignore` (add build artifacts)
- Create: `RELEASING.md`

**Interfaces:**
- Consumes: `tabrot paths` keys from Task 1; install commands from Tasks 2–4; release flow from Task 6.
- Produces: nothing consumed by other tasks — this is the user-facing contract.

- [ ] **Step 1: Replace README's Quickstart with Install + Quickstart + data location**

In `README.md`, replace this block:

````markdown
## Quickstart

```bash
git clone https://github.com/zcor/tabrot && cd tabrot
./tabrot snapshot                 # exhume
# feed snapshots/<date>.txt + TRIAGE.md to your LLM of choice; file the verdicts
./tabrot init work                # create a manifest from your PIN verdicts
./tabrot open work                # resurrection on demand
```

Requirements: macOS or Linux, Python 3 (stdlib only), a Chromium-family browser, and the courage to be free.
````

with:

````markdown
## Install

**Homebrew (macOS or Linux):**

```bash
brew install zcor/tabrot/tabrot
```

**Debian/Ubuntu:** grab the `.deb` from the [latest release](https://github.com/zcor/tabrot/releases/latest):

```bash
sudo apt install ./tabrot_0.2.0_all.deb
```

**From source:**

```bash
git clone https://github.com/zcor/tabrot && cd tabrot
sudo make install        # PREFIX=/usr/local by default; DESTDIR supported
```

No install required either — `./tabrot` works straight from the clone.

Requirements: macOS or Linux, Python 3 (stdlib only), a Chromium-family browser, and the courage to be free.

## Quickstart

```bash
tabrot snapshot                  # exhume
# feed the snapshot + TRIAGE.md to your LLM of choice; file the verdicts
tabrot init work                 # create a manifest from your PIN verdicts
tabrot open work                 # resurrection on demand
```

### Where your data lives

Everything tabrot writes — manifests, snapshots, your `PARKED.md` ledger —
lives in `~/.tabrot` (override with `TABROT_HOME`). Run `tabrot paths` to
see every location, including where the `TRIAGE.md` protocol is installed.

**Upgrading from a pre-0.2 checkout?** Your data used to live inside the
repo. Move it once:

```bash
mkdir -p ~/.tabrot/manifests ~/.tabrot/snapshots
mv manifests/*.urls ~/.tabrot/manifests/ 2>/dev/null || true
mv snapshots/*.txt ~/.tabrot/snapshots/ 2>/dev/null || true
mv PARKED.md ~/.tabrot/ 2>/dev/null || true
```

(`manifests/examples/` stays in the repo — it's documentation.)
````

- [ ] **Step 2: Update CONTRIBUTING.md**

In `CONTRIBUTING.md`, insert a new ground rule after the "**Tests.**" bullet (which ends with "...will find the edge case you didn't."):

```markdown
- **Run the suite.** `make test` runs the parser tests and the CLI smoke
  test; `make lint` runs shellcheck. Both must pass before a PR. Neither
  needs a browser, real session files, or anything beyond bash, python3,
  and shellcheck.
```

- [ ] **Step 3: Update the PARKED template's placement paragraph**

In `templates/PARKED.template.md`, replace:

```markdown
Copy this file to the root of wherever you run `tabrot` from (or wherever you
want your real ledger to live) and rename it `PARKED.md`. `.gitignore` in this
repo already excludes your real `PARKED.md` — this template is the only copy
that belongs in version control.
```

with:

```markdown
You don't need to copy this by hand: the first data-touching `tabrot`
command seeds it to `~/.tabrot/PARKED.md` for you (`tabrot paths` prints
the exact location, and `TABROT_HOME` moves it). Your real ledger lives
there — outside any repo, which is exactly where a file full of your own
browsing context belongs. This template is the only copy that belongs in
version control.
```

- [ ] **Step 4: Update the Claude Code integration skill**

In `integrations/claude-code/SKILL.md`, make these four edits:

Edit A — replace step 1's command and parenthetical:

```markdown
1. **Snapshot.** Run the installed tool to exhume the current tab state:

   ```bash
   ./tabrot snapshot
   ```

   (If `tabrot` isn't on PATH or isn't in the current directory, ask the
   user where it's installed, or look for a `tabrot` script at the repo
   root of wherever they point you.) This reads the browser's session
   files directly off disk — nothing is sent anywhere by this step.
```

with:

```markdown
1. **Snapshot.** Run the installed tool to exhume the current tab state:

   ```bash
   tabrot snapshot
   ```

   (If `tabrot` isn't on PATH, ask the user where it lives — a checkout's
   `./tabrot` works identically.) This reads the browser's session files
   directly off disk — nothing is sent anywhere by this step. The command
   prints where the snapshot landed; `tabrot paths` prints every location
   tabrot uses (`snapshots=`, `parked=`, `manifests=`, `triage=`, ...) —
   use it instead of guessing paths anywhere in this skill.
```

Edit B — replace step 2's first sentence:

```markdown
2. **Read the protocol.** Read `TRIAGE.md` from this tabrot checkout in
   full before triaging anything.
```

with:

```markdown
2. **Read the protocol.** Read the file at `tabrot paths`' `triage=` key in
   full before triaging anything.
```

Edit C — in step 4, replace:

```markdown
   - Append PARK lines to the user's `PARKED.md` (create it from
     `templates/PARKED.template.md` if it doesn't exist yet). Append,
     don't overwrite — this is a ledger, not a scratch buffer.
   - Append PIN lines to the relevant project manifest(s) under whatever
     directory the user keeps manifests in (e.g. `work.urls`,
     `personal.urls`), grouped as TRIAGE.md specifies. If a suggested
     project doesn't have a manifest yet, ask before creating one.
```

with:

```markdown
   - Append PARK lines to the user's ledger at `tabrot paths`' `parked=`
     location (tabrot seeds it from the template on first use). Append,
     don't overwrite — this is a ledger, not a scratch buffer.
   - Append PIN lines to the relevant project manifest(s) in the
     `manifests=` directory (e.g. `work.urls`, `personal.urls`), grouped
     as TRIAGE.md specifies. If a suggested project doesn't have a
     manifest yet, ask before creating one (`tabrot init <project>`
     creates it properly).
```

Edit D — replace the closing paragraph:

```markdown
This skill assumes a working `tabrot` checkout is reachable (either on
PATH or at a path the user gives you) so it can run `tabrot snapshot` and
read `TRIAGE.md`. It does not vendor either — it drives the real repo.
```

with:

```markdown
This skill assumes `tabrot` is installed (brew, deb, or `make install`) or
a checkout is reachable, and locates everything else — protocol, ledger,
manifests — via `tabrot paths`. It vendors nothing; it drives the real
tool.
```

- [ ] **Step 5: Write RELEASING.md**

Create `RELEASING.md`:

```markdown
# Releasing tabrot

1. Bump `TABROT_VERSION="X.Y.Z"` in `tabrot`. Commit.
2. `make test lint` — both green.
3. Tag and push:

   ```bash
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```

4. The `release` workflow then: verifies tag == `TABROT_VERSION`, runs
   lint + tests, builds `tabrot-X.Y.Z.tar.gz` (git archive) and
   `tabrot_X.Y.Z_all.deb`, runs lintian (advisory), smoke-installs the
   deb, creates the GitHub Release with both artifacts, and pushes the
   rendered formula to `zcor/homebrew-tabrot`.
5. Verify: `brew install zcor/tabrot/tabrot && tabrot version` on a Mac,
   and `sudo apt install ./tabrot_X.Y.Z_all.deb && tabrot version` on
   Debian/Ubuntu.

## One-time setup

- Tap repo: `zcor/homebrew-tabrot` (public, can start as just a README —
  CI creates `Formula/tabrot.rb`).
- Repo secret `TAP_GITHUB_TOKEN`: fine-grained PAT, **Contents: Read and
  write**, scoped to **only** `zcor/homebrew-tabrot`, set on `zcor/tabrot`.
  Rotate on expiry; it can push exactly one repo, nothing else.

Note: `make dist` packs `HEAD` (git archive), so always commit before
tagging; the tarball never includes uncommitted work.
```

- [ ] **Step 6: Update .gitignore**

Append to `.gitignore`:

```
# Build/packaging artifacts
build/
dist/
```

(The existing `snapshots/*`, `manifests/*.urls`, and `PARKED.md` patterns stay — they keep pre-0.2 checkouts from ever committing user data.)

- [ ] **Step 7: Verify nothing regressed**

Run: `make test && make lint`
Expected: all green — proves the PARKED template edit didn't break ledger seeding (the CLI test asserts the seeded file exists) and the scripts still lint.

- [ ] **Step 8: Review the full diff, then commit**

```bash
git diff --stat
git add README.md CONTRIBUTING.md RELEASING.md templates/PARKED.template.md integrations/claude-code/SKILL.md .gitignore
git commit -m "docs: install instructions, data-home migration, paths-aware integration, release runbook"
```

---

### Task 8: Release v0.2.0 (one-time infra + tag) — PARTIALLY USER-GATED

**Files:** none in this repo (external: `zcor/homebrew-tabrot` repo, repo secret, git tag).

**Interfaces:**
- Consumes: everything above, pushed to `main`.
- Produces: live release; `brew install zcor/tabrot/tabrot` and the `.deb` work for real users.

Steps 2–3 require the maintainer's GitHub credentials (PAT creation is browser-only). The executor performs what `gh` auth allows, and must STOP and hand off — with exact instructions — where it doesn't.

- [ ] **Step 1: Push main and confirm CI is green**

```bash
git push origin main
gh run watch --repo zcor/tabrot
```
Expected: the `ci` workflow passes on both OSes. Do not proceed to tagging until green.

- [ ] **Step 2: Create the tap repo (needs zcor perms)**

```bash
gh repo create zcor/homebrew-tabrot --public --description "Homebrew tap for tabrot" --add-readme
```
If `gh` lacks permission to create under `zcor`, hand this command to the maintainer verbatim.

- [ ] **Step 3: Create TAP_GITHUB_TOKEN (USER ACTION — browser only)**

Maintainer: GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token. Resource owner: `zcor`. Repository access: **Only select repositories → zcor/homebrew-tabrot**. Permissions: **Contents: Read and write**, nothing else. Then:

```bash
gh secret set TAP_GITHUB_TOKEN --repo zcor/tabrot
```
(paste the token when prompted — do not put it in shell history or files)

- [ ] **Step 4: Tag and watch the release**

```bash
git tag v0.2.0
git push origin v0.2.0
gh run watch --repo zcor/tabrot
```
Expected: `release` workflow green; `gh release view v0.2.0 --repo zcor/tabrot` lists `tabrot-0.2.0.tar.gz` and `tabrot_0.2.0_all.deb`; `zcor/homebrew-tabrot` has a new commit `tabrot 0.2.0` containing `Formula/tabrot.rb`.

- [ ] **Step 5: End-to-end install verification (macOS)**

```bash
brew install zcor/tabrot/tabrot
tabrot version        # expected: tabrot 0.2.0
tabrot paths          # expected: share=...Cellar/tabrot/0.2.0/share/tabrot (via prefix symlink)
brew test tabrot      # expected: passes
```
Report the exact outputs. If anything fails, do NOT retag — fix, bump to 0.2.1, and release again per RELEASING.md.
