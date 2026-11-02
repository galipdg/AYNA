# Active — Galip Enes Doğan (`galip`)

Only galip's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-03 (main-checkout session, with the orchestrator session's results of 11-02; no new issue started)
- Current issue: none in progress. Open PRs of mine:
  - **#150** `Refs #147` step schema v0.2 rows. omer approved. `main` merged in again on 11-02 (`0f78c4c`; conflicts were appends in `schemas/README.md`, `decisions/README.md`, plus `stepLimitReached` + `0.2` in `ai/API.md` and its test). Re-requested hasan's review with a comment. His only open point is the cell text rule: non-empty-Value-first, because a WinForms cell's Name is header + row index. When he approves, flip the v0.2 ADR to Accepted in the PR.
  - **#176** `Refs #36`: **merged 2026-11-02** (`dc02da1`, squash; the orchestrator merged it on galip's one-time OK). #36 stays open for the 40 pairs (#33). Not done, in its task note: the dataset test in the eval CI job (`eval/pyproject.toml` testpaths, hasan) and `splitlines()` mis-splitting U+2028.
  - **#181** RS 0.8 (§2.2 documents up to date; REST API v0 from omer's #31 note; NFR-32 names login, health and the OpenAPI docs as public, omer's #60 note) and the descriptor and snapshot ADRs flipped to Accepted. Reviews requested from omer and hasan.
- Merged since 10-31: #164, #165, #166, #173, #174, #177 (mine); #159, #160, #155, #157, #167, #172, #175, #180 (teammates).
- Decider approvals given 11-02: ADR element descriptor v0 (comment on #175) and ADR snapshot schema v0 (comment on #180; also answered hasan's `rpc.py` questions: keep the `__main__` delegation, and keep `setup()` recording the reason). ADR healing proposal 0.2 (#174) **waits for hasan's approval** (asked on #174); flip it when he gives it.
- Reviews posted 11-02:
  - #179 APPROVE, with the accounts ADR approved as decider. Notes: a 401 must not dead-letter the outbox (#44); the last-admin race; no login rate limit.
  - #169 APPROVE, with one sentence to fix before merge: "`LabeledBy` is confirmation, not primary" contradicts descriptor ADR §5. hasan's `active.md` conflicts with `main`.
  - #170 APPROVE: all three earlier points fixed; spike suite 56 OK on macOS. Merges after #169, needs one more `git merge origin/main`.
- Issues (orchestrator, 11-02):
  - #16 closed.
  - #35: both criteria ticked, with an evidence comment.
  - #149 open only for box 2: #74 must put `PUT /api/runs/{runId}/results/{stepIndex}` into the OpenAPI.
  - #37 and #36: boxes ticked; the 40 pairs wait on #33.
  - #71: open only for the offline manual check (galip, Wi-Fi off).
  - #20 waits on omer's #126 (still a draft); galip reviews it when it is ready.
  - #58's expected output was updated on 10-31.
- Now unblocked, not started (new work): **#43** (#11 merged in #175); **#42** once hasan's #46 lands.
- After those merge (galip):
  - RS: close TBD-1 with the pinned pilots (P1 HandBrake, P2 KeePass 2), SC-07 on KeePass 2, CON-02/Q7 and the trace row, NFR-02's cause from #161 (a modal box, not the window state). This is for after #169.
  - RQ4 validity threat: a Qt AutomationId is a dotted path, so an id-only baseline breaks on every container move in #46.
  - `FEATURE_VERSION` moves from `recognition/snapshot.py` to `heal/features.py` with #43.
- After #150 merges: `SelectRow` + row checks into RS FR-11/15/18; #37 prompt lines and the `column` enum when `columns` is non-empty; #36 grid labelling rules.
- #58 design (omer, #165): embedding stays off the repository's write path (FR-28). Objects are stored without a vector, embedded after commit and retried while missing; retrieval falls back to the current screen. omer writes it in #25.
- Still open from earlier: SDD AI-5.5 storage / AI-9 rows 7–8 (omer's #144 point 3); reasons opt-in (waits on #162); the 200-char string cap and quoted-literal check (#37's grammar); NL dataset §8 outsider consent/brief (galip's decision); #19 §7 after the advisor meeting; `pattern: "\S"` for both element and snapshot schemas in one 0.2 PR after #15/#24 (agreed on #180).
- Blocked on teammates: the 40 pairs of #36 and then #57 (#33), #58 (omer's #25 + #36), #72 (#71 + #57), #76 (#49 + #46). #131 GPU request is on hold.
- Inbox: handled but not yet deleted: omer #3, hasan #9, hasan #6, omer #7 (→ #131), hasan #16, omer #50/#45/#53, omer #143–#151 conflicts, omer #48, omer #31 (done in #181), hasan #11, hasan #12 ×2. Delete them only when no open PR touches `people/galip/inbox.md`: #169, #170 and #179 still do.
- Workspace: `~/Desktop` is iCloud-synced and evicts files ("dataless"). By 11-03: 592 files in `agent/.venv`, 509 in `ai/.venv`, 349 in `.git`. Some reachable **git objects are unreadable** (`mmap failed: Operation timed out`; `git rev-list --all` stops), and `brctl download` does not restore them. Checked 11-03: nothing is lost. Every local branch is an ancestor of its GitHub branch or exists on GitHub, and there are no stashes and no untracked work. **Fix: a fresh clone outside iCloud** (copy `CLAUDE.local.md`, rebuild the venvs; the Claude project memory folder is keyed to the old path). Until then, tests run from a venv outside `~/Desktop`. `client/node_modules` is absent: run `npm ci` before client work. The orchestrator's agents leave `.claude/worktrees/` untracked in the checkout.
- Open questions: project licence (TBD-7, before #41); plan-doc reference numbering (TBD-11); 30 s service timeout on a loaded laptop (#71, #162); qwen3:8b 3/12 vs gemma4 9/12 on the trial pairs (#36).
