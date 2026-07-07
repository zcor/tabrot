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
   ./tabrot snapshot
   ```

   (If `tabrot` isn't on PATH or isn't in the current directory, ask the
   user where it's installed, or look for a `tabrot` script at the repo
   root of wherever they point you.) This reads the browser's session
   files directly off disk — nothing is sent anywhere by this step.

2. **Read the protocol.** Read `TRIAGE.md` from this tabrot checkout in
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
   - Append PARK lines to the user's `PARKED.md` (create it from
     `templates/PARKED.template.md` if it doesn't exist yet). Append,
     don't overwrite — this is a ledger, not a scratch buffer.
   - Append PIN lines to the relevant project manifest(s) under whatever
     directory the user keeps manifests in (e.g. `work.urls`,
     `personal.urls`), grouped as TRIAGE.md specifies. If a suggested
     project doesn't have a manifest yet, ask before creating one.
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

This skill assumes a working `tabrot` checkout is reachable (either on
PATH or at a path the user gives you) so it can run `tabrot snapshot` and
read `TRIAGE.md`. It does not vendor either — it drives the real repo.
