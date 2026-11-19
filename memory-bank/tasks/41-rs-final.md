# #41 RS final and submission (23 Nov)

- Issue: https://github.com/galipdg/AYNA/issues/41
- Owner: galip · Branch: `galip/41-rs-final`
- Started: 2026-11-19 · Last update: 2026-11-19

## Approach
RS 0.9 → 1.0 in `docs/rs/RS.md` and `docs/rs/scenarios.md`: fold in what merged since 0.9 and the RS points promised in the 2026-11-15 reviews. Each TBD is now closed or deferred with a reason. The PDF is built by `docs/rs/build_pdf.py`: Markdown → one HTML page → headless Chrome, with `scenarios.md` included as Appendix C. The PDF is committed as `docs/rs/RS-1.0.pdf`, as the criterion asks.

## Decisions (small, local to this task)
- 2026-11-19 — **FR-35 matches playback (#63, `agent/ayna_agent/playback/triage.py`)**:
  - an ambiguous match is "element not found";
  - a refused step and a rejected action carry no category; the decision log keeps a finer reason;
  - "unexpected window" is defined (the step's own window is not in front while another window of the app is) and takes precedence over element not found.
  - Nothing in playback produces `unexpectedWindow` yet: `runSteps` plays against one window handle, and a closed window ends the call with -32001. That is #40/#63 follow-up work (hasan).
- 2026-11-19 — **FR-29 never heals after an ambiguous match or outside the step's own window.** So SC-31 cannot run on the "wrong navigation" bug5. Logging in opens Ayarlar, so the main window is not in front: the step fails as unexpected window, and there are no same-window candidates to reject.
  - SC-31 now says "the list screen has lost its search button", which is a real bug with same-screen candidates. The title is kept, because `test_bugs.py` looks it up.
  - Asked hasan (inbox) to rebuild bug5 that way. The wrong-navigation case is SC-22's kind.
- 2026-11-19 — The PDF build needs `markdown` (pip) and Chrome, not pandoc or LaTeX: nothing on this Mac had them. The script lives in `docs/rs/`, mine, and is not product code.
- 2026-11-19 — Relative links in the PDF point to GitHub `main`; the repository was public when checked on 2026-11-19 (`gh repo view`). If it goes private, those links 404 for a reader outside the team. The links to `scenarios.md` point into Appendix C.

## Status
- [x] RS 1.0 text: header and history; FR-11, FR-15 and FR-18 (schema 0.2); FR-29 and FR-35; NFR-02 (#161 root cause); NFR-12 (#162); pilots named (TBD-1); §1.3 state; §2.2; §3.5 contracts; E.1 rows closed or deferred
- [x] scenarios.md: C.2 statuses and pilots, SC-07 (KeePass 2 / Notepad++), SC-20 (bug3 line), SC-31 (missing control + note), logical names are the app's
- [x] Consistency check (scratch script, §5.3): 40 FR (35 Must), 46 NFR, 36 SC, 16 UC, 11 TBD, **0 errors**. Scenario names checked against `eval/nl/objects/sample.json`: only `settings.notificationsTab` is missing, and #36 lists it
- [x] `hasan`'s `eval/apps/sample/tests/test_bugs.py`: 25 passed against the edited scenarios (macOS, offscreen)
- [x] PDF built, 38 pages. Pages 1, 14 and 35 checked as images: Turkish glyphs, tables, repeated table headers, Appendix C lists, page footer
- [ ] PR (`Closes #41` only after submission; until then `Refs #41`), reviews from omer and hasan
- [ ] galip submits the PDF to the course by 23 Nov and ticks "Submitted"
- Next step: after the PR merges, galip submits `docs/rs/RS-1.0.pdf` and comments the date and channel on #41; then close #41.

## Manual checks
- 2026-11-19 · galip's agent · PDF pages 1, 14 and 35 rendered and inspected · pass · scratch renders only (not committed)

## Open issues
- `unexpectedWindow` is in the contract and the RS but never produced: multi-window playback (SC-20's dialog, SC-22, the new SC-31 path) needs the agent to follow the step's own window. hasan's area (#40/#63); noted in his inbox.
- TBD-3, TBD-4, TBD-7, TBD-8 and TBD-11 are deferred, not closed. TBD-4 and the whole of E.2 wait on the advisor meeting (#19), which has not happened.
- The plan document (Claude Docs) still names Hasan as RS lead (TBD-8).

## Handoff
- Rebuild: `python -m pip install markdown==3.11.3 && python docs/rs/build_pdf.py`, which writes `docs/rs/RS-<version>.pdf` from the Version row.
- Re-run the consistency check with an equivalent script. The scratch one parsed FR, NFR and TBD rows, UC and SC headings, FR → SC and the Given/When/Then of each SC.

## Outcome (fill when the issue closes)
