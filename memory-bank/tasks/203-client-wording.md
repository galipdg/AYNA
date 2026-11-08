# #203 Client wording: Turkish and English points from the #188–#191 reviews

- Issue: https://github.com/galipdg/AYNA/issues/203
- Owner: omer · Branch: `omer/203-client-wording`
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
One pass over `client/src/renderer/src/i18n/{en,tr}.ts`, the glossary in `docs/ui/style-guide.md` §5, and the Turkish demo guides (`DEMO.md`, `DEMO-windows.md`). A new `i18n.test.ts` case guards the spellings (no "öge", no "ajan", no straight `"` in Turkish) so they do not creep back.

## Decisions (small, local to this task)
- 2026-11-08 — "failed" is **Başarısız** (omer): matches "Kontrol başarısız" and what test tools say. Glossary only; the Runs screen has no texts yet.
- 2026-11-08 — Page names **Nesne Gözcüsü** + **Nesne Deposu** (omer). Buttons and messages keep the short "depo" ("Depoya ekle", "Depodan kaldırıldı"); English stays "Repository".
- 2026-11-08 — "Find by" is **Bununla bul** in both the option and the glossary; "Bulma özellikleri" is gone (it appeared nowhere in the UI).
- 2026-11-08 — Timeout texts take their seconds from `CHECK_TIMEOUT_MS` / `REQUEST_TIMEOUT_MS`, now in `shared/api.ts` (main re-exports them). Texts that say "in time" (repository, tests) stay without a number: the import call waits 30 s.
- 2026-11-08 — Repository "Seen in" keys renamed to `repoViewCapturedIn` / `repoViewCapturedHere` / `repoViewNotCapturedHere`.
- 2026-11-08 — "en çok" → "en fazla" in every Turkish text (not only "En fazla bekle"), so the limit texts read alike.
- 2026-11-08 — Typographic quotes “…” in every Turkish text, not only `repoViewNoMatch`; English keeps straight quotes.
- 2026-11-08 — The Verify check property `visible` stays "Visible / Görünür": only the Spy's `offscreen` row became "On screen / Ekranda".

## Status
- [x] Dictionaries, Spy tooltip on "Text", glossary, DEMO guides
- [x] `npm run lint && npm run typecheck && npm test` (203 pass)
- [x] PR #218 (`Closes #203`), reviewers galip and hasan; point-by-point answer posted on #203 (2026-11-08)
- Next step: wait for the #218 reviews and CI; after #217 merges, fix `DEMO.md` line 109 (see Open issues).

## Manual checks
- Not needed beyond a look at the Spy and Repository in `npm run dev:mock` (wording only, no layout change). "Nesne Deposu" is longer than "Depo": check the nav at 1280 px (below 1180 it collapses to icons).

## Open issues
- `DEMO.md` line 109 ("14 öge", "ajanın") is left alone because PR #217 (#207) rewrites that line; fix its new text after #217 merges, to avoid a conflict.
- Other docs (SDD, wireframes, memory) still say "ajan"/"öge" in places; they are not UI and out of scope.

## Handoff
None yet.

## Outcome (fill when the issue closes)
