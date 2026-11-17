# #183 Client UI design, app shell and plain-language UI

- Issue: https://github.com/galipdg/AYNA/issues/183
- Owner: omer · Branch: `omer/183-ui-design` (stacked on `omer/25-repo-objects`, PR #187, because the shell must hold the Spy and the add-to-repository form)
- Started: 2026-11-03 · Last update: 2026-11-15

## Approach
Design first, then code. `docs/ui/` holds the design: `README.md` (principles, review questions), `style-guide.md` (layout, colour tokens, type, components, wording, glossary), `flows.md` (mermaid flows F1–F8), `wireframes.md` (screens 0–14, every RS §3.5.1 screen). After the team review: CSS tokens + component classes in `styles.css`, a shell component (top bar + navigation), and the existing screens moved into it. The Spy's three-panel layout is #184; translation is #185.

## Decisions (small, local to this task)
- 2026-11-03 — Colours as CSS custom properties, light/dark from `prefers-color-scheme`; text colours checked ≥ 4.5:1 (computed in the session) — closed network, accessibility
- 2026-11-03 — Live run status lives in the test editor, not a separate screen (proposed; team to confirm, README Q3)
- 2026-11-03 — omer could not judge the design from ASCII wireframes, so the shell was built before the team review; the team reviews the running shell and `docs/ui/` together before the PR (acceptance criterion 1 read that way)
- 2026-11-03 — Version lives in the shell's state (newest by default), not in saved settings; `VersionBar` replaced by the top bar's `VersionMenu`
- 2026-11-03 — Session ended inside the shell goes back to the login card (not yet a dialog over the screen as in flows F7)

## Status
- [x] Draft `docs/ui/` (wireframes, flows, style guide)
- [x] Shell + shared styles (`Shell.tsx`, `Page.tsx`, `Menu.tsx`, `AppMenu.tsx`, `VersionMenu.tsx`, `SettingsPage.tsx`, `Icons.tsx`, `styles.css`); server settings, login, picker, users, tokens, Spy moved in
- [x] omer looked at the running shell 2026-11-15 (`npm run demo`, macOS): 7/7 steps pass, one finding in Runs fixed (#68)
- [x] Team review: galip and hasan approved PR #188 (merged 2026-11-08) as the design review. Answers: Q1 keep Repairs in the navigation (galip); Q2 NL panel on the right of the test editor, with insert position, dropped steps in place, two kinds of 422, timeouts 30/35/40 s, no model picker, typed text not logged (galip; for #78); Q3 and Q4 no objection, proposals kept; Q5 1280 × 720 design confirmed, the 960–1280 band now says tables may scroll sideways (hasan, #207); Q6 Turkish words applied in #203 (öğe, Aracı, Başarısız, "En fazla bekle"). hasan's Advanced point: style guide now says Advanced is not only for test engineers and opens itself for a Find-by fix (#204). galip's screen 10 point (contributions, largest-remainder rounding) goes to #75.
- [ ] Manual check with someone not on the team or at the weekly session
- Next step (2026-11-15): the hand check at the weekly session (label `needs-windows-test`, steps on #183); on pass, close #183.

## Manual checks
- 2026-11-03 · agent · shell on macOS (dark), real server :8080 + fake agent, driven over CDP · Spy, Later place pass after a fix (long window titles overflowed the panels) · evidence: screenshots in the session only
- 2026-11-15 · omer · macOS 27, `npm run demo` (Docker server + fake agent) · login and app/version/user/language/agent in the top bar; navigation with unbuilt screens unavailable; version only in the top bar; Settings, Users, API tokens in one style; TR ⇄ EN; light and dark; navigation collapses below 1180 px — **pass 7/7**. Finding: Runs row line misaligned in the actions cell → fixed on `omer/68-runs-row-line`, rechecked: pass. Evidence: omer's screenshot (not kept).
- pending · weekly session · the same steps on Windows at 100 % and 150 % (criterion 7)

## Open issues
- RS §3.5.1 says "layouts and wireframes are in the SDD": the SDD (#45, omer) should link `docs/ui/`, and RS §3.5.1 (galip) may point here instead.
- `docs/` is hasan's area; `docs/ui/` is created because #183 asks for it. `docs/README.md` (hasan) does not list it yet.

## Handoff
- See the shell without the mock stub (it has no login): server from `docker compose up`, then in `client/`: `AYNA_AGENT_PYTHON=python3 PYTHONPATH=$PWD/dev/mock AYNA_MOCK_WINDOWS=$PWD/dev/mock/windows.json AYNA_MOCK_SNAPSHOT=$PWD/../schemas/examples/snapshot/trial-login.json AYNA_MOCK_UIA=on npx electron-vite dev`.
- The pick hotkey is `Ctrl+Shift+A` (`client/src/main/spy.ts`), not configurable; shown in the Spy header only (Settings does not show it yet, unlike wireframe 13).
- A CI service account is an ordinary tester account with API tokens (ADR accounts and tokens), not a third role.

## Outcome (fill when the issue closes)
