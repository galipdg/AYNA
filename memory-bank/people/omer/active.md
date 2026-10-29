# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29
- Current issues:
  - #32: merged (PR #127), closed; Windows run pending (`needs-windows-test`, check posted on #32)
  - #10 (literature, team): draft PR #126 (`Closes #10`, `Closes #20`) on `omer/10-literature-review`; galip's entries and section 2 are in, main merged in, gaps-table fixes applied in the file and the plan doc; waits for hasan's five entries and for the plan-copy question (comment on #126)
  - Reviews 2026-10-29: approved #134, #135, #141, #146, #150, #151 (server/client commitments listed below); comments with decisions on #140 (NFRs confirmed), #143 (TBD-9 → #152, TBD-10 → API tokens), #144 (SDD placement, retrieval via server). Content reviews of the RS PRs #137, #138, #140, #143 and the SDD part #144 are still open.
- Next step: content reviews of #137 → #140 → #138 → #143, then #144 (my sections listed in each PR body). Then start #17 (agent process manager; #135's contract), folding in the two #127 review notes (see `tasks/32-server-settings.md`).
- Commitments made in reviews (do them in these issues): #39 — `Step.checkpoint` and `Step.row` as JSON strings, `timeoutMs` integer, start at schema 0.2, validate steps with a 2020-12 validator (new dependency, ask); #25 — logical names unique per AppVersion with the schema's pattern, refuse `none.noMatch`, `columns` string list from snapshot headers; #74 — per-candidate data on `CANDIDATE`, keep the whole proposal JSON on the node, update `docs/graph-model.md`; #51 — 409 for a repeated result PUT with a different body, screenshot uploaded separately; #44 — outbox items carry their server URL; #78 — server read timeout 35 s, `app` = application id; #82 — do not publish the AI port 8090; #17 — agent exits on stdin EOF (asked of galip in #135), heartbeat via WebSocket ping frames, agent command configurable.
- Open questions: which plan copy is canonical (omer's Claude Doc vs galip's export; asked on #126); project licence undecided (`tasks/18-tool-matrix.md`); Leotta [4] PDF unread; `/api/health` unbounded while Neo4j shuts down (`tasks/32-server-settings.md`); duplicate-name race in #128 (`tasks/128-apps-api.md`)
- Waiting on: hasan (no activity since 2026-10-26) for #10 entries, #12 (blocks #15), #122 `eval/` part, reviews on galip's PRs; galip for the plan-copy answer and the stdin-EOF change in #135
- Network: SSH to github.com times out here; push/fetch over HTTPS with `gh auth git-credential` (see `learnings.md`)
