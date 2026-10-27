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
