# Active — Galip Enes Doğan (`galip`)

Only galip's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-31 (orchestrator session: review round of 10-31; main-checkout session: #166 fix pushed, #177 opened; no new issue started)
- Current issue: none in progress. Open PRs of mine:
  - **#150** `Refs #147` step schema v0.2 rows. omer approved. Waiting on hasan's re-review: the cell text rule is non-empty-Value-first, not his Name-first, because a WinForms `DataGridView` cell's Name is header + row index (MS docs). The reasons are in the 2026-10-29 PR comment. 2026-10-31: main merged in; ADR notes fixed (WinForms timing: normal is 9–12 ms/element and seconds only while a modal blocks, #170; the KeePass 2 check now targets Grid/Table on `m_lvEntries`, a SysListView32). When all three approve, flip the ADR to Accepted in the PR.
  - **#166** `Refs #49` scorer DPI. hasan approved. The one-sided `dpi` fix both asked for is pushed (`0da0c92`: one known `dpi` is used for both, neither known means 96) and answered on the PR. The schema point goes to #174; `dpi: int` = `GetDpiForWindow` of the top-level window is confirmed to omer. Waiting for omer's re-review.
  - **#173** `Refs #71` loopback by resolved address (the name `localhost` is no longer trusted); `stepLimitReached` flag at the 12-step cap. omer's inbox has the contract note.
  - **#174** `Refs #149` healing-proposal schema 0.2: optional `dpi` on `scoredElement`, optional `featureVersion` on scorer and target, plus #151 doc asks and SDD AI-5.2. New ADR `2026-10-31-healing-proposal-schema-0-2` is Proposed and needs three approvals.
  - **#176** `Refs #36` NL dataset: team-pair quoting (`bare-suffix`), check-box pairs (`start-state`, §6.8), and a style-enum sync test.
  - **#177** `Refs #35` RS 0.7: NFR-45 sets aside a result the server refuses as invalid (omer's #164 review). Review requested from omer. After it merges, tick #35's criterion 2.
- Reviews posted 2026-10-31 (galip's OK): #169 COMMENT (fix the #161 paragraph, the wrong refs — #22 is not version drift — name P1 = HandBrake / P2 = KeePass 2 for SC-07, exclude Qt item views from #33's unique-id test), #170 REQUEST_CHANGES (`kp_state.py --fresh` kills any KeePass and deletes `%USERPROFILE%\OneDrive\Belgeler\Database.kdbx`; the probe walks `PwEntryForm` twice; two numbers wrong), #167 APPROVE, #172 APPROVE. Re-review #169/#170 when hasan pushes fixes.
- After those merge (galip):
  - RS: close TBD-1 with pinned pilots; SC-07 on KeePass 2; CON-02/Q7/trace row; NFR-02 cause from #161.
  - `ai/tests/test_nl_dataset.py` docstring (eval now has a project).
  - RQ4 validity threat: Qt AutomationId is a dotted path, so an id-only baseline breaks on every container move in #46.
  - #42: "< 1 s per object" excludes snapshot capture (one snapshot per window).
- After #150 merges: `SelectRow` + row checks into RS FR-11/15/18; #37 prompt lines and `column` enum when `columns` is non-empty; #36 grid labelling rules (the grid sentence, the *seç* rule, the statusLabel note).
- #58's expected output updated on GitHub 2026-10-31 (server-side retrieval + `POST /ai/embed`, decision of 2026-10-29). omer's design point on #165: embedding must stay off the repository's write path (FR-28). Objects are stored without a vector, embedded after the commit, retried while the vector is missing, and fall back to the current screen; omer writes it in #25. SDD AI-4 already says "stale, refreshed later".
- Still open from earlier: REST API row → v0 once #160 merges; SDD AI-5.5 storage / AI-9 rows 7–8 (omer's #144 point 3); reasons opt-in (waits on #162); the 200-char string cap and quoted-literal check (change #37's grammar); NL dataset §8 outsider consent/brief (galip's decision); #19 §7 after the advisor meeting.
- Blocked on teammates: #42 and #43 (hasan's #11/#12), the 40 pairs of #36 and then #57 (#33), #58 (omer's #25 + #36), #72 (#71 + #57), #76 (#49 + #46). #131 GPU request is on hold.
- Inbox: handled but not yet deleted: omer #3, hasan #9, hasan #6, omer #7 (→ #131), hasan #16 (step schema v0 flip, done on #150). Delete them when no open PR touches `people/galip/inbox.md`.
- Workspace: `~/Desktop` is iCloud-synced (`CloudDocs/Desktop` → `~/Desktop`). It produced " 2" duplicate files and stale `.git` locks on 2026-10-31. Consider moving the repo out of `~/Desktop`.
- Open questions: project licence (TBD-7, before #41); plan-doc reference numbering (TBD-11); 30 s service timeout on a loaded laptop (#71, #162); qwen3:8b 3/12 vs gemma4 9/12 on the trial pairs (#36).
