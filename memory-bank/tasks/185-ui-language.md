# #185 Client language: Turkish and English

- Issue: https://github.com/galipdg/AYNA/issues/185
- Owner: omer · Branch: `omer/185-ui-language` (stacked on `omer/184-spy-workspace`)
- Started: 2026-11-03 · Last update: 2026-11-03

## Approach
Rules in ADR `2026-11-03-client-ui-language`. No library: `i18n/en.ts` defines `Strings`, `i18n/tr.ts` has the same shape; `strings.ts` holds the current dictionary as a live `export let strings`, so the ~230 `strings.x` reads in the components did not change. App keeps the language in state and provides `LanguageContext`; a switch sets the dictionary first, then the state, so the whole tree re-renders in the new language without remounting (capture, selection and place are kept). `main.tsx` asks main for the language before the first render.

## Decisions (small, local to this task)
- 2026-11-03 — `Settings.language` stores only an explicit choice (null = follow the first-run rule each start) — a user who never chose follows a changed OS language.
- 2026-11-03 — first run uses the OS's *first* preferred language only (`de-DE, en-US` → tr) — the issue's rule, read literally.
- 2026-11-03 — the dictionaries format their own counts (`count`, locale-bound); `formatDate` / `formatTime` read `strings.locale` — no global locale state besides the dictionary.
- 2026-11-03 — known server messages are mapped in **both** languages (English gets the client's wording, without UUIDs) — one rule, and the 409 texts no longer show object ids.
- 2026-11-03 — the i18n test lives in `src/main/__tests__/` and `tsconfig.node.json` includes `strings.ts` + `i18n/` — renderer tests cannot use Node types under `tsconfig.web.json`.
- 2026-11-03 — "Object Spy" → "Nesne Gözcüsü", "Agent" → "Ajan", "Runs" → "Çalıştırmalar", roles "Yönetici" / "Test uzmanı" — first choices; galip and hasan to correct (style-guide glossary).

## Status
- [x] Settings.language, `getLanguage` / `setLanguage` IPC, first-run rule (tests in `settings.test.ts`)
- [x] en + tr dictionaries, parity test (checked it fails when a tr text is removed)
- [x] Switch in top bar, Settings and the gate (pre-login / first-run screens)
- [x] Dates (Users, tokens, capture time) and counts per language
- [x] Server message mapping (`serverText`) in Users, versions, add-to-repository
- [x] ADR (Proposed), docs/ui wireframes + style guide lines
- [x] client/AGENTS.md rule updated (omer's OK 2026-11-03)
- [ ] RS NFR-17 / TBD-2 by galip (inbox note on `omer/25-repo-objects`)
- [x] Pushed, PR #190 opened (base main, stacked on #189); CI 5/5 green on 2026-11-03 (run 41658132027)
- Next step: omer reads both languages on every screen; galip/hasan review the Turkish wording and the ADR on the PR.

## Manual checks
- 2026-11-03 · agent · macOS dark, real server :8080 + fake agent, driven over CDP · first run Turkish (OS tr-TR), gate switch → English saved in settings.json, top-bar switch with a capture open keeps capture and selection, tree search by English type label, Users dates "31 Eki 2026" and duplicate user 409 in Turkish, Settings page · pass · evidence: screenshots in the session only
- pending · omer · read both languages on every screen; Turkish wording

## Open issues
- Texts already stored in component state (a notice shown before the switch) stay in the old language until replaced. Acceptable; noted.
- Agent failure detail (`agent.ts` exit reason, stderr line) and agent RPC messages are shown as sent (English diagnostics). Translating them needs a structured `AgentStatus.detail` — touches #17's pending Windows fix; suggest a follow-up issue if wanted.
- Schema-validation field messages from the server are not mapped (shown as sent).
- Two older `electron-vite dev` instances (16:36, 17:11) run from `client/`; Vite hot-reloaded this branch into them and their old preload has no `getLanguage`, so their windows go blank. Restart them.

## Handoff
- Adding a text: add it to `en.ts`, then `tr.ts`; `npm test` names any key that is missing or still English. Same-on-purpose texts go in `SAME_IN_EVERY_LANGUAGE` in `i18n.test.ts`.
- Changing a server message the client maps: update its pattern in `strings.ts` and the example in `i18n.test.ts`.

## Outcome (fill when the issue closes)
