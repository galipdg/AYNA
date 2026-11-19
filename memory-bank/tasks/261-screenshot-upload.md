# #261 Client uploads step screenshots after a run and removes the agent's PNGs

- Issue: https://github.com/galipdg/AYNA/issues/261
- Owner: omer · Branch: `omer/261-screenshot-upload`
- Started: 2026-11-19 · Last update: 2026-11-19

## Approach
- `stepPlayer.ts` passes on the agent's `screenshotPath` (agent-rpc 1.2).
- `screenshots.ts` (`screenshotKeeper`): right after each step the runner copies the PNG to `userData/run-screenshots/<runId>/step-NNNN.png` and deletes the agent's file; at the run's end it removes the agent's `ayna-screenshots/run-*` folder(s). Only folders shaped `…/ayna-screenshots/run-…` are ever removed (the path comes from another process).
- Outbox entry `screenshot` queued right after its result; `putScreenshot` (`runs.ts`) PUTs the bytes. The sender's `released` hook deletes the copy when the entry leaves the queue (delivered, refused, set aside) and the run's own folder when its `finish` does.

## Decisions (small, local to this task)
- 2026-11-19 — Copy at once, not upload from the agent's path: the client plays one `runSteps` call per step and the agent names the image by its index *within the call*, so every step writes the same `run-<runId>/step-0000.png`; a slow or away server would get the wrong image. Told hasan (inbox).
- 2026-11-19 — A refused image (400/409/413/415, or file gone) drops only that image; the run and its results go on. 404 still sets the whole run aside.
- 2026-11-19 — Set-aside screenshots lose their file (entry kept as a trace): the criterion asks for no PNG left behind.

## Status
- [x] Code + tests: 328 client tests, lint, typecheck (macOS)
- [ ] PR (`Closes #261` after the Windows check; real agent writes the PNGs only on Windows)
- Next step: Windows check below at the weekly session; until then the PR is "Part of #261".

## Manual checks
- Pending (Windows session): real agent + trial app.
  **Setup:** Hasan's machine; `git switch omer/261-screenshot-upload`; server running; trial app open; in `client/`: `npm ci && npm run dev`; log in; the trial app's version; a 3+ step login test.
  1. Run the test. *Expected:* passes; during the run `%TEMP%\ayna-screenshots\run-<runId>` holds at most one PNG; after the run it is gone.
  2. Open Run details. *Expected:* each step shows its own image (step 1 ≠ step 3).
  3. `%APPDATA%\ayna-client\run-screenshots` (the client's data folder). *Expected:* no folder for the run once the report shows the images.
  4. Stop the server, run, start the server again. *Expected:* after the outbox delivers, the report shows every step's image and the data folder is empty.
  **Report back:** pass/fail per step; for a failure the `[outbox]`/`[screenshots]` console lines and a screenshot.

## Open issues
- `dev/mock` agent sends no `screenshotPath`, so `npm run demo` cannot show this on macOS.
- Agent: a per-step `runSteps` call always writes `step-0000.png` (hasan's side; the client works around it).

## Handoff

## Outcome (fill when the issue closes)
