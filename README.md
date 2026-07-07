# tabrot

**Humanity's most widespread untreated disease. This is the cure.**

![tabs closed](https://img.shields.io/badge/tabs_closed-144-critical) ![guilt](https://img.shields.io/badge/guilt-0-success) ![disease](https://img.shields.io/badge/tabrot-terminal-blueviolet) ![dependencies](https://img.shields.io/badge/dependencies-none-informational)

---

## The Disease

**tabrot** *(n., clinical)* — the progressive accumulation of browser tabs, each one a promise you made to a future self who never showed up for the meeting.

We have decoded the genome. We have landed robots on other planets. We have built machines that write poetry and hold conversations and prove theorems. **Not one member of our species can close their browser tabs.** Presidents suffer from tabrot. Surgeons operate between windows containing 300 open tabs. Somewhere right now, a person who optimizes distributed systems for a living has a tab open from 2023 because *it might be important*. It is not important. They cannot close it. Neither can you.

This is not a productivity problem. This is a disease with a pathology, and it deserves to be treated like one.

### Pathology: the four stages

| Stage | Presentation | Prognosis |
|---|---|---|
| **I — Colonization** | 10–30 tabs. Patient claims they are "all current." Patient is lying. | Reversible |
| **II — Sedimentation** | Tabs form geological strata. The bottom layers can no longer be identified without carbon dating. Favicon-only navigation begins. | Intervention advised |
| **III — Metastasis** | Multiple windows. Windows *about* other windows. A tab kept open solely to remind the patient of a different tab. | Seek help |
| **IV — Acceptance** | Patient opens a *new* window because the old one is "full." The old window is never seen again but never closed. It runs forever, warm, humming, a hospice of intentions. | Historically terminal. **Until now.** |

### Etiology: why you can't just close them

Because every tab is one of exactly four things wearing a disguise:

1. **A note you never filed** — *origami-whatever.chat, open for 6 weeks because James said to look at it and closing it means forgetting James.*
2. **A todo you never tracked** — *the tab where you were finally going to deal with that thing.*
3. **A login bookmark doing a launcher's job** — *six Search Console tabs kept alive because finding the right Google account again is twenty minutes of your one wild and precious life.*
4. **Junk** — *eleven copies of your own homepage. You know. You know what you did.*

Closing a tab without giving its cargo a home isn't tidying — it's *amnesia*. Your brain knows this. That's why your thumb hovers over the ✕ and retreats. The disease is not the tabs. **The disease is that your tabs have no afterlife.**

---

## The Cure

`tabrot` gives every tab somewhere better to be. Three organs, no dependencies, plain files:

### 1. 📸 Snapshot — exhume the graveyard
```bash
tabrot snapshot
```
Reads your Chromium-family browser's session files **directly off disk** (Brave, Chrome, Edge, Arc, Chromium — no extension, no cloud, nothing leaves your machine) and produces a clean list of every window and tab: URL and title. Yes, even the window you minimized in shame during a different fiscal year.

### 2. 🧠 Triage — the last rites, administered by any LLM
Feed the snapshot to the model of your choice with the included [`TRIAGE.md`](TRIAGE.md) protocol. Every tab gets exactly one verdict:

| Verdict | Meaning | Where it goes |
|---|---|---|
| `JUNK` | Duplicate, dead, or self-inflicted | Nowhere. Freedom. |
| `PARK` | A note in disguise | One line in `PARKED.md` — *with why you kept it and who told you to* |
| `PIN` | A login/launcher tab | A project manifest (see below) |
| `TODO` | An action item in disguise | Your actual task system |

Once a tab's cargo is housed, closing it costs nothing. That's the entire trick. That's the cure. (Claude Code user? There's a drop-in skill in [`integrations/claude-code/`](integrations/claude-code/). Any other model works fine — the protocol is just markdown.)

### 3. 🚀 Launchers — never re-hoard
```bash
tabrot open work
```
One command opens a fresh window with that project's operator links from a plain-text manifest — the right dashboards, the right docs, and (the killer feature) **the right Google account baked into every deep link** via the `/u/N` index, so you land logged-in instead of spelunking through the account switcher. The tabs you kept open "so you wouldn't lose them" are now summonable. Close the window like a person with nothing to fear.

---

## Origin story

This tool exists because a human with a **144-tab, 12-window** Brave session — a systems person, a professional, someone you might otherwise trust — finally gave up and asked a frontier AI to intervene. The model parsed the session file off disk, identified the six Search Console tabs, the seven Gmail inboxes, the eight copies of `x.com/home`, the untitled tab at position 19 that turned out to be the only actual action item, and a tab kept open for six weeks out of loyalty to a friend named James.

Ten of twelve windows closed that afternoon. Nothing was lost. The patient reported feeling "so happy."

It took one of the most advanced reasoning systems ever constructed to close one man's browser tabs. **It should not have to take yours.** The workflow is now this repository.

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

## Philosophy

- **Local-only.** Your tabs are read from disk and never transmitted anywhere. What you feed your LLM is your business.
- **Plain text forever.** Manifests, the parked ledger, snapshots — all flat files. Greppable by you, your scripts, and your agents, in perpetuity.
- **The ledger is the product.** `PARKED.md` is where tabs go to *matter* instead of rot: every kept link records *why* and *who*, so your future self — or your future agent — finds it with context attached.
- **No willpower components.** Systems that require discipline are prayers. This is plumbing.

## Prior art / non-solutions

Tab groups (organized rot), OneTab (a mass grave with a search bar), bookmarks (where links go to be forgotten *formally*), "I'll deal with it this weekend" (longitudinal studies ongoing since 1994).

## Roadmap

- Firefox session support (the other pandemic)
- `tabrot doctor` — staging diagnosis from your own snapshot
- Scheduled snapshots + diff ("what did you rot this week")

## License

MIT. Close your tabs. Tell your loved ones.
