# PARKED.md

This is the ledger. Every tab triaged as `PARK` by [`TRIAGE.md`](../TRIAGE.md)
gets exactly one line here — not because you're going to read it again
tomorrow, but because a tab you closed with nowhere to go is amnesia, and a
tab you parked with context attached is just... filed.

Copy this file to the root of wherever you run `tabrot` from (or wherever you
want your real ledger to live) and rename it `PARKED.md`. `.gitignore` in this
repo already excludes your real `PARKED.md` — this template is the only copy
that belongs in version control.

## Format

One line per entry, appended under the `## Entries` heading, oldest or
newest first (your call — nobody's grading this):

```
<url> · <date parked, YYYY-MM-DD> · <source/person, or "—" if unknown> · <why it's kept> · #tag
```

- **url** — the full URL, as-is. (Exception: never park a URL containing a
  token, session ID, or credential — see `TRIAGE.md`'s SECURITY rule. That
  kind of tab doesn't belong in a plain-text file, parked or not.)
- **date parked** — when you filed it, not when the tab was originally
  opened. You'll want this later to notice things that have been "parked"
  for eleven months, which is a diagnosis, not a filing status.
- **source/person** — who sent it, who mentioned it, or what triggered you
  opening it. "—" if genuinely unknown. Don't guess a name to fill the
  column; an honest "—" is worth more than a fabricated source.
- **why it's kept** — the actual reason, in your own words. Not a
  restatement of the page title.
- **#tag** — one or more free-form tags for future grepping. `#work`,
  `#personal`, `#reading`, `#waiting-on-someone`, whatever taxonomy you
  actually use.

## Intake tray

This file is a waiting room, not a warehouse. Anything here that's clearly
scoped to a specific project should eventually **drain out** to that
project's own docs (its README, its issue tracker, its own notes file) —
`PARKED.md` is for the stuff that doesn't have a better home yet, or that
spans projects. If you find yourself with fifteen entries all tagged
`#project-x`, that's a sign project-x needs its own notes file, not a
bigger ledger.

## Entries

```
https://en.wikipedia.org/wiki/Studor_vent · 2026-06-12 · plumber (Kyle) · he referenced this mid-quote and I wanted to understand what he was talking about before agreeing to it · #reference #plumbing

https://news.ycombinator.com/item?id=39821234 · 2026-06-18 · — · thread on local-first sync, wanted to finish reading before it rotates off the front page · #reading #someday

https://example.com/blog/why-we-rewrote-our-scheduler · 2026-06-30 · Dana (Slack) · she said "this is basically what we should do for the queue rewrite," want to reread before the design review · #work #todo-adjacent
```
