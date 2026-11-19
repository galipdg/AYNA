# Active — Galip Enes Doğan (`galip`)

Only galip's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-19 (main-checkout session: reviews, RS final, inbox round, #36 pairs).
- **Open PRs of mine, each waiting on reviews. galip merges them, in this order:**
  1. **#267 RS 1.0 + PDF (#41, due 23 Nov).** After merge, **galip submits `docs/rs/RS-1.0.pdf` to the course** and comments the date and channel on #41, then closes it. Reviewers: omer and hasan. Rebuild with `python docs/rs/build_pdf.py` (needs `markdown` and Chrome) if the text changes.
  2. **#269 inbox round:** `runId` pass-through, `rpcVersion` 1.2, `agent-rpc.md` rows, screenshot ADR Accepted, inbox cleared.
  3. **#259 → #260 (hasan) → #270 (mine, #36):** after #260 merges, retarget #270 to `main` and add `Closes #36`. hasan's §7.6 playback of my 8 scenarios is pending (Windows).
- **Inbox:** every entry is handled. The five kept on `main` are merge anchors for #259 and #260 (`learnings.md` 2026-11-15; checked with `git merge-tree`). After those two merge, delete all but the two that are still galip's to act on:
  - **CI billing:** Actions refuses every job because the repository is private again (omer, #262). Only the owner can fix it: make the repo public, or Settings → Billing → raise the Actions spending limit or fix the failed payment.
  - **Copilot review (#256):** remove the Copilot rule from Settings → Rules → Rulesets → `protect-main`, and turn off Settings → Copilot → Code review if it is on. Keep the one-approval rule.
- **Asked of others, not mine to do:**
  - **hasan:**
    - rebuild `bug5` as "list screen without its search button" (SC-31 in RS 1.0);
    - multi-window playback and `unexpectedWindow`;
    - approve the `failure-category` ADR (asked on #240) and the `healing-proposal-schema-0-2` ADR (#174);
    - the 7 `test_playback_rows.py` tests that need `comtypes` on macOS;
    - review my generator commit `2f2ec67` in #270.
  - **omer:** finish #126 (it closes #10 and #20; section 2 is done), and take `main`'s side of my inbox when he merges.
- **Next issues:**
  - **#37** criterion 1: run `ai/ayna_ai/generate.py` on the 40 sample pairs with qwen3:8b and gemma4 once #270 merges. Ollama is installed (`/opt/homebrew/bin/ollama`) but its server was not running. Decide hasan's `max_text` cap first (#71 task note).
  - **#147:** criterion 3 is met by #270 (guideline) and #40 (playback). Still to come: #37's prompt lines and derived schema for rows (do not narrow `column` to an enum, omer #221), and omer's confirmation for the step editor (#38), asked on #270.
  - **Week 6 (24–30 Nov):** #43 (`heal/features.py`), #42 (`heal/candidates.py`), #226 (the `rpc.py` half waits on hasan's `SnapshotTimeout` fields).
  - **#149:** AC2 waits on #74 (omer).
  - **`ai/` (#71/#78):**
    - an optional `reasons` request field;
    - a 60 s default timeout (RS NFR-12 now says 60 s);
    - `warm_up` must send the same `options` as `request_body`;
    - label latencies as Apple silicon or Windows in `ai/README.md` and `ai/API.md`;
    - fix `ai/spikes/llm-smoke.md`'s reproducibility claim.
- **Human-only, overdue:**
  - #19 (advisor workshop; RS Appendix E.2 waits on it);
  - #131 (GPU request; draft in `ai/spikes/gpu-request-draft.md`, on hold for support programmes);
  - #28 (G0 gate, team).
- Local tools on this Mac:
  - The venvs under `~/Desktop` hang (iCloud).
  - Scratch venvs on Python 3.12 work, since `python3` is 3.15 and has no PySide6 wheels: `python3.12 -m venv <scratch>/venv-agent`, then pip the pins from `agent/pyproject.toml`, then `cd agent && PYTHONPATH=. pytest -m "not windows"`. Result: 812 passed, plus 7 `comtypes` failures, also on `main`.
  - For `eval` and `ai/tests/test_nl_dataset.py`: `jsonschema pytest PySide6-Essentials`, run with `QT_QPA_PLATFORM=offscreen`.
  - Client: Node ≥ 22.12 at `/opt/homebrew/opt/node@22/bin`.
  - Server: needs Java 21 and Docker; this Mac has Java 17.
