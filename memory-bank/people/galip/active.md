# Active — Galip Enes Doğan (`galip`)

Only galip's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-15 (main-checkout session: PR reviews and inbox; no issue started, at galip's request).
- Current issue: none in progress. **`galip/inbox-2026-11-15` is committed locally, not pushed.** It needs galip's OK to push, then a PR (`Refs #52 #185 #152 #53`) with omer's review requested on the agent, RS and SDD parts and hasan's on `errors.py`. What it contains:
  - agent: `RPC_VERSION = "1.0"`, `agent/tests/test_rpc_contract.py` (every Dispatcher reply checked against `schemas/agent-rpc.schema.json`), the four exceptions moved to `ayna_agent/errors.py` (re-exported from `rpc.py`), and the stale start-up comment fixed;
  - `docs/agent-rpc.md`: 1.0, the settled version numbers, nullable `listWindows` fields, and the `run.stepResult` field names;
  - ADRs runs-api, run-screenshots and contracts-v1-freeze set to Accepted;
  - RS 0.9 (TBD-2 closed, NFR-07/08 confirmed by #152), SDD §5 refreshed, inbox cleared, two notes in hasan's inbox.
- Reviews given 2026-11-15, all APPROVE: #240 (failure category, ADR approved), #234 (pick hotkey), #237 (playback v1), #239 (bug versions), #235 (Windows LLM latency). RQ1 container decision on #29: a second set, reported separately.
- Promised in those reviews, not done yet:
  - **`ai/`** (#71/#78): an optional `reasons` request field, default false; a 60 s default service timeout; `StepGenerator.warm_up` must send the same `options` as `request_body` (it warms the wrong offload today). After #235 merges: label latencies as Apple-silicon or Windows in `ai/README.md` and `ai/API.md`, linking `eval/llm-latency/report.md`. Correct `ai/spikes/llm-smoke.md`'s reproducibility claim, and plan #77 with repeated runs per sentence.
  - **After #240 merges:** set `2026-11-15-failure-category` to Accepted if omer has not, and add `category` to `runSteps`' result list in `docs/agent-rpc.md`. `ping` answers 1.1 only in hasan's #63 change that fills it.
  - **After #237 merges, in `docs/agent-rpc.md`:** add the `LegacyIAccessible.DoDefaultAction` rung to the `Select` row, fix the `handle` row (#40 did not make it optional), and fix the "still answers 0.1" line in "Not yet".
  - **RS final #41 (course deadline 23 Nov):**
    - FR-35: an ambiguous match is `elementNotFound`; a refused step or a rejected action carries no category.
    - FR-29: an ambiguous match never starts healing.
    - SC-20: one line naming the *wrong saved value* version (bug3).
    - SC-31 vs FR-35: bug5 opens Ayarlar as a separate window, so it may be *unexpected window*. Settle this with #63 and #73.
    - SelectRow and the row checks into FR-11, FR-15 and FR-18.
    - TBD-1, SC-07 and NFR-02.
  - **#36 guideline:** never pair `rowCount` (GridPattern) with `rowExists` (on screen) on a virtualised target.
  - **#147/#37:** prompt lines and derived schema for rows. List the object's `columns` in its description, and do not narrow to an enum (omer #221: columns can be incomplete).
- Open, no action yet: #226 (`-32002` `data: {blocked, reached}`, Week 6, mine); `docs/agent-rpc.md` "What the client does with a result" once #54 adds screenshots (omer 11-08); JUnit mapping of a `repairProposed` run is mine to settle (runs ADR, #66). Overdue: #19 (advisor workshop; Q4/Q5), #131 (GPU request), #20 (waits on #10 → PR #126). Week 6: #43 and #42, not started.
- Local tools on this Mac:
  - The venvs under `~/Desktop` hang on import because iCloud evicted their files.
  - I ran the agent tests from a scratchpad venv: `python3 -m venv <scratch>/venv-agent && <scratch>/venv-agent/bin/pip install -e "agent[dev]"`. Result: 436 passed, plus 1 known macOS-only failure in `test_uia.py`, reported to hasan.
  - The client needs Node ≥ 22.12 at `/opt/homebrew/opt/node@22/bin`.
  - Server tests need Java 21 and Docker; this machine has Java 17.
  - `git fetch` over HTTPS hung once. `git -c credential.helper= -c credential.helper='!gh auth git-credential' fetch origin` worked.
