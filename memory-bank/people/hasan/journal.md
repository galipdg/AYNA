# Journal — Hasan Berk Yanıkkaya (`hasan`)

Append-only. One entry per session, newest at the bottom:
`## YYYY-MM-DD · #<issue>` then 2–5 bullets: what changed, decisions, next step.

## 2026-10-25 — #9 one-screen PySide6 trial app
- Picked #9 over #8/#10: no dependencies, finishable alone, and it unblocks
  #21 → #33 → #46/#47 → the RQ measurements. #8 and #10 both need all three members.
- Scaffolded the first Python module in the repo: `.venv` plus a local
  `eval/apps/trial/requirements.txt` (user's choice; a repo-wide `pyproject.toml`
  stays open as a devops/ADR question).
- Built `app.py`, `uia_dump.py`, 12 tests and a README. All three acceptance
  criteria verified on this Windows machine; 12/12 tests pass.
- Four non-obvious findings cost most of the session and are now in `learnings.md`:
  the venv launcher owning a child process (which made `pywinauto.Application.start()`
  hang), the dotted AutomationId, `accessibleName` replacing the UIA Name, and the
  window frame's id-less buttons. Told galip via his inbox; commented on #9.
- Commits 5e23d15, 350071c; PR #116.
- Next step: review and merge PR #116, then confirm with omer that it covers #2.

## 2026-10-29 — review queue (#135, #138, #141–#146, #150, #151, #157)
- Cleared the whole queue: 11 PRs reviewed, 6 approved (#141, #142, #144, #145, #146, #151),
  5 left as comments with concrete asks (#135, #138, #143, #150, #157). Nothing waits on me.
- Reviewed by measuring, not by reading: a Qt `QTableWidget`/`QListWidget` probe answered all
  four of galip's #150 questions and found two schema defects (ValuePattern-first reads `''` on
  every Qt cell; `cell` is unsatisfiable on a list); the #141 scorer run showed a wrong Win32
  button scoring 0.800 and the score not being comparable across targets, so #73's threshold
  cannot be a constant; `eval/nl/objects/trial.json` verified live against the running trial app,
  which galip had marked unverified.
- Tested finding 7's own hypothesis and it failed: on KeePass 2, plain property reads cost
  2.79 ms/element and the ten pattern probes 1.56 ms, so the WinForms COM bridge is not the
  cause of the 278.5 s walk — it is tied to that window state. Corrected the finding in
  `eval/spikes/uia-dump.md` (PR #159 is still open) and posted the correction on #143 and #138,
  since I had overstated it in both reviews.
- Signed off NFR-02 (sample-app-scoped only), NFR-04, NFR-05, TBD-5 (plus a third "search ran out
  of budget" state), TBD-6 and RQ2; refused RQ1's definition as vacuous and proposed a two-number
  replacement. Committed the CLI runner's exit codes (0/1/2) and the camelCase contract rule.
- Next step: open the two issues promised in the reviews (the KeePass 2 hot spot; Ollama on
  Windows — every LLM number is from an M2 and the service's 30 s deadline already fires there),
  then #122.
- Followed through on both promises: opened **#161** (root-cause the 278.5 s WinForms walk, Week 2,
  blocks #12's snapshot budget) and **#162** (measure local-model latency on Windows, Week 3 —
  every number we have is from an M2 and the service's 30 s deadline already fires there), linked
  from the PRs where I promised them. Pushed `47d1e8b` to `hasan/6-uia-dumps` (PR #159).
