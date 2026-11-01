# #24 Object Spy view

- Issue: https://github.com/galipdg/AYNA/issues/24
- Owner: omer · Branch: `omer/24-object-spy` (stacked on `omer/17-agent-process-manager`, PR #154, until it merges; do **not** merge this PR into that branch, see `learnings.md` 2026-10-31)
- Started: 2026-10-31 · Last update: 2026-11-01

## Approach
Build the parts that need no snapshot format first: window list over `listWindows`, the on-screen highlight overlay, the screen layout and the hotkey plumbing. The element tree and property panel wait for `schemas/snapshot.schema.json` (#12, hasan); element under the cursor waits for #22. Main process: `src/main/spy.ts` (agent calls → plain results, geometry; no Electron imports, unit-tested) and `src/main/overlay.ts` (`Highlighter`, Electron).

## Decisions (small, local to this task)
- 2026-10-31 — Started before #12/#22 (omer's choice): everything downstream (#15, #25, G0) waits on the snapshot schema; asked hasan on #12 to publish a draft first.
- 2026-10-31 — `AgentManager.call` rejects with typed errors (`AgentNotConnectedError`, `AgentTimeoutError`, `AgentRpcError` with `code`), so callers map `-32001` etc. without parsing messages.
- 2026-10-31 — Overlay is a `data:` page with no script (`javascript: false`, no preload), click-through, `focusable: false`, shown with `showInactive()`, on top at `screen-saver` level. It flashes for 3 s like TestComplete's highlight; the frame sits outside the element (window grown by the 3 px border).
- 2026-10-31 — Physical px → DIP with `screen.screenToDipRect(null, rect)` on Windows only (Electron has it only there; it uses the scale of the display under the rectangle). Elsewhere identity: no UIA backend off Windows.
- 2026-10-31 — The overlay is destroyed when the main window closes; otherwise the hidden window would keep `window-all-closed` from firing.
- 2026-10-31 — Pick hotkey `CommandOrControl+Shift+A` (TestComplete's Object Spy key, familiar to testers), one constant in `spy.ts`. Held only while the Spy is mounted, since a global shortcut takes the key from every program, the app under test included; released on window close and on a main-frame navigation (a reload skips React cleanup). The cursor point goes to the renderer in physical px (`screen.dipToScreenPoint` on Windows).

- 2026-11-01 — Property panel built on `schemas/element.schema.json` 0.1 (#11) without waiting for #12: `ElementDescriptor` + `ELEMENT_FIELDS` in `src/shared/element.ts`, a test keeps the list equal to the schema's fields. Every field is listed; an absent one shows "not captured". Until the tree exists the panel shows the selected window (`windowDescriptor`: title → name + windowTitle, className, bounds, handle → nativeWindowHandle; controlType is not guessed). Bounds show the size, DPI the scaling %.

## Status
- [x] Branch from `omer/17-agent-process-manager` (with `origin/main` merged in), task note, board → In progress
- [x] Typed agent errors; `listWindows` + `highlight` IPC; `Highlighter`; 63 client tests, lint, typecheck green 2026-10-31
- [x] Spy screen (`ObjectSpy.tsx`, shown in the "ready" view): window list, select → highlight + window details, agent error messages, refetch when the agent reconnects. Lint, typecheck, format, 63 tests green 2026-10-31
- [x] Global pick hotkey (`PickHotkey` in `spy.ts`, wired in `index.ts`; the Spy shows the key, or a message when another program holds it, and the picked point). Element lookup needs #22. 66 tests, lint, typecheck, format green 2026-10-31
- [x] Property panel (`PropertyPanel.tsx`) on the element descriptor, fed by the selected window for now. Lint, typecheck, format, 76 tests, build green 2026-11-01; UI look not yet checked by a person (see Manual checks)
- [ ] Element tree (needs the snapshot schema from #12); feed the panel from the selected tree node
- [x] Pushed `937a06f` over HTTPS 2026-10-31; reminded hasan on #12 (schema draft, or fields in a comment and omer drafts the file; answer asked by 2 Nov) and #22 (`elementFromPoint` contract in `docs/agent-rpc.md` first)
- Next step: omer's manual check of the property panel (below); then wait for the snapshot schema (#12, asked on the issue 2026-10-31) for the element tree + property panel; when #22 adds `elementFromPoint` to agent RPC, call it from the pick handler.

## Manual checks
- 2026-10-31 · agent · macOS · built app over CDP with a scratch stub server (health + apps, no auth: the running Compose server is the #60 build and needs a login this branch lacks) and a scratch fake agent answering `listWindows`: list shows both windows ("(no title)", "unknown process" for null), selecting shows details and opens the overlay at 646×486 for a 640×480 window (border 3 px each side), visible then hidden after 3 s; `-32001` variant shows "UI Automation is not available…"; quitting leaves no Electron or agent process. Pass; screenshots in the session scratchpad only (not kept). The overlay itself could not be photographed (no screen-recording permission for the terminal).
- 2026-10-31 · agent · macOS · hotkey registered (hint shows ⌘⇧A, not the "in use" message); after `location.reload()` it registers again, so the old registration was released. Pressing the key could not be simulated (osascript has no keystroke permission) → pending omer's press.
- 2026-11-01 · omer · macOS · `npm run dev` with `AYNA_AGENT_PYTHON` pointing at a scratch fake agent (stdlib WebSocket, `ping` + `listWindows`) and a scratch stub server on 127.0.0.1:8099 (health + apps, no auth): connect + app pick, agent connected, both windows listed, ⌘⇧A hint shown; ⌘⇧A near top-left and bottom-right gives small/large points, also with AYNA in the background; while the Spy is open the key is taken from other apps; after ⌘Q the key works again in a text editor; selecting "AYNA Trial" flashes the frame for 3 s. All pass (reported by omer, no screenshots). This closes the pending press above.
- pending omer · macOS · property panel: select a window → all 17 descriptor fields listed, name/window title/class/bounds (with size)/window handle filled, the rest "not captured" in italics; long values wrap
- Planned for the weekly Windows session (needs a UIA backend, #12): highlight lands exactly on the window at 100 %, 150 % and mixed-DPI monitors (incl. one left of the primary); the frame takes no clicks and no focus; it disappears after 3 s; closing AYNA leaves no frame behind; Ctrl+Shift+A over another app shows the cursor point in physical px (compare with the element's bounds at 150 %), and the key works normally in other apps once the Spy is closed.

## Open issues
- `listWindows` answers `-32001` until #12 lands, so on any machine today the Spy shows "UI Automation not available".
- When #60 lands on `main`, `App.tsx`, `api.ts`, `preload/index.ts` and `main/index.ts` will conflict with this branch (login screen, session); resolve at merge.

## Handoff
- `AgentManager.call` errors are now typed; `describeFailure` in `spy.ts` turns them into `AgentFailure` reasons.

## Outcome (fill when the issue closes)
