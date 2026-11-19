# #245 Run report stream is cut off with Access Denied on the async dispatch

- Issue: https://github.com/galipdg/AYNA/issues/245
- Owner: omer · Branch: `omer/245-report-async-auth`
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach
Found during #44's screen check (`npm run demo`): "Raporu aç" failed. `report.html` is a `StreamingResponseBody`, completed on an ASYNC dispatch that `SecurityConfig` re-authorized without the bearer context. Fix: `.dispatcherTypeMatchers(ASYNC, ERROR).permitAll()` first in `authorizeHttpRequests`. A client cannot start an ASYNC/ERROR dispatch itself; each one continues a REQUEST dispatch that passed the rules below it.

## Decisions (small, local to this task)
- 2026-11-15 — regression test lives in `auth/` (`RunReportOverHttpIntegrationTest`), not `runs/` — it is a security test and needs package-private `AccountService.createFirstAdmin`.
- 2026-11-15 — the screenshot endpoint returns `byte[]` (no async dispatch), so it was never affected; the test only checks it is still 401 without a token.

## Status
- [x] failing test over real HTTP (chunked body cut off), fix, test green
- Next step: push and open the PR after omer's OK.

## Manual checks
- Re-open a report from Runs and from the editor's "Run details" in `npm run demo` after the fix (not yet done).

## Open issues
- none
