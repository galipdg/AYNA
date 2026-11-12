# #59 HTML run report v0

- Issue: https://github.com/galipdg/AYNA/issues/59
- Owner: omer · Branch: `omer/59-run-report` (from `main` at `3df2b81`)
- Started: 2026-11-10 · Last update: 2026-11-10

## Approach
Server only. `GET /api/runs/{runId}/report.html?lang=en|tr` renders the run on request from the graph and the screenshot files. Nothing is stored, so retention (#51) needs no change and the report is never stale.

- `runs/RunReport`: pure renderer (no Spring), one HTML string with inline CSS and the screenshots as `data:image/png;base64` URIs. A `<meta>` CSP (`default-src 'none'`) means the saved file cannot load anything, even by mistake.
- `RunService.reportInput`: one read transaction for the run, the test, application and version names and the screenshot paths, then the files are read.
- `RunController.runReport`: `text/html; charset=UTF-8`, `Content-Disposition: inline; filename="ayna-run-<runId>.html"`, `Cache-Control: no-store`, the same CSP as a header.

## Decisions (small, local to this task)
- 2026-11-10 — omer: language `?lang=tr|en`, default `en` (the server stays English, ADR client-ui-language); the client sends the user's language. Agent messages stay as sent.
- 2026-11-10 — "Generated for every run automatically" read as: every run, in any state (running, aborted, with missing results), has a report on request. SDD §3 already says "Reports are generated on request (#59)".
- 2026-11-10 — Keyword, property and operator labels copy the client's `stepsKeywords` / `stepsProperties` / `stepsOperators` wording (tr.ts, en.ts), so the report reads like the step editor.
- 2026-11-10 — `Content-Disposition: inline` with a filename: a browser shows it, the client (#68) saves it under that name.
- 2026-11-10 — `Cache-Control: no-store`: a running run's report changes, and it holds screenshots of the AUT.
- 2026-11-10 — Times are shown in the server's time zone with the offset written out; no script, so the browser cannot localise them. 2026-11-12: Compose sets `TZ` (hasan's review); the image has tzdata.
- 2026-11-12 — Streaming (hasan's review): before, a Turkish 50-step report peaked near 90 MB (all PNGs, a UTF-16 builder after the first `ı`, its copy, the bytes). The run is read before the response starts, so a 404 stays a problem body; MockMvc tests follow the async dispatch.
- 2026-11-12 — `repairProposed` counts as a failure for the "first failed step" link.

## Status
- [x] Branch, #59 In progress on the board
- [x] Renderer + unit test (`RunReportTest`, 8)
- [x] Endpoint + integration tests (`RunReportIntegrationTest`, 7): every step with its screenshot, running/aborted/failed runs, a vanished file, `lang`, 404; NFR-09 50 steps × 222 KB in 216 ms (15 MB file)
- [x] OpenAPI regenerated (`runReport`, `lang` enum en/tr), SDD §2 server row, §3 files, §4.1 reports row
- [x] Server 149/149 before the last rename + CSS tweak; the report and OpenAPI tests rerun after it (17/17)
- [x] PR #229; hasan approved 2026-11-12 with three points, all done on 2026-11-12: the report streams (`StreamingResponseBody`, one step's text and one PNG in memory, base64 encoded through to the stream; NFR-09 now 148 ms), `repairProposed` has words, colour and a count, and Compose sets `TZ` (default `Europe/Istanbul`, also in `.env.example`). Server 151/151.
- Next step: push the fixes on omer's OK, merge this branch into `omer/68-run-history`.

## Manual checks
- 2026-11-10 · agent · sample EN/TR reports with real PNGs (written by a throwaway test, not committed) opened in the built-in browser over a local `http.server` (the pane does not script `file://`): 3 of 3 images decoded, no console errors (no CSP violation), layout checked at ~800 px; badges then kept on one line · evidence: session screenshots.
- pending · omer · open a report file with the network off (Wi-Fi off), by double-click from Finder · evidence: TBD

## Open issues
- hasan (#229 review): FR-35's failure `category` has no place in `StepResultResponse` or this report; it should go into the REST read model before #224 freezes (a tag before the message). Not in #59's scope; raise with #224 / #63.
- hasan offers a small issue for the CLI runner saving this report (`--report <path>`, after the last screenshot upload, never changing the exit code); waiting for omer's word.
- The real per-step screenshots come with #54 (hasan) and their upload with #44's client half / #61; until then reports of real runs show "no screenshot".
- The client button that opens or saves the report is #68.

## Handoff

## Outcome (fill when the issue closes)
