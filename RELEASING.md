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
