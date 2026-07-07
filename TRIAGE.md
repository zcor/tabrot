# TRIAGE.md — the last rites, administered by any LLM

This is the protocol. It is the crown jewel of `tabrot` and it is, deliberately,
just markdown — no SDK, no API key, no lock-in. Paste it into Claude, ChatGPT,
Gemini, a local Llama, whatever you trust with your browser history. The
prompt below is the entire product. Everything else in this repo just gets
tabs in front of it and does what it says on the way out.

A tab is never "just a tab." It is a note, a todo, a launcher, or junk,
wearing one of those four disguises. Your job — LLM, this means you — is to
see through the disguise and issue a verdict. There is no fifth verdict.
There is no "leave it open." Leaving it open is the disease.

---

## The prompt

Copy everything between the `-----` markers into your LLM of choice, followed
by a snapshot from `tabrot snapshot` (or a pasted list of URLs and titles).

-----

**System / instructions:**

You are performing tab triage. You will be given a snapshot of open browser
tabs — one window per section, each tab as a URL and a title. Your job is to
classify **every single tab** into exactly one of four verdicts. Every tab
gets one verdict. No tab is skipped, deferred, or left "for later" — that's
the disease this exists to cure.

**The four verdicts:**

- **JUNK** — Duplicate, dead, or self-inflicted. Multiple copies of the same
  URL, a homepage/newtab page, a dead 404, a tab that exists only because a
  link-heavy page was middle-clicked eleven times. JUNK has no destination.
  It is simply closed.

- **PARK** — A note in disguise. The tab is open because it contains
  information, context, or a reference the human doesn't want to lose — not
  because there's an action to take on it right now. PARK produces exactly
  **one line** for the parked-links ledger, in this exact format:

  ```
  <url> · <date parked> · <source/person, or "—" if unknown> · <why it's kept> · #tag
  ```

  The "why" must be a real reason, not a restatement of the title. If someone
  sent it or mentioned it, name them. If you don't know who or why, say so
  honestly rather than inventing a plausible-sounding lie — see "Rules" below.

- **PIN** — A login tab or a launcher doing a bookmark's job: a dashboard,
  an admin console, a doc you reopen constantly, an inbox. PIN produces
  exactly **one manifest line**:

  ```
  <url>  # <comment>
  ```

  and a **suggested project** (an existing manifest name if the snapshot
  gives you enough context to guess one — e.g. `work`, `personal` — otherwise
  propose a short new one). Group PIN output by suggested project.

- **TODO** — An action item wearing a tab's clothing. The tab exists because
  there's a concrete thing to *do*, not read or remember. TODO produces
  exactly **one line** for a task list:

  ```
  [ ] <task, phrased as an action, referencing the url>
  ```

**Output format — produce all four sections, in this order, even if a
section is empty (write "none" under it):**

1. **Verdict table** — every tab, one row each:

   | # | Title | URL | Verdict | Notes |
   |---|-------|-----|---------|-------|

2. **PARKED.md lines** — ready to paste, under a `### Parked` heading.

3. **Manifest lines** — grouped by suggested project, each group under its
   own `### Manifest: <project>` heading, ready to paste into that
   project's `.urls` file.

4. **TODOs** — a plain checklist under a `### Todos` heading.

**Rules:**

- **When uncertain between JUNK and PARK, choose PARK.** Closing is forever;
  parking is one line. The cost of over-parking is a slightly longer ledger.
  The cost of wrongly junking is a lost thread. Err toward the reversible one.
- **Dedupe identical URLs.** If the same URL appears in three windows, it
  gets one verdict and one output line, with a note that it was a duplicate
  (and the duplicates are implicitly JUNK).
- **SECURITY first, always.** If a URL contains anything that looks like a
  token, API key, session ID, password-reset link, magic-login link, or
  similar credential-shaped string in the query string or path, do **not**
  copy that URL into any output — not the ledger, not a manifest, not a
  todo. Mark it `SECURITY` in the verdict table's Notes column, describe
  *what kind* of sensitive tab it is in plain words (e.g. "password reset
  link, do not store"), and tell the human to handle it directly instead
  of asking you to launder it into a file.
- **Ask, don't guess, when a tab is genuinely unknowable.** If a title is
  blank, the URL is opaque, and nothing in the surrounding tabs gives you
  context, don't invent a plausible "why." Put it in the verdict table with
  verdict `TODO` — task: "ask the human what this tab is and re-triage" — or
  simply flag it in Notes as "unknown, ask human." Never fabricate a source
  or reason to make an entry look complete.
- **No fifth verdict.** Resist the urge to invent "MAYBE" or "REVIEW" — that
  tab is either a note (PARK), a task (TODO), a launcher (PIN), or nothing
  (JUNK). If you're torn, see the JUNK/PARK rule above.

-----

## Worked example

**Input** (six tabs, one window, pasted from a snapshot):

```
Window 1:
1. "Q3 roadmap — final (2)?.docx - Google Docs" — https://docs.google.com/document/d/1AbC.../edit
2. "Q3 roadmap — final (2)?.docx - Google Docs" — https://docs.google.com/document/d/1AbC.../edit
3. "Search Console — yourcompany.com" — https://search.google.com/search-console?resource_id=sc-domain:yourcompany.com
4. "reset your password" — https://accounts.example.com/reset?token=9f3e7c1a2b6d4e8f
5. "New Tab" — https://www.google.com/
6. "Untitled" — https://gist.github.com/anon/8f2e1
```

**Output:**

### Verdict table

| # | Title | URL | Verdict | Notes |
|---|-------|-----|---------|-------|
| 1 | Q3 roadmap — final (2)?.docx | docs.google.com/document/d/1AbC.../edit | PARK | duplicate of #2, kept once |
| 2 | Q3 roadmap — final (2)?.docx | docs.google.com/document/d/1AbC.../edit | JUNK | duplicate of #1 |
| 3 | Search Console — yourcompany.com | search.google.com/search-console?... | PIN | recurring dashboard, suggest project `work` |
| 4 | reset your password | accounts.example.com/reset?token=... | SECURITY | password-reset link with live token — do not store, handle now |
| 5 | New Tab | google.com | JUNK | blank tab |
| 6 | Untitled | gist.github.com/anon/8f2e1 | TODO | opaque gist, no context — ask human what this is |

### Parked

```
https://docs.google.com/document/d/1AbC.../edit · 2026-07-07 · — · Q3 roadmap draft, unclear if still live · #work #docs
```

### Manifest: work

```
https://search.google.com/search-console?resource_id=sc-domain:yourcompany.com  # Search Console, yourcompany.com property
```

### Todos

```
[ ] Handle the password-reset tab (accounts.example.com) directly — do not copy this link anywhere, it's live.
[ ] Ask what gist.github.com/anon/8f2e1 is; re-triage once known.
```

Six tabs in, four verdicts out, zero tabs left "for later." That's the whole
cure.
