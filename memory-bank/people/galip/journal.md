# Journal — Galip Enes Doğan (`galip`)

Append-only. One entry per session, newest at the bottom:
`## YYYY-MM-DD · #<issue>` then 2–5 bullets: what changed, decisions, next step.

## 2026-10-25 · #7
- Installed Ollama 0.40.11 (Homebrew); pulled `qwen3:8b` and `gemma4:e4b-it-qat` (disk-limited choice, see task note).
- Added `ai/spikes/llm_smoke.py` (stdlib, loopback only), the inputs, a spike schema and `llm-smoke.md`. Schema-valid: qwen3 10/10, gemma4 9/10; 15–18 tok/s; 3–4.5 GB.
- Found a gemma4 runaway inside a free JSON string, which is input for #37. Drafted the GPU request.
- Next: offline repeat (manual check), then PR.

## 2026-10-25 · #6
- Pulled main (#113, #114, #115 merged; #7 closed). Started #6 on `galip/6-uia-tree-dump`.
- Added `eval/spikes/uia_dump.py` (`dump` on Windows via pywinauto uia, `stats` anywhere), `uia-targets.json` (KeePass 2, HandBrake, KeePassXC, Notepad++), 23 unittest tests and the note `uia-dump.md` with expectations written before the run.
- Checked the pywinauto 0.6.9 source: `Desktop.windows()` needs `visible_only=True`; wrapper properties hide COM errors, so the reader uses raw `Current*` properties. Pinned 0.6.9 (1.0.0b1 exists).
- Removed omer's protect-`main` item from my inbox (Galip's call); wrote the Windows-session request into hasan's inbox. GPU request on hold until the support programs reply.
- Merged origin/main (#3 CI, #9 trial app). Took hasan's #9 finding: TitleBar controls are left out of the interactive share. Split #6 into PR #119 (tooling, `Refs #6`, ready) and a later dumps PR that closes #6; label `needs-windows-test` added.
- Galip handed the rest of #6 to hasan: he runs the check, his agent fixes the script if needed, writes the results and closes #6 with his own PR.
- Next: review + merge #119.

## 2026-10-27 · inbox + #10 + reviews
- Pulled main (52 commits: #3 CI, #4/#5/#14/#18/#128 by omer, #8/#9 by hasan, my #119). Read inbox and the open PRs #126, #127, #130.
- Approved PR #127 (#32 client server settings) with two non-blocking notes: `AppPicker.choose()` has no catch; IPC handlers do not check the sender.
- #7: ticked its first three criteria, commented, and moved the unsent GPU request to the new issue #131 (Week 2, on hold).
- Filled the Commands sections of `ai/AGENTS.md` and `agent/AGENTS.md` (ruff + pytest run in fresh venvs on macOS, Python 3.15).
- #10: wrote the Similo, WATER and Vista entries on `galip/10-literature-galip` (from omer's branch). WATER's full text was not reachable (ACM 403); used the authors' slides plus Vista and Similo.
- Found that `merge=union` brings deleted inbox lines back when another branch appends; kept handled items until #126 and #130 merge.
- Next: #13 step schema v0 after the user's OK.

## 2026-10-27 · #13
- Started #13 on `galip/13-step-schema`; board In progress. Galip chose: version at the document root, `timeoutMs` (camelCase), `jsonschema~=4.26` in `ai/`, Wait = until the target is ready.
- Added `schemas/step.schema.json` (2020-12, `if`/`then` per keyword), `schemas/examples/step/` (14-step test, 7 valid + 29 invalid named cases) and `ai/tests/test_step_schema.py` (44 pass; dropping three rules made 7 fail).
- Wrote the Proposed ADR `2026-10-27-step-schema-v0`, the schemas README section and review notes in omer's and hasan's inboxes (graph needs `timeoutMs`; `checkpoint` cannot be a Neo4j map).
- Opened PR #134 (reviewers omer, hasan). Next: collect both approvals.

## 2026-10-27 · #16
- Pulled main (nothing new). #13 is in review (PR #134); Week 2 left #16 as the only code issue. Galip chose to start it although it depends on #12, because only `snapshot` needs #12.
- Added `agent/ayna_agent/rpc.py`: JSON-RPC 2.0 over WebSocket on 127.0.0.1 (`websockets~=17.3`, approved), `Authorization: Bearer` token checked in the handshake, token from `AYNA_AGENT_TOKEN`, `--port 0` + stdout ready line, `Desktop` protocol for the UIA backend (all calls on one worker thread).
- 50 tests with a fake desktop over a real WebSocket, Python 3.11 and 3.15; manual CLI run matched `docs/agent-rpc.md`. ADR `2026-10-27-agent-rpc-v0` (Proposed). Requests in hasan's (backend) and omer's (client) inboxes.
- Next: open the PR; wire hasan's backend in when #12 lands.
- 2026-10-27 merge: took main (#127, #130, #133) into the branch; resolved `active.md` by hand.

## 2026-10-27 · orchestrator session (#19, #20, #27, #34, #35, #36, #37, #49, #50, #71)
- Pulled main (#136). Inbox had nothing new to act on. Picked galip's Nov–Dec issues that do not wait on a teammate's unfinished work. Ran up to three subagents in parallel, each in its own worktree with its own PR.
- PRs opened: #138 (#19 pre-read), #137 (#27 RS outline), #139 (#20 lit. §2, into omer's branch), #140 (#34: 36 SC, 40 FR, 36 NFR), #143 (#35 RS draft), #142 (#37 generator: 10/10 valid on both models), #141 (#49 scorer: Similo weights, exact fractions), #145 (#36 guideline + checker + 12 trial pairs), #144 (#50 `docs/sdd/SDD-ai.md`), #146 (#71 stdlib service, per-step drop list, `none.noMatch`, 30 s timeout).
- Orchestrator fixes:
  - #49: a missing property is skipped only when the target lacks it, and automationId compares the Qt leaf only.
  - #71: aligned with RS FR-26/SC-27, so invalid steps are dropped one by one and an answer with no valid step gets 422 `no_valid_steps`.
  - #139: retrieval refs changed from #57 to #58.
- Blocked on teammates: #42, #43, #57, #58, #72, #76 and the 40 pairs of #36.
- Next: the advisor's answers for #19, reviews, the #71 offline manual check.

## 2026-10-28 · #147, #149 (orchestrator, continued)
- galip allowed GitHub writes: commented on #21 and #80 (ADRs go to `memory-bank/decisions/`). Opened #147 (schema v0.2 rows), #148 (server load test, proposed for omer) and #149 (healing proposal transport); all three are Todo on the board.
- Health check: local repo clean, 12 PRs green and mergeable. Omer's #126 conflicts with main in `people/omer/active.md` only.
- Subagents opened PR #150 (#147: `SelectRow`, row by index or key-cell value, `cell`/`rowExists`/`rowCount` checks, v0.2 keeps every 0.1 step valid, #37 derivation needs no change) and PR #151 (#149: one `run.stepResult` payload for client and CLI, first-write-wins per (runId, stepIndex), exact fractions as strings). Both ADRs are Proposed.
- Next: reviews; the follow-ups listed in active.md once the ADRs are approved.

## 2026-10-29 · review round (no issue started)
- Pulled main (nothing new locally; #134–#146, #151 merged today). Inbox: hasan asked to flip the step schema v0 ADR; done on #150 (`a759985`, pushed).
- Approved #160 (OpenAPI + problem details), #159 (UIA dumps, pilots KeePass 2 + HandBrake), #155 (SDD §1–4), #157 (SDD §6). Approved as decider: the problem-details ADR and the graph schema v0.1 ADR (#156).
- Cross-PR finding raised on #155/#160: the server cannot pass AI 4xx bodies through unchanged under the problem-details ADR (`status` is a string there); proposed mapping with `code` + extension members.
- galip decided retrieval: the server picks the candidate objects, AI service gets no Bolt edge (#58 to update).
- Collected the review follow-ups left on merged PRs into `active.md`. PR-body edits (DoD ticks) are blocked by auto mode.
- Next: RS follow-ups from the #143 reviews (FR-30 first), then the `ai/API.md` / scorer items.

## 2026-10-30 · #71, #49 review follow-ups
- PR #165 (`galip/71-ai-api-followups`): `AYNA_AI_TOKEN` bearer token, required with `--allow-remote`, checked before routing (12 new tests, 355 ai tests pass); `app`/`version`/`screen` documented as the server sends them; retrieval decision recorded in `ai/API.md`, README, `retrieve.py`, SDD-ai. omer told via inbox (contract change).
- PR #166 (`galip/49-dpi-location`): per-element `dpi`, location and area in DIP, exact arithmetic kept; `parentPath` contract; U+0307 note corrected (hasan's `ż` example keeps its dot under NFC). 129 agent tests pass.
- Next: reviews on #164–#166; #58 issue text; remaining small asks in `active.md`.
## 2026-10-29 · #35 review follow-ups
- Folded omer's and hasan's #143 reviews into RS 0.6 on `galip/35-rs-review-followups`: FR-30/FR-23 follow the healing-transport ADR, TBD-5/6/9/10 closed, FR-35 "search incomplete", NFR-45 and NFR-46 added. SDD-ai AI-5.1/AI-6.1 aligned.
- Consistency check rerun (scratch script): 0 errors; 40 FR, 46 NFR, 16 UC, 36 SC.
- Next: PR review by omer and hasan; tick #35 criterion 2 after merge.

## 2026-10-31 · review round (orchestrator; no new issue)
- Pulled main (#159, #164, #165, plus teammates' merges). Found the main checkout on another session's branch and iCloud " 2" duplicates; a parallel session ("Proje kuralları ve inbox görevleri") is doing #166 in the main checkout, so my agents worked only in their own worktrees.
- #150: merged main (GitHub flagged union-driver memory files; no real conflict), 466 ai tests pass. Fixed two ADR notes from the #170 findings.
- New PRs from subagents: #173 (#71 loopback by resolved address, `stepLimitReached`), #174 (#149 healing-proposal schema 0.2, ADR Proposed), #176 (#36 quoting and check-box rules).
- Ticked the "ADR added" DoD box in the bodies of #141, #142, #145, #146 (hasan's ask).
- Drafted reviews for #167, #169, #170, #172; posting and the #58 body edit were blocked by auto mode, so galip posts them by hand.
- Next: post the reviews; push the #166 fix from the main checkout; hasan's re-review of #150.

## 2026-10-31 · review replies (main-checkout session)
- #164, #165, #159 merged. On #166 (omer, hasan): a `dpi` on one side only made an unchanged control off 100 % look moved; fixed by using the known `dpi` for both (`0da0c92`, 132 agent tests). The schema `dpi` change is in the orchestrator's #174, not duplicated.
- Opened #177 (RS 0.7, NFR-45 dead-letter clause from omer's #164 review).
- Coordinated with the orchestrator session over `SendMessage`: it took #150, #173, #174, #176, the four reviews and #58; this session took #166 and #177.
- Moved two identical " 2" duplicate files (iCloud Desktop) to the session scratchpad; two transient `.git` lock errors during fetch, gone on retry.

## 2026-11-02 · open PRs, conflicts and reviews (main-checkout session, with the orchestrator)
- Split the work over `SendMessage`: the orchestrator took #176 and the issue audit (#16 closed, #35/#36/#37/#71/#149 boxes); this session took #150, the RS, ADR statuses and the reviews.
- #150: `main` merged (`0f78c4c`), ai 510 and agent 276 tests pass, and hasan's review is re-requested. #181: RS 0.8 (documents table, NFR-32 public endpoints) plus the descriptor and snapshot ADRs flipped to Accepted after galip's decider approvals on #175 and #180.
- Reviews: #179 APPROVE (accounts ADR approved); #169 APPROVE with one label-precedence sentence to fix; #170 APPROVE.
- iCloud evicted files in `agent/.venv` and `.git`. Ran the agent tests from a scratchpad venv and recorded it in `learnings.md`.

## 2026-11-08 · review round for the client stack (main-checkout session)
- Reviews, all APPROVE: #154 (agent manager; real agent from `main` on macOS: connect, -32001, SIGKILL → restart, `stop()` by EOF in 11 ms; warned that a squash-merge gives the stack add/add conflicts whose "take ours" resolution drops `stop()`'s deadline), #210 (eval rename), #192 (step editor; 183 tests also pass with #150's 0.2 schema; in-flight save drops edits; 0.2 row steps open as "Kontrol eksik" until #205), #197 (undo; key-by-index id mismatch after a save, with a fix; `DEMO.md` status rows out of date: #26/#193/#182/#194/#170 merged).
- #150: `main` merged (clean locally), ADR v0.2 Accepted, hasan's two KeePass 2 corrections. Found: three server tests on `main` PUT `"version": "0.1"` (omer's files), so they fail once the schema is 0.2.
- `galip/71-request-log-race`: the `request` log line is written before the answer (omer's 11-05 inbox fix); 6/6 fail → 6/6 pass with a 50 ms delay injected after the write.

## 2026-11-15 · PR reviews and inbox (main-checkout session, no issue started)
- `main` pulled: 24 merges since 11-08 (contracts v1 #224, playback for #22/#26, run history/report, eval sample app versions, load test #152).
- Reviews, all APPROVE: #240 (failure category; ADR approved; Ambiguous is `elementNotFound` but never heals), #234 (pick hotkey, after hasan's fixes), #237 (playback v1; three `agent-rpc.md` mismatches I'll fix after merge), #239 (bug versions; bug3 stays on SC-20; SC-31's step should be Click `main.searchButton`), #235 (Windows latency; `reasons` opt-in and the 60 s default accepted; `warm_up` bug confirmed in my code). RQ1: container controls get a second, separately reported set (#29).
- `galip/inbox-2026-11-15` (local): `rpcVersion` 1.0 with an agent-side schema test, `errors.py`, `agent-rpc.md` versions, three ADRs Accepted, RS 0.9 (TBD-2, NFR-07/08), SDD §5 refresh. The inbox is handled but not cleared, because `merge=union` would bring the entries back while four open PRs touch it. Agent tests: 436 passed from a scratchpad venv. The iCloud-evicted venv still hangs.
- Next: push and open a PR on galip's OK; then the `ai/` follow-ups from #235 and the RS final (#41, due 23 Nov).
