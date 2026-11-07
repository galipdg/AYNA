# #184 Object Spy: three-panel workspace

- Issue: https://github.com/galipdg/AYNA/issues/184
- Owner: omer · Branch: `omer/184-spy-workspace` (stacked on `omer/183-ui-design`)
- Started: 2026-11-03 · Last update: 2026-11-07

## Approach
`ObjectSpy.tsx` is three panels in a grid that fills the work area (windows | tree | properties); each panel scrolls on its own. Tree logic (visible rows, search, parents) is pure in `src/shared/tree.ts` (tested in `src/main/__tests__/tree.test.ts`); `ElementTree.tsx` draws only the rows in view (fixed 28 px rows, overscan 10). `PropertyPanel.tsx` groups plain properties (how AYNA finds it, where it is, state) with every descriptor field under Advanced (FR-02). Add to repository replaces the properties in the right panel.

## Decisions (small, local to this task)
- 2026-11-03 — Search folds case and Turkish i/ı/İ (`foldText`) and also matches the plain type label ("text box" finds Edit)
- 2026-11-07 — From hasan's #189 review and Windows run: `foldText` also drops the marks of ş ğ ü ö ç (NFD), so ASCII typing finds Turkish text ("giris" → "Giriş"); search also matches `nearestLabel`, so an unnamed text box is found by its caption (user approved the review scope)
- 2026-11-03 — During a search the chosen element and its ancestors stay drawn even when they do not match, so the selection never disappears
- 2026-11-03 — A selection made outside the tree (pick hotkey, #22) opens its ancestors once; the user can fold them again
- 2026-11-03 — Off screen shown as "Visible yes/no" (inverted) in State; the raw `offscreen` stays under Advanced
- 2026-11-03 — Row offsets use React `style` (CSSOM), which the production CSP (`style-src 'self'`) allows; checked in the built app

## Status
- [x] Three panels, window search, tree search, keyboard (arrows, Home/End), plain groups + Advanced, add form in the right panel
- [x] Large capture: 3031 elements (generated over the mock snapshot, restored after) → 25 of 1112 rows in the DOM, expand ≈ 8 ms, search ≈ 19 ms (macOS, dev build)
- [ ] omer looks at it; Windows session with a pilot app
- [x] 2026-11-07: fold + `nearestLabel` fix, 138 client tests, lint, typecheck, format green
- [ ] Windows session 2026-11-07 (hasan): 6 of 8 steps pass. Step 2 failed on the fold (fixed) and its example needs a Turkish-UI app (the trial app is English); step 6: scrolling and search not smooth at 285 real elements (VS Code), follow-up issue
- Next step: rerun step 2 (English example "user" on the trial app) and step 6 at the next Windows session; `needs-windows-test` stays

## Manual checks
- 2026-11-03 · agent · macOS dark, real server :8080 + fake agent, driven over CDP · three panels, search, add form, 3031-element tree, production CSP · pass after two fixes (form rows stretched; selection hidden by a search) · evidence: screenshots in the session only
- Weekly Windows session · pending; posted on #184 2026-11-03 (issuecomment-6606325026, label `needs-windows-test`); the branch must be pushed before the session. Setup: server + client on Windows, a pilot app open. Steps: (1) choose the pilot window → tree fills the middle, window properties on the right; (2) search a control by its text → matches underlined, ancestors open; (3) choose a control → right panel shows its groups, panels do not move; (4) Advanced → every UIA field; (5) Add to repository → form in the right panel, Save → "Saved …" message; (6) a window with thousands of elements (e.g. a grid) → scrolling and search stay smooth; (7) ⌘/Ctrl+Shift+A over a control (needs #22) → it is chosen and scrolled into view. Report: pass/fail per step, screenshot, Windows version, scaling.

## Open issues
- Search over the full Qt AutomationId is noisy ("Login" → 8 matches, the dotted path names the window); hasan suggests matching the leaf or showing which field matched. Follow-up issue.
- 26 % of VS Code's rows are unnamed Group/Pane/ToolBar wrappers; label them by type or collapse them (hasan, #184 Windows result). Follow-up issue.
- "AutomationId" still shows in the add form's "How AYNA finds it" summary when it is a Find-by property; no plain word for it in the glossary yet (ask at the #183 review).
- The pick hotkey selects nothing until #22 (`elementFromPoint`) lands.

## Handoff
- Large-tree check: generate a snapshot with many elements over `client/dev/mock/snapshot.json`, press Capture again, restore with `git checkout client/dev/mock/snapshot.json`.

## Outcome (fill when the issue closes)
