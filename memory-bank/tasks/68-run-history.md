# #68 Run history view

- Issue: https://github.com/galipdg/AYNA/issues/68
- Owner: omer · Branch: `omer/68-run-history` (from `omer/59-run-report` at `bc52600`, stacked on PR #229)
- Started: 2026-11-10 · Last update: 2026-11-10

## Approach
- Server: `GET /api/apps/{appId}/runs?testId=&status=`, newest 100 of the application (`RunService.listAppRuns`). The per-test list (20, `/api/tests/{id}/runs`) stays for #44's catch-up.
- Client main: `src/main/runs.ts` (`listRuns`, `fetchReport` as text, `reportFileName`); `index.ts` shows the report in its own window (`reportWebPreferences`: no script, no preload) from a temp file, and saves it through a save dialog.
- Renderer: `Runs.tsx` with test and result filters, the table (test, result, start, duration, user), Open report and Save….
- Demo seed adds three sample runs (passed, failed, aborted) with PNG cards, once.

## Decisions (small, local to this task)
- 2026-11-10 — omer: an app-wide endpoint, so the screen opens on every run of the application (rather than "pick a test first").
- 2026-11-10 — omer: the report opens in a separate Electron window plus a Save button (rather than the system browser or an iframe).
- 2026-11-10 — Limit 100 (the screen says so when it is reached); no paging in v0.
- 2026-11-10 — The report window loads a temp file (`<temp>/ayna-reports/<uuid>.html`), not a `data:` URL: a 50-step report is about 15 MB. The file goes when the window closes, the folder at quit. The same run opens again in the same window.
- 2026-11-10 — The report's language is the UI language, read in main (`uiLanguage`), so the renderer sends only the run id.
- 2026-11-10 — The Save dialog comes before the download, so a cancel costs nothing; the file name is "AYNA <test> <local date time>.html", made safe by `reportFileName`.
- 2026-11-10 — "Test" is the same word in Turkish: `runsFilterTest` / `runsHeaderTest` are in `SAME_IN_EVERY_LANGUAGE`.
- 2026-11-12 — A `running` run on the screen updates on Refresh only; subscribing to `/ws/runs` here is left for #44's client half, which builds the live view (confirmed in reply to hasan).
- 2026-11-10 — The list is keyed by its request (`Answered`), so a filter change shows "loading" without a setState in the effect (lint rule `react-hooks/set-state-in-effect`).

## Status
- [x] Branch, #68 In progress on the board
- [x] Server endpoint + 3 integration tests (`RunIntegrationTest` 28/28), OpenAPI regenerated
- [x] Client main, preload, renderer, i18n, styles; `runs.test.ts` (7), `security.test.ts` report window
- [x] Client lint, typecheck, 229/229 tests; `electron-vite build` passes
- [x] Real stack (`docker compose -p ayna68`, port 28080): seed twice → 3 runs, filters by test and by status, TR/EN report of the failed run with 4 screenshots
- [ ] Hand check of the screen in the Electron app (below)
- [x] PR #231 (retargeted to `main` after #229 merged); hasan approved 2026-11-12. His fix before merge is done: report files are swept synchronously at quit and once at start (they hold AUT screenshots). Small points done: a locked old file no longer reports a false failure, `formatDuration` rounds before choosing the unit, the not-found text names the application too, `reportFileName` avoids Windows device names, the seed uses #40's message wording and the runner's `not run: an earlier step failed`.
- Next step: merge #231 when CI is green; hasan checks the screen on Windows (his queue).

## Manual checks
- pending · omer · on macOS. **Setup:** the `ayna68` stack is up on `http://localhost:28080` (admin `demo` / `demo-pass-68`, seeded); `cd client && npm run dev`; Settings → server `http://localhost:28080`, log in as `demo`, choose "AYNA Deneme Uygulaması". **Steps:** 1. open Runs (Ctrl+4); 2. choose test "Hatalı şifre uyarısı"; 3. choose result "Başarısız"; 4. Raporu aç; 5. close the report, Kaydet…, save to Desktop, open the file with Wi-Fi off; 6. switch language to English and open a report again. **Expected:** 1. three runs, newest first, with pills Başarılı / Başarısız / Yarıda kesildi; 2. one run; 3. still one; 4. a window with the Turkish report and four screenshots; 5. "Rapor kaydedildi: …" and the file opens offline; 6. the report is in English. Teardown: `docker compose -p ayna68 down -v`.

## Open issues
- `client/src/main/spy.ts` and `src/main/__tests__/demoSeed.test.ts` are not Prettier-clean on `main` already; CI does not run `format:check`. Left alone (out of scope).
- Report times are in the server's time zone; in Docker that is UTC (#59 note).

## Handoff
- The branch is stacked on `omer/59-run-report`; once #229 merges, `git merge origin/main` here and the PR diff shrinks to #68 alone.

## Outcome (fill when the issue closes)
