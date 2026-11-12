# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-12 (#33 sample app built, verified and in review)
- Current issue: **#33 is built and in review** (PR #230, `Closes #33`). Nothing else in
  progress.
- **My open PRs, in merge order:**
  1. **#170** (`hasan/161-winforms-walk`, `Closes #161`) — 5/5 CI green, both approvals,
     `MERGEABLE`. Waiting only on the merge click.
  2. **#200** (`hasan/26-minimal-playback`, `Closes #26`) — CI 5/5 green. Two of its commits
     are in galip's `rpc.py` and `docs/agent-rpc.md` on purpose, each on its own, so he can
     take, move or redirect them.
  3. **#201** (`hasan/dpi-awareness-v2`) — the two coordinate bugs from the Windows session.
  4. **#230** (`hasan/33-sample-app`, `Closes #33`) — new today. Four commits: the app, its
     tests, `eval/AGENTS.md`, memory.
- **#33: two of three criteria are measured, the third is not mine to tick.** 44 interactive
  controls over five screens, 0 without an AutomationId, `pytest eval` 125 green in 39 s,
  ruff clean — all on Windows. Criterion 3 says *every member's machine*, so **galip and
  omer have to run `python eval/apps/sample/app.py` once on macOS**; the exact commands and
  the expected output are in PR #230's body. Nothing in the app is Windows-only.
- **Two things in PR #230 that are not mine to decide:**
  - For galip: `texts.py` and `uia_check.py --json` are what `eval/nl/objects/sample.json`
    (#36) should be generated from, instead of hand-written ids.
  - Measured and recorded: **UI Automation cannot choose an item in a Qt combo box**
    (`SelectionItem.Select`, `Invoke`, `ValuePattern.SetValue` all leave it unchanged; items
    appear only after `ExpandCollapse`). SC-20 needs it, so it is an open question for
    playback (#40).
- **Review queue: empty** as of 2026-11-07; check `gh pr list --search "review-requested:@me"`
  at the next session start, because omer and galip have been merging since.
- Two gotchas this session added to `learnings.md`, both costly: a Qt environment variable
  set in a pytest process poisons every app the run starts afterwards (12:40 of timeouts),
  and the #199 one-module-name-per-tree trap bit again — that rule now lives in
  `eval/AGENTS.md` as well.
- `.codex/` sits untracked in my working tree (another CLI's hooks, my user's). Deliberately
  not committed and not ignored.
