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
- Next: push + issue comment + `needs-windows-test` (needs OK), then dumps at the Windows session.
