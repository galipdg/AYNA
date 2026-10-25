# Windows-bound work moves to Hasan

- Date: 2026-10-25
- Status: Accepted (refines [Weekly Windows test session](2026-10-25-weekly-windows-test-session.md))
- Deciders: Galip, Ömerfaruk, Hasan
- Issues: reassigned #6, #11, #12, #22, #23, #29, #64, #73 (galip → hasan); #13, #19, #27, #34, #35, #41, #76, #79, #87, #93, #97 (hasan → galip); #18, #48 (hasan → omer)

## Context
Galip and Ömerfaruk work on macOS; only Hasan has Windows. Writing UI Automation code on a Mac, handing it to Hasan through his inbox, waiting for the weekly session and looping back through PRs turned out slow. Of 90 open personal issues, 31 need Windows.

## Decision
- Agent work that touches UI Automation or pilot apps (recognition engine, Spy backend, RQ1 measurement, healing inside playback) is owned by Hasan, together with his existing playback, CLI and measurement issues.
- Client screens that only need a final look on Windows (Spy view, live run, healing approval, checkpoints) stay with Ömerfaruk and are checked at the weekly session; installer and air-gapped test (week 12) stay with him and use the planned Windows VM.
- Hasan's issues that do not need Windows move to Galip (RS chain, step schema, RQ4/H1 offline analysis, demo script, semester report) and Ömerfaruk (tool matrix, SDD test section). Bug-injected versions, JUnit XML, the testability guideline and eval tooling stay with Hasan because they belong to his work.
- Ownership: `agent/ayna_agent/recognition/` → hasan; `agent/ayna_agent/rpc.py`, `docs/rs/`, `docs/report/` → galip; `docs/sdd/` → omer.

## Consequences
Load after the move (open personal issues): Galip 31 (0 Windows), Ömerfaruk 32 (8 final checks on Windows), Hasan 27 (23 Windows). The HAVELSAN letter of intent names Galip as owner of the object recognition engine; the final report and presentation must describe the new split (Galip: AI assistant, self-healing scorer, RS; Hasan: recognition and playback engines). Revisit if the Windows VM makes macOS development of agent code practical.
