# Contributing

Thank you for enlisting in the fight against humanity's silent pandemic.
Tabrot doesn't respect borders, employers, or operating systems, and
neither does the cure — patches welcome.

## Ground rules

- **stdlib only.** `tabrot` reads session files off disk and writes plain
  text; it does not need a package manager to do either. No runtime
  dependencies, in `src/` or anywhere else. If your patch needs a
  dependency to work, that's a sign the patch is solving the wrong
  problem — find the stdlib way, or open an issue and make the case.
  (Test-only tooling is judged the same way: prefer `unittest` over
  pulling in a framework.)

- **Privacy, absolutely.** This is a public repo. Fixtures, examples,
  test data, and docs must contain **zero real personal data** — no real
  names, no real email addresses, no real URLs that belong to an actual
  person or company, no real session files from anyone's actual browser.
  Use placeholder domains (`example.com`, `yourcompany.com`), fictional
  names, and synthetic session-file fixtures constructed by hand or by a
  generator, never copy-pasted from your own `~/Library/Application
  Support` or `~/.config`. If a bug report needs a real snapshot to
  reproduce, sanitize it first — swap every real URL, title, and account
  index for a placeholder before it goes anywhere near an issue or a PR.

- **Tests.** New behavior in `src/` needs a test in `tests/`. Bug fixes
  need a regression test that fails without the fix. We're not chasing a
  coverage number, but "I fixed it and it works on my machine" is not a
  test — someone else's 400-tab fever dream will find the edge case you
  didn't.

- **Run the suite.** `make test` runs the parser tests and the CLI smoke
  test; `make lint` runs shellcheck. Both must pass before a PR. Neither
  needs a browser, real session files, or anything beyond bash, python3,
  and shellcheck.

- **Keep the protocol in `TRIAGE.md` the source of truth.** If you're
  changing triage behavior, update `TRIAGE.md` first and make the code
  match it, not the other way around — the protocol is meant to be
  readable and pasteable independent of this codebase, and it should
  never drift from what the tool actually does.

## Most wanted

**Firefox support.** Right now `tabrot snapshot` only reads
Chromium-family session files (Brave, Chrome, Edge, Arc, Chromium).
Firefox is the other pandemic and currently untreated by this tool — if
you're willing to reverse-engineer `sessionstore.jsonlz4` and friends, you
will have the eternal gratitude of everyone who made the mistake of
"just trying Firefox for a while."

Other good targets: `tabrot doctor` (a staging diagnosis straight from a
snapshot — see the README's four stages), and scheduled-snapshot diffing
("what did you rot this week"). Check the README's Roadmap section before
starting something large, and consider opening an issue first so effort
isn't duplicated.

## Sending a patch

Small, focused PRs. Explain the symptom, not just the fix — what tabrot
disease were you treating? Screenshots of your own 200-tab window are
encouraged but, per the privacy rule above, please blur or redact
anything real before you post it.
