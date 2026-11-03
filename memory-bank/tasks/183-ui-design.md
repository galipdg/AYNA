# #183 Client UI design, app shell and plain-language UI

- Issue: https://github.com/galipdg/AYNA/issues/183
- Owner: omer · Branch: `omer/183-ui-design` (stacked on `omer/25-repo-objects`, PR #187, because the shell must hold the Spy and the add-to-repository form)
- Started: 2026-11-03 · Last update: 2026-11-03

## Approach
Design first, then code. `docs/ui/` holds the design: `README.md` (principles, review questions), `style-guide.md` (layout, colour tokens, type, components, wording, glossary), `flows.md` (mermaid flows F1–F8), `wireframes.md` (screens 0–14, every RS §3.5.1 screen). After the team review: CSS tokens + component classes in `styles.css`, a shell component (top bar + navigation), and the existing screens moved into it. The Spy's three-panel layout is #184; translation is #185.

## Decisions (small, local to this task)
- 2026-11-03 — Colours as CSS custom properties, light/dark from `prefers-color-scheme`; text colours checked ≥ 4.5:1 (computed in the session) — closed network, accessibility
- 2026-11-03 — Live run status lives in the test editor, not a separate screen (proposed; team to confirm, README Q3)

## Status
- [x] Draft `docs/ui/` (wireframes, flows, style guide)
- [ ] omer reviews the draft
- [ ] Team review (galip, hasan); record answers to README questions 1–6 here
- [ ] Shell + shared styles; existing screens moved in
- [ ] Manual check with someone not on the team or at the weekly session
- Next step: omer reviews `docs/ui/`; then ask galip and hasan for the review (PR or the weekly session)

## Manual checks
- (none yet)

## Open issues
- RS §3.5.1 says "layouts and wireframes are in the SDD": the SDD (#45, omer) should link `docs/ui/`, and RS §3.5.1 (galip) may point here instead.
- `docs/` is hasan's area; `docs/ui/` is created because #183 asks for it. `docs/README.md` (hasan) does not list it yet.

## Handoff
- The pick hotkey is `Ctrl+Shift+A` (`client/src/main/spy.ts`), not configurable; Settings shows it read-only.
- A CI service account is an ordinary tester account with API tokens (ADR accounts and tokens), not a third role.

## Outcome (fill when the issue closes)
