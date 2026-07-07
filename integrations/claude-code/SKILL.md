---
name: tabrot
description: Use when the user wants to close their tabs, mentions tab cleanup, says they have too many tabs open, or invokes "tabrot" directly. Triages an open-tab snapshot into JUNK/PARK/PIN/TODO, files the results, and reports which windows are safe to close.
---

# tabrot: tab triage

The user has tabrot — they have too many browser tabs open and want out.
This skill runs the cure end to end: snapshot, triage, file, report. Do not
just summarize the tabs; actually write PARK lines to their ledger and
append PIN lines to their manifests, the way the protocol specifies.

## Steps

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

2. **Read the protocol.** Read the file at `tabrot paths`' `triage=` key in
   full before triaging anything. It defines the four verdicts (JUNK /
   PARK / PIN / TODO), the exact output format for each, and the rules —
   including the JUNK-vs-PARK tiebreak, deduping, and the SECURITY rule
   for tokens/session IDs in URLs. Follow it exactly; don't improvise a
   fifth verdict or a different ledger format.

3. **Triage interactively.** Apply the protocol to the snapshot. This is a
   conversation, not a silent batch job:
   - Present the verdict table to the user as you go (or in batches if the
     snapshot is large — tens of windows deserve a check-in, not a wall of
     text).
   - For any tab flagged `SECURITY` (URL contains what looks like a token,
     session ID, or password-reset link), do **not** write it anywhere —
     tell the user directly and let them handle it.
   - For any tab that's genuinely unknowable, ask the user rather than
     guessing a plausible-sounding source or reason.
   - Let the user override a verdict if they disagree — they know their
     tabs better than the model does.

4. **File the results.**
   - Append PARK lines to the user's ledger at `tabrot paths`' `parked=`
     location (tabrot seeds it from the template on first use). Append,
     don't overwrite — this is a ledger, not a scratch buffer.
   - Append PIN lines to the relevant project manifest(s) in the
     `manifests=` directory (e.g. `work.urls`, `personal.urls`), grouped
     as TRIAGE.md specifies. If a suggested project doesn't have a
     manifest yet, ask before creating one (`tabrot init <project>`
     creates it properly).
   - Surface TODOs as a plain checklist in the chat — don't silently file
     these into some other system unless the user has one and asks you to.

5. **Report back.** Finish by telling the user, explicitly and by window,
   which windows are now fully accounted for (every tab triaged, every
   PARK/PIN/TODO filed) and therefore **safe to close**. Be precise —
   "Window 2 is clear, close it" is the deliverable. Don't make them
   re-derive that from the verdict table.

## Install

Copy this directory into your Claude Code skills folder:

```bash
cp -r integrations/claude-code ~/.claude/skills/tabrot
```

Claude Code will pick it up on the next session. It triggers on phrasing
like "close my tabs," "tab cleanup," "I have too many tabs open," or
"tabrot," so you don't need to invoke it by exact name.

This skill assumes `tabrot` is installed (brew, deb, or `make install`) or
a checkout is reachable, and locates everything else — protocol, ledger,
manifests — via `tabrot paths`. It vendors nothing; it drives the real
tool.
