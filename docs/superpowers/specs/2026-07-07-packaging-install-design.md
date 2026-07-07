# tabrot packaging & installation — design

**Date:** 2026-07-07
**Status:** approved (design review with maintainer)
**Target release:** v0.2.0

## Problem

tabrot currently runs only from a git checkout. The `tabrot` script resolves
everything — the Python parser, `snapshots/`, `manifests/` — relative to its
own file location, so installing it to a system `bin/` directory breaks it:
it would look for its parser next to itself and try to write user data into
the install prefix. The goal is standard installation (`make install`,
`brew install`, a `.deb`) without giving up the project's zero-dependency,
plain-text character.

## Decisions (settled in design review)

1. **Channels:** Makefile install + Homebrew tap (`zcor/homebrew-tabrot`) +
   `.deb` attached to GitHub Releases. No hosted apt repo, no Launchpad PPA,
   no homebrew-core submission at this stage.
2. **Artifact shape:** bin + share layout. No build step; repo files are
   installed as-is. (Single-file build and a Go/Rust rewrite were considered
   and rejected: the former complicates dev/test and diverges installed
   artifact from source; the latter buys nothing for a bash+stdlib-python
   tool and contradicts the plain-text philosophy.)
3. **User data home:** `~/.tabrot`, overridable via `TABROT_HOME`. Same
   behavior whether tabrot is installed or run from a checkout — no dual
   mode for data.
4. **Releases:** tag-driven GitHub Actions pipeline. Push `vX.Y.Z` tag →
   test → build artifacts → GitHub Release → auto-update tap formula.

## 1. CLI refactor (`tabrot` script)

### Data paths

- `TABROT_HOME="${TABROT_HOME:-$HOME/.tabrot}"`
- `MANIFESTS="$TABROT_HOME/manifests"`, `SNAPSHOTS="$TABROT_HOME/snapshots"`,
  `PARKED="$TABROT_HOME/PARKED.md"`
- `ensure_home()` runs at the start of the data-touching commands —
  `snapshot`, `open`, `init`, `list` — and does two things: `mkdir -p` the
  subdirectories, and seed `PARKED.md` from the template when it does not
  exist yet. `version`, `paths`, and `help` make no filesystem changes.

### Code-asset resolution (parser, TRIAGE.md, templates)

Resolution order, first hit wins:

1. `TABROT_SHARE` env var, if set (dev/debug escape hatch).
2. Checkout layout: `$DIR/src/snss_tabs.py` exists next to the script →
   parser `$DIR/src/snss_tabs.py`, protocol `$DIR/TRIAGE.md`, templates
   `$DIR/templates/`.
3. Installed layout: `$DIR/../share/tabrot/` → parser `snss_tabs.py`,
   protocol `TRIAGE.md`, templates `templates/`, all inside that directory.
4. Neither found → explicit error: name the paths tried, suggest
   reinstalling or setting `TABROT_SHARE`.

Note on symlinks: `$DIR` is computed from `dirname "${BASH_SOURCE[0]}"`
*without* resolving the file's own symlink. This is deliberate and is what
makes prefix-sibling resolution work everywhere we ship: Homebrew links both
`bin/tabrot` and `share/tabrot` from the Cellar into the prefix, dpkg
installs to `/usr/bin` + `/usr/share/tabrot`, and `make install` mirrors the
same layout under any `PREFIX`. Do **not** introduce `readlink -f` (not
portable to macOS bash 3.2); `TABROT_SHARE` covers exotic setups.

### New subcommands

- `tabrot version` (also `--version`, `-v`): prints `tabrot X.Y.Z`. Single
  source of truth is a `TABROT_VERSION="0.2.0"` variable at the top of the
  script. CI asserts the release tag matches it.
- `tabrot paths`: machine-readable `key=value` lines so integrations and
  agents never guess locations:
  `home=`, `manifests=`, `snapshots=`, `parked=`, `share=`, `parser=`,
  `triage=`, `templates=`.
- `usage()` updated to list both.

### Behavior preserved

`snapshot`, `open`, `init`, `list` keep their semantics; only the locations
of data and assets change. `set -euo pipefail`, the polite
python3-missing error, and browser detection are untouched.

### In-scope hardening

The snapshot error capture currently writes to the predictable path
`/tmp/tabrot_snapshot_err.$$` (symlink-attack surface on shared machines).
Replace with `mktemp`, cleaned up on all paths.

## 2. Makefile

Variables: `PREFIX ?= /usr/local`, `BINDIR = $(PREFIX)/bin`,
`SHAREDIR = $(PREFIX)/share/tabrot`, full `DESTDIR` support on install and
uninstall (required by dpkg staging and distro packagers).

| Target | Behavior |
|---|---|
| `install` | `tabrot` → `$(DESTDIR)$(BINDIR)/tabrot` (0755); `src/snss_tabs.py`, `TRIAGE.md`, `templates/` → `$(DESTDIR)$(SHAREDIR)/` (0644) |
| `uninstall` | remove exactly what `install` created |
| `test` | `python3 tests/test_parser.py` then `tests/test_cli.sh` (no pytest — zero-dep stays true) |
| `lint` | `shellcheck tabrot tests/test_cli.sh` |
| `dist` | `tabrot-$(VERSION).tar.gz` from git archive; `VERSION` extracted from the script's `TABROT_VERSION` line |
| `deb` | stage via `make install DESTDIR=…`, generate control from template, `dpkg-deb --build --root-owner-group` → `dist/tabrot_$(VERSION)_all.deb`. Linux-oriented; on a machine without `dpkg-deb` it exits with a clear message |

## 3. Homebrew tap

- New repo: `zcor/homebrew-tabrot`. Install command:
  `brew install zcor/tabrot/tabrot`.
- The formula's source of truth lives in **this** repo at
  `packaging/homebrew/tabrot.rb.template` with `{{VERSION}}`, `{{URL}}`,
  `{{SHA256}}` placeholders. The release workflow renders it and pushes
  `Formula/tabrot.rb` to the tap — the tap repo is never hand-edited.
- Formula body: `desc`, `homepage`, `url` (GitHub release tarball),
  `sha256`, `license "MIT"`; `install` does `bin.install "tabrot"` and
  `pkgshare.install "src/snss_tabs.py", "TRIAGE.md", "templates"`
  (yielding `share/tabrot/{snss_tabs.py,TRIAGE.md,templates/}` — the layout
  the script's installed-mode resolution expects); `test do` runs
  `tabrot version` and asserts the version string.
- Python dependency: default is **no hard brew dependency** — macOS with
  Command Line Tools (a Homebrew prerequisite) always has `python3`, and the
  script's runtime check covers the rest. At implementation time, if a
  clean `uses_from_macos`-style declaration verifies on Linuxbrew, it may be
  added; correctness must not depend on it.

## 4. Debian package

- `packaging/deb/control.in` template. Fields: `Package: tabrot`,
  `Version: {{VERSION}}`, `Architecture: all`, `Section: utils`,
  `Priority: optional`, `Depends: bash, python3`,
  `Maintainer: zcor <email — see Open items>`,
  `Homepage: https://github.com/zcor/tabrot`, short + extended Description.
- Installed layout: `/usr/bin/tabrot`, `/usr/share/tabrot/…`,
  `/usr/share/doc/tabrot/copyright` (MIT text, DEP-5 format).
- `lintian` runs in CI on the built package; findings are triaged, not
  driven to zero (e.g. the missing-man-page warning is accepted for now).
- User install path: download from the GitHub Release, then
  `sudo apt install ./tabrot_0.2.0_all.deb`.

## 5. Versioning & CI

- Semver, tags `vX.Y.Z`, first packaged release **v0.2.0**.
- All GitHub Actions pinned by full commit SHA (SEAL supply-chain rule).
- Secret: `TAP_GITHUB_TOKEN` — fine-grained PAT, `contents: write`,
  scoped to `zcor/homebrew-tabrot` only.

**`.github/workflows/ci.yml`** (push + PR): matrix `ubuntu-latest` +
`macos-latest`; runs `make test`, `make lint`, and an installed-layout
smoke: `make install` into a temporary `DESTDIR`, then run
`tests/test_cli.sh` against that installed binary.

**`.github/workflows/release.yml`** (tag `v*`):
1. Assert tag version == `TABROT_VERSION` in the script (fail fast on drift).
2. `make test` + `make lint`.
3. `make dist deb`.
4. Install smoke test: `sudo apt install ./dist/tabrot_*_all.deb` directly
   on the Ubuntu runner, then run `tabrot version` and `tabrot paths`.
5. `gh release create` with the tarball and `.deb` attached.
6. Render the formula template with version/url/sha256 of the released
   tarball; commit to the tap via `TAP_GITHUB_TOKEN`.

## 6. Documentation & integration updates

- **README:** new Install section (brew tap, `.deb`, `make install`,
  run-from-clone), "where your data lives" (`~/.tabrot`, `TABROT_HOME`),
  and an "upgrading from a checkout" note: one documented `mv` of existing
  `manifests/*.urls`, `snapshots/*.txt`, `PARKED.md` into `~/.tabrot/`.
  No migration subcommand (YAGNI). Quickstart updated away from
  clone-and-`./tabrot` as the only path.
- **integrations/claude-code/SKILL.md:** use `tabrot` from PATH; locate the
  protocol and ledger via `tabrot paths` instead of "this checkout";
  checkout fallback retained for unpackaged users.
- **templates/PARKED.template.md:** wording updated — the real ledger lives
  at `~/.tabrot/PARKED.md`, not repo root.
- **CONTRIBUTING.md:** document `make test` / `make lint`.
- **RELEASING.md:** the release runbook — bump `TABROT_VERSION`, tag, push,
  what CI does, required secret.
- **.gitignore:** keep the legacy repo-local ignore patterns so pre-0.2
  checkouts never accidentally commit user data.

## 7. Testing

- `tests/test_parser.py` — unchanged.
- `tests/test_cli.sh` — new CLI smoke test, runs against
  `TABROT_HOME="$(mktemp -d)"`, needs no browser or session files:
  - `version` / `--version` print the expected string, exit 0
  - `paths` prints all expected keys pointing under the temp home
  - `init foo` creates the manifest; `init foo` again fails without
    overwriting; `list` shows `foo`
  - first data-touching command seeds `PARKED.md` from the template
  - `help` exits 0; unknown command exits nonzero with usage on stderr
  - runs both from checkout layout and (in CI) against the installed layout
- CI runs the suite on Linux and macOS; the release workflow additionally
  smoke-tests the installed `.deb`.

## Files created / modified

| Path | Change |
|---|---|
| `tabrot` | refactor paths, add `version`/`paths`, `ensure_home`, mktemp fix |
| `Makefile` | new |
| `packaging/homebrew/tabrot.rb.template` | new |
| `packaging/deb/control.in` | new |
| `packaging/deb/copyright` | new |
| `.github/workflows/ci.yml`, `release.yml` | new |
| `tests/test_cli.sh` | new |
| `README.md`, `CONTRIBUTING.md`, `RELEASING.md`, `integrations/claude-code/SKILL.md`, `templates/PARKED.template.md`, `.gitignore` | updated |
| `zcor/homebrew-tabrot` (separate repo) | created once, then CI-managed |

## Non-goals

- homebrew-core submission, hosted apt repository, Launchpad PPA
- man page (lintian warning accepted)
- migration subcommand
- Firefox support, `tabrot doctor` (separate roadmap items)
- Windows support

## Open items (implementation-time)

- Brew python declaration: verify whether a `uses_from_macos`-style python
  reference is valid/beneficial on Linuxbrew; ship without it if unclear.
- Maintainer email for the deb control file.
