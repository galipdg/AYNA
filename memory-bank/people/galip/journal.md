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
