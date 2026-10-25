# Weekly Windows test session for macOS developers

- Date: 2026-10-25
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan

## Context
The automation agent (pywinauto, UI Automation) only runs on Windows. Galip (recognition, healing, AI) and one other member use macOS; Hasan uses Windows. A Windows VM is planned but not set up yet.

## Decision
- Code is written during the week on any OS. Windows-only verification happens in one weekly in-person session on Hasan's Windows machine.
- Issues waiting for that session carry the label `needs-windows-test`, with the test commands and manual check posted as an issue comment.
- Results are posted as issue comments; failures are also appended to the owner's `inbox.md`.
- pywinauto stays behind a thin interface so most agent logic is unit-tested on macOS with fakes.

## Consequences
Windows feedback can lag up to a week, so Windows-dependent issues should be started early in their week and the weekly session must happen before each gate (G0 week 3, G2 week 9, G3 week 12). Revisit when the Windows VM is available.
