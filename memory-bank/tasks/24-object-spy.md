# #24 Object Spy view

- Issue: https://github.com/galipdg/AYNA/issues/24
- Owner: omer · Branch: `omer/24-object-spy` (stacked on `omer/17-agent-process-manager`, PR #154, until it merges; do **not** merge this PR into that branch, see `learnings.md` 2026-10-31)
- Started: 2026-10-31 · Last update: 2026-10-31

## Approach
Build the parts that need no snapshot format first: window list over `listWindows`, the on-screen highlight overlay, the screen layout and the hotkey plumbing. The element tree and property panel wait for `schemas/snapshot.schema.json` (#12, hasan); element under the cursor waits for #22. Main process: `src/main/spy.ts` (agent calls → plain results, geometry; no Electron imports, unit-tested) and `src/main/overlay.ts` (`Highlighter`, Electron).

## Decisions (small, local to this task)
- 2026-10-31 — Started before #12/#22 (omer's choice): everything downstream (#15, #25, G0) waits on the snapshot schema; asked hasan on #12 to publish a draft first.
- 2026-10-31 — `AgentManager.call` rejects with typed errors (`AgentNotConnectedError`, `AgentTimeoutError`, `AgentRpcError` with `code`), so callers map `-32001` etc. without parsing messages.
- 2026-10-31 — Overlay is a `data:` page with no script (`javascript: false`, no preload), click-through, `focusable: false`, shown with `showInactive()`, on top at `screen-saver` level. It flashes for 3 s like TestComplete's highlight; the frame sits outside the element (window grown by the 3 px border).
- 2026-10-31 — Physical px → DIP with `screen.screenToDipRect(null, rect)` on Windows only (Electron has it only there; it uses the scale of the display under the rectangle). Elsewhere identity: no UIA backend off Windows.
- 2026-10-31 — The overlay is destroyed when the main window closes; otherwise the hidden window would keep `window-all-closed` from firing.

## Status
- [x] Branch from `omer/17-agent-process-manager` (with `origin/main` merged in), task note, board → In progress
- [x] Typed agent errors; `listWindows` + `highlight` IPC; `Highlighter`; 63 client tests, lint, typecheck green 2026-10-31
- [ ] Spy screen: window list, select → highlight, error messages
- [ ] Global hotkey plumbing (cursor point in physical px; lookup needs #22)
- [ ] Element tree + property panel (needs the snapshot schema from #12)
- Next step: Spy screen in the renderer (`ObjectSpy.tsx`), reached from the "ready" view.

## Manual checks
- Planned for the weekly Windows session (needs a UIA backend, #12): highlight lands exactly on the window at 100 %, 150 % and mixed-DPI monitors (incl. one left of the primary); the frame takes no clicks and no focus; it disappears after 3 s; closing AYNA leaves no frame behind.

## Open issues
- `listWindows` answers `-32001` until #12 lands, so on any machine today the Spy shows "UI Automation not available".
- When #60 lands on `main`, `App.tsx`, `api.ts`, `preload/index.ts` and `main/index.ts` will conflict with this branch (login screen, session); resolve at merge.

## Handoff
- `AgentManager.call` errors are now typed; `describeFailure` in `spy.ts` turns them into `AgentFailure` reasons.

## Outcome (fill when the issue closes)
