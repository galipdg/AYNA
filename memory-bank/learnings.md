# Learnings

Append-only. Non-obvious things learned the hard way that help everyone. Format:
`- YYYY-MM-DD · <id> · <area> · <what happened> → <what to do instead>`

- 2026-10-25 · hasan · agent/eval · A venv's `python.exe` on Windows is a launcher that runs the real interpreter as a **child** process, and the GUI window belongs to that child. `pywinauto.Application(backend="uia").start(...)` therefore watches the launcher's PID, never finds the window, and blocks past its own timeout (a blocking COM call cannot be interrupted by pywinauto's wait loop) → launch GUI apps with `subprocess.Popen`, find the window by a UIA property (Qt's ClassName is the Python class name), and clean up with `taskkill /F /T /PID` so the child dies too.
- 2026-10-25 · hasan · eval · Qt (PySide6 6.12, Win11) builds the UIA **AutomationId** as a dotted path over the whole object chain, so `setObjectName("usernameInput")` inside a window named `loginWindow` becomes `QApplication.loginWindow.usernameInput`, not `usernameInput` → the object repository must store the full id, and renaming an ancestor changes every descendant's id (a fragility source worth measuring in RQ1).
- 2026-10-25 · hasan · eval · Qt maps `accessibleName` onto the UIA **Name** property and it *replaces* the control's natural Name: on a top-level window it hides the window title, on a QLabel it hides the label's text, so a checkpoint can no longer read the text it is supposed to verify → set `accessibleName` only on controls with no useful visible text (unlabelled inputs, icon-only buttons), never on windows or labels. This contradicts the "accessibleName on every control" advice in #9's description and should go into the testability guideline (#94).
- 2026-10-25 · hasan · eval · A window's frame contributes UIA controls that belong to Windows, not the app: a TitleBar, a `MenuBar`/`System` menu item and Minimize/Maximize/Close buttons, all with an empty AutomationId → "every button has an AutomationId" checks must be scoped to the app's own widgets (for Qt: UIA ClassName starting with `Q`) or they always fail.
- 2026-10-25 · galip · github · `gh project ...` failed: the default gh token has no Projects scope → run `gh auth refresh -s project` once (browser approval), then move cards with `gh project item-edit` (AYNA board = project 1, owner galipdg, field "Status": Todo / In progress / Done).
- 2026-10-25 · omer · server · Spring Boot 4 moved test annotations to per-module packages: `AutoConfigureMockMvc` is `org.springframework.boot.webmvc.test.autoconfigure`, and start.spring.io names the web starter `spring-boot-starter-webmvc` → check Boot 4 package names before copying Boot 3 examples.
- 2026-10-25 · galip · github · `gh pr edit` fails with "Projects (classic) is being deprecated" (GraphQL `projectCards`) → update the PR with `gh api -X PATCH repos/galipdg/AYNA/pulls/<n> -F body=@file.md` instead.
- 2026-10-25 · galip · agent · pywinauto 0.6.9's `Desktop(backend="uia").windows()` defaults to `visible_only=False` (unlike `find_elements`), and `UIAElementInfo` properties turn COM errors into `None`/`""`, so a failed read looks like an empty AutomationId or Name → pass `visible_only=True`, and read `element_info.element.Current*` when you need to tell "empty" from "failed". PyPI also has a 1.0.0b1 pre-release (2026-10-15); pin `pywinauto==0.6.9` until we test 1.0.
- 2026-10-25 · omer · #3 · GitHub Actions YAML: in a plain (unquoted) `run:` value, ` #` starts a comment, so `run: echo "see #5"` reaches the shell as `echo "see` and fails with "unexpected EOF". Use a block scalar (`run: |`) or quote the whole value.
- 2026-10-25 · omer · client · Electron 45 no longer downloads its binary on `npm install` (no postinstall; it downloads lazily), but electron-vite looks for `node_modules/electron/path.txt` and fails with "Electron uninstall" → `client/` runs `install-electron` as `predev` / `prepreview`. Closed-network build machines will need `ELECTRON_MIRROR` / `electron_config_cache` pointing at a local copy.
- 2026-10-25 · omer · client · vitest 4 and 5 make npm 10 and 11 crash during install with `Cannot read properties of null (reading 'edgesOut')` (arborist `#loadPeerSet`, peer chain via `@vitest/mocker` → msw). Not a cache problem; reproduces in an empty dir → `client/` uses `node --test`. With `"type"` unset in package.json, add `--disable-warning=MODULE_TYPELESS_PACKAGE_JSON` for ESM test files.
- 2026-10-25 · omer · client · `tsc` with a `jsconfig.json` defaults to `maxNodeModuleJsDepth: 2` and type-checks plain JS inside node_modules (hundreds of errors from e.g. `string_decoder`) → set it to 0.
- 2026-10-25 · omer · client · typescript-eslint 8.72 accepts only TypeScript `<6.1`, while `npm i typescript` installs 7.x (the native port) → pin `typescript@~6.0` until typescript-eslint supports 7.
- 2026-10-25 · hasan · github · GitHub applies issue-closing keywords found in **commit messages**, not only in PR bodies: galip's commit body said "...and closes #6 with his own PR", so merging PR #119 (whose body deliberately said `Refs #6`, "merging it does not close the issue") auto-closed #6 one second later, with none of its acceptance criteria met → never write `closes/fixes/resolves #<n>` in a commit message unless you mean it right now; phrase it as "#<n> will be closed by a later PR" or just "for #<n>". A `Refs #<n>` in the PR body does not protect you if a commit body says otherwise.
- 2026-10-27 · hasan · eval/agent · The UIA tree is **asymmetric** for an owned modal dialog: KeePass 2's "Add Entry" is owned by a child window of the main form, so UIA reports its parent as that form's ToolBar, the ToolBar's own `children()` do not list it, and the desktop root does not either. A walker that starts at the desktop (or at the app's main window) misses the whole dialog — in #6 it cost 40 elements and every one of the entry editor's fields → find top-level windows with Win32 `EnumWindows` and convert the handles to `UIAElementInfo(hwnd)`. Deduplicate by window handle afterwards, because an owned dialog that *is* reachable downward (Notepad++'s Find) would otherwise be dumped twice.
- 2026-10-27 · hasan · eval/agent · While a modal **shell** dialog (class `#32770`: Save As, Open) is up, `Desktop(backend="uia").windows()` and any `children()` call into that process hang for minutes (killed after 3 min; it returned immediately once the dialog closed). Win32 keeps working throughout: `EnumWindows` + `SendMessage(BM_CLICK)` on the button, or sending keys, closes the dialog → never leave a file dialog open while taking a snapshot, and prefer Win32 to drive one.
- 2026-10-27 · hasan · eval · A WinForms app with a modal dialog open answers UIA very slowly: one `children()` call on the (disabled) main window's ToolBar took 18 s and the full KeePass 2 walk 279 s, against 2 s for WPF and 0.5 s for Qt on the same machine → the 2 s snapshot target of #12 is unreachable with per-property COM reads on WinForms; it needs cached requests (`IUIAutomation.AddPropertyCachedRequest`) and most likely a dialog-only scope.
- 2026-10-27 · hasan · eval · UIA cannot fill password fields: `ValuePattern.SetValue` is blocked on them (`ElementNotEnabled`), KeePassXC (Qt 6.11) does not even expose its password box as an `Edit` element, and the wizard page bottoms out at `Group`/`Pane` → type into password fields with keystrokes. `set_focus()` is not enough either; it returns while the window is still in the background (`has_keyboard_focus()` False) → check `GetForegroundWindow()`'s PID before sending keys and abort if it is not the target, or the keystrokes land in whatever the user is doing.
- 2026-10-27 · hasan · eval · KeePassXC locks its database after a few minutes of inactivity and throws away the open entry form (the dump then only contains the unlock screen: 58 elements instead of 84) → prepare an app's state immediately before the dump, and check the dumped window title before trusting the numbers.
- 2026-10-25 · omer · #14 · neo4j-migrations creates its own `__Neo4jMigrationsLock` uniqueness constraints and `__Neo4jMigration` nodes in the same database; filter `__`-prefixed labels out of any test or query that lists constraints, indexes or labels.
- 2026-10-26 · omer · git · On some networks SSH to github.com (port 22 and ssh.github.com:443) times out while HTTPS works → one-off `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' fetch|push https://github.com/galipdg/AYNA.git …` without changing global config.
- 2026-10-26 · omer · #18 · support.ranorex.com (Zendesk) returns 403 to curl and WebFetch, so link checks report its articles as broken → read them through the public Zendesk API `https://support.ranorex.com/api/v2/help_center/en-us/articles/<id>.json` (title + body) or search with `/api/v2/help_center/articles/search.json?query=…`.
- 2026-10-27 · galip · git · `merge=union` brings deleted lines back: if one branch deletes handled items from an `inbox.md` while another open branch appends to the same file, the merge (in either order) keeps the deleted items next to the new one (tested in a scratch repo) → delete handled inbox items only when no open PR touches that inbox (`gh pr list --search "<path>"`), or delete them again after those PRs merge.
- 2026-10-28 · galip · #147 · Grammar-constrained decoding keeps the JSON shape but not the content of a free string: with the step schema's derived grammar, qwen3:8b filled a checkpoint's `column` (free string, `maxLength` 100) with `}}]}</think>` and 100 characters of garbage, and the document was still schema-valid → narrow every free string whose values are known (targets, column headers, list items) to an `enum` in the generation schema, and keep `maxLength` on the rest.
- 2026-10-27 · galip · ai · `pip install -e` worked once, then `import ayna_ai` failed with ModuleNotFoundError: on galip's Mac new files under the repo get the macOS `hidden` flag (`ls -lO` shows `hidden`), and Python 3.11.13+ / 3.15 `site.py` skips hidden `.pth` files, so the editable-install hook is ignored. `chflags nohidden` on the `.pth` helps only until the flag is set again (it came back within the hour) → run `PYTHONPATH=. pytest` (and `PYTHONPATH=. python -m ...`) from the module folder. CI is not affected.
- 2026-10-27 · galip · ai · jsonschema (4.26) reports a field forbidden by a `false` subschema (e.g. `"then": {"properties": {"value": false}}` for a Click step) at the **enclosing object** with "False schema does not allow 'x'": `absolute_path` and `schema_path` do not name the field → to name it, find the key whose value `is error.instance` (see `_describe` in `ai/ayna_ai/validate.py`); do not filter such errors by path.
- 2026-10-27 · galip · ai · Ollama (0.40.11, qwen3:8b) at temperature 0 with a fixed seed gave **different answers to the identical request** on the same Mac (SC-27 sentence: `none.noMatch` in 4 runs, `login.passwordInput` in 4 later runs) — the earlier runs coincided with heavy machine load / other clients and a different prompt-cache state; it only shows when the decision is close → treat "deterministic" as "nearly always", run RQ3/model comparisons on an otherwise idle machine, record the load, and repeat borderline cases.
- 2026-10-27 · galip · agent · `pip install -e` in `agent/.venv` worked, but `import ayna_agent` failed: files under the repo on this Mac carry the macOS `hidden` flag (`ls -lO` shows it; it comes back after `chflags nohidden`), and recent Python (seen with 3.12.9) skips hidden `.pth` files, so the editable install is never loaded → run tests as `python -m pytest` from `agent/` (puts the current directory on `sys.path`) or set `PYTHONPATH=.`; CI on Windows is not affected.
- 2026-10-29 · omer · #39 · networknt json-schema-validator 3.x (server step validation) writes its messages in the JVM's default locale, so on a Turkish Windows or macOS they come out in Turkish ("gerekli 'value' özelliği bulunamadı") → set `SchemaRegistryConfig.builder().locale(...)` explicitly (`StepSchema.java` uses English). It also reports a missing (`required`) or extra (`additionalProperties`) field at the parent object's path and a forbidden field as "schema for 'x' is false"; `StepSchema.fieldError` moves the path onto the field itself.
- 2026-10-29 · omer · #45 · GitHub marks a PR "conflicting" when only `merge=union` files (`inbox.md`, `journal.md`, `learnings.md`) clash, because its merge ignores the union driver; locally `git merge origin/main` resolves them silently. To tell real conflicts from these, run `git merge-tree --write-tree --name-only origin/main origin/<branch>`: an empty conflict list means a plain merge + push clears GitHub's flag.
- 2026-10-29 · omer · #31 · springdoc 3.x (Boot 4) keeps Swagger UI's default `url: "https://petstore.swagger.io/v2/swagger.json"` in `swagger-initializer.js` and only appends `configUrl`; the UI falls back to it if the config fails → set `springdoc.swagger-ui.disable-swagger-default-url=true` (and `validator-url=none`) on a closed network. For a stable generated `openapi.yaml`, also set `springdoc.writer-with-order-by-keys=true` and a fixed server URL, else the test's random port leaks into `servers:`.
- 2026-10-29 · omer · github · Pushing over HTTPS with `gh auth git-credential` is rejected for any commit that touches `.github/workflows/` ("refusing to allow an OAuth App to create or update workflow … without `workflow` scope") → `gh auth refresh -h github.com -s workflow` once (browser approval; inside Claude Code's `!` run it needs `-h`, else run it in a separate terminal).
- 2026-10-29 · omer · #158 · springdoc 3.x: once a controller method has a swagger `@ApiResponse` (e.g. a 404) and no `@ResponseStatus`, the generated 200 response disappears from the contract → add error responses with an `OperationCustomizer` instead (`@ErrorResponses` + `OpenApiConfig.errorResponses()`); it runs after the success response is built. Also: Spring omits `type` from a `ProblemDetail` body when it is `about:blank`.
- 2026-10-31 · omer · docker · Server exits at start with `AuthenticationException: The client is unauthorized` after `NEO4J_PASSWORD` was changed in `.env`: Neo4j applies `NEO4J_AUTH` only when the volume is first created → keep the old password or `docker compose down -v` (deletes the data). Neo4j 5 also refuses to start (exit 70) with a password under 8 characters; the AYNA first admin needs 8 too.
- 2026-10-31 · omer · github · Merging a stacked PR (base = another feature branch) skips the review gate twice: GitHub allows it with no approvals, and `Closes #n` does not fire because the base is not `main`; the code then reaches `main` inside the base PR, whose older approvals do not cover it (#168 → #160) → never merge a stacked PR into its base; wait for the base to merge, retarget to `main`, then review. To undo, revert the squash commit on the base branch and open a new PR from the original branch.
- 2026-10-31 · omer · ci · GitHub-hosted `windows-latest` runners have an interactive desktop: the `eval` job launches the PySide6 trial app and drives it with pywinauto UIA (`eval/apps/trial/tests/test_uia.py`, 5 tests, ~3 s) with no extra setup. Useful for #67 (sample suite on a Windows runner).
- 2026-10-29 · hasan · #6 · A Qt Widgets AutomationId is present but usually **not unique**: Qt builds it as the dotted path of `objectName`s and a widget without an `objectName` contributes its *class name* instead, so siblings collide (in KeePassXC 2.8 all 14 toolbar buttons are `Application.MainWindow.toolBar.QToolButton`; only 8% of its interactive AutomationIds are unique in their window). The path also grows with nesting depth and passes 200 characters around 11 levels, and inserting any widget above an element rewrites its id → on Qt, treat AutomationId as a weak property and never match on it alone; in WPF and WinForms every id that exists *is* unique in its window (100% in both).
- 2026-10-29 · hasan · #6 · UIA's `LabeledBy` is populated for **0 of 204** interactive elements across WinForms, WPF, Qt and Win32 (KeePass 2, HandBrake, KeePassXC, Notepad++), read from the raw `IUIAutomationElement.CurrentLabeledBy` with 0 read errors — apps simply do not set `AutomationProperties.LabeledBy` / a Qt buddy label → find a field's label geometrically (nearest `Text` left of or above it inside the same container), do not rely on `LabeledBy`. `AcceleratorKey` is 0% everywhere too; `AccessKey` (the `&` mnemonic) is the one secondary text property that is populated, 13–39%.
- 2026-10-29 · hasan · #6 · A property-complete UIA walk over a **WinForms** window is two orders of magnitude slower than over WPF: KeePass 2 took 278.5 s for 106 elements where HandBrake took 1.97 s for 149, with `read_errors: 0` in both (so nothing timed out and was swallowed — the reads themselves cost ~2.6 s per element). The suspect is the ten pattern probes per element over the WinForms COM bridge, not yet isolated with `--no-patterns` → do not size a snapshot budget from a WPF or Win32 measurement, and measure WinForms with and without pattern probes before promising a 2 s snapshot (#12).
- 2026-10-29 · hasan · #6 · **Corrects the two 2026-10-29 `#6` entries above that were measured on KeePassXC's unlock screen.** The first KeePassXC dump caught the locked database (58 elements, no form), and the re-take on the entry form (84 elements, 41 interactive) moves the numbers: unique AutomationIds 8% → **10% (4/41)**, and the 200-character clip bites much harder than it looked — **25 of 84 ids are clipped**, in 5 groups of indistinguishable prefixes covering 23 elements, including a password `Edit` and its parent `Group`, which share a clipped id → when a spike's numbers come from one window, say which window in the note; a dump of an app's *idle* screen measures the idle screen, not the app.
- 2026-10-29 · hasan · #6 · UIA's `LabeledBy` **is** populated by Qt, contrary to the 2026-10-29 entry above that measured 0 of 204: on KeePassXC's entry form 5 of 41 interactive elements (12%) carry one (`Title:`, `Username:`, `Notes:`, `URL:`, `Expires:`), derived from the `QFormLayout` buddy label. WinForms, WPF and Win32 really are at 0% over 178 interactive elements. Two traps: the property sits on the **row container, not the editable control** (the password row's `Group` has `LabeledBy = "Password:"` while the `IsPassword` `Edit` inside it has neither a Name nor a `LabeledBy`), and the labelled containers are not in the interactive set → a label lookup (#11) still has to work geometrically, but should read `LabeledBy` on the element *and its parent* first, and on Qt it can be used to check the geometric answer.
- 2026-10-29 · hasan · #6 · Narrows the 2026-10-27 entry "KeePassXC does not even expose its password box as an `Edit`": on the **entry form** it does — an `Edit` with `IsPassword: True`, no Name, wrapped in a `Group` named `Password field`. It is the **unlock screen and the new-database wizard** that bottom out at `Group`/`Pane` → do not generalise a control-type observation from one screen of a Qt app to the whole app; re-check it on the screen the test actually targets.
- 2026-10-29 · hasan · #150 · A Qt table exposes **no row elements and no per-cell identity**: a `QTableWidget`'s raw children are its column headers, its row headers (named `1`, `2`, `3`) and its cells, flat and interleaved, and *every one of them carries the table's own AutomationId* (all 16 descendants of a probe table shared `QApplication.<window>.central.customerGrid`). A cell is identifiable only through `GridItemPattern` row/column, which are **0-based** while a tester counts rows from 1. `GridPattern.CurrentRowCount` excludes the header row, and `TablePattern.GetCurrentColumnHeaders()` returns the header texts, so addressing a row by index or by a key cell both work → never store a cell as a repository object, address rows through the grid, and do not let candidate generation (#42) assume AutomationId narrows anything inside a Qt grid.
- 2026-10-29 · hasan · #150 · A Qt cell's text is in its **Name**; it also exposes a `ValuePattern` whose value is the **empty string** (all 9 cells of a probe table, and `QListWidget` items behave the same). So a "ValuePattern first, else Name" rule reads `''` for every Qt cell → read Name first and fall back to ValuePattern, or take whichever is non-empty. `SelectionItemPattern.Select()` on a row's first cell does select the whole row, but only because the view had `setSelectionBehavior(SelectRows)`; with Qt's default (`SelectItems`) the same call selects one cell while every check still passes → a "select the row" keyword must either require a row-selecting grid or verify what it actually selected.
- 2026-10-29 · hasan · #6 · **Narrows the 278.5 s WinForms entry above: the pattern-probe hypothesis is not supported.** On KeePass 2's start-up window, 15 plain property reads cost **2.79 ms per element** and the ten pattern probes **1.56 ms per element** — the probes are *cheaper* than the properties, and both together extrapolate to about 0.5 s for 106 elements against the 278.5 s measured. Measured on only 6 reachable elements of the start-up "open database" dialog, not the Add Entry dialog with a database open that the #6 dump captured → the WinForms COM bridge is not inherently slow; the outlier is tied to that window state and is still unexplained. Reproduce the #6 state before bisecting further.
- 2026-10-29 · hasan · #22 · `IUIAutomation::ElementFromPoint` costs **~5 ms** (median 4.7 ms, max 6.0 ms over 5 calls) on a WinForms window, so NFR-01's 300 ms budget for the Spy pick is comfortable and whatever risk that requirement carries is in filling the property panel afterwards, not in the hit test.
- 2026-10-29 · hasan · #49 · The healing scorer's location similarity has its cut-off in **physical** pixels (`1 - d/100 px`), while a layout shift is a device-independent quantity, so the same movement scores differently per display scaling: a control moved 64 DIP scores 0.36 at 100%, **0.20 at 125%** (this machine, DPI 120), 0.04 at 150% and 0.00 at 200% → divide the distance by `dpi/96` (`GetDpiForWindow`, which `eval/spikes/uia_dump.py` already records per window) before comparing, or an RQ4 number is not comparable between machines.
- 2026-10-29 · hasan · git · **The `merge=union` conflict flag cascades, so a batch of PRs has to be merged one at a time.** Nine open PRs all appended to `memory-bank/people/hasan/inbox.md`, so GitHub flagged every one of them as conflicting (it ignores the union driver — see omer's 2026-10-29 entry). Merging the first one re-flags the remaining eight, because each still appends to the same trailing region: the fix is not a one-off, it is `git merge origin/main` + push on every remaining branch **after each merge**. Nine PRs cost nine rounds. Verify a re-sync with `git diff --name-only origin/main...<branch>` before and after — if the file set shrinks, that is the stacked-PR cleanup (the base PR's files dropping out), not content loss; if it grows, stop. Chaining the branches into each other collapses it to one round but invalidates reviews that were given on the individual diffs → not worth it. The real fix is to stop appending to one shared file: a directory of dated one-fact files never conflicts (proposed, needs an ADR).
- 2026-10-31 · hasan · #161 · A UI Automation walk of a WinForms window costs ~18 ms per element — until the application stops pumping messages, and then it collapses: with a modal message box open (KeePass's "password is weak" Yes/No box), a traversal-only walk of the window behind it took **230 s for 85 elements** against 0.6 s for the same 114-element walk with the box closed. The median element stayed at 1.4 ms; six container elements (the dialog window 72.5 s, the main window 30 s, a ComboBox 24 s, the ToolBar 18 s) absorbed 170 s of it, because `GetFirstChild`/`FindAll` on a container needs the provider's UI thread and the box owns it. A *tracked menu* does not do this (1.55 s with the File menu open) — the message box's own modal loop does. Consequences: (1) any snapshot/search deadline must be enforced on a timer, not between elements, because a single call can block for a minute; (2) "the app is showing a message box" is a far more likely cause of a snapshot timeout than "the window is huge", so report what the walk was blocked on; (3) when a measurement on a desktop app is 100× out, suspect a modal dialog before suspecting the framework. Measured with `eval/spikes/uia_probe.py`, raw data in `eval/spikes/uia-probe-keepass2-modal.json`.
- 2026-11-01 · hasan · #161 #12 · **A walk that starts from every top-level window counts an owned dialog twice.** An owned modal dialog (KeePass 2's *Add Entry*, Notepad++'s *Find*) is both a top-level window — so `find_windows` returns it as a root — and a child of its owner in the UIA tree, so a pre-order walk over those roots visits its whole subtree twice. `uia_dump.walk` deduplicates by window handle and was right; `uia_probe.py` did not and reported 154 elements for a tree of 114 (#170 review caught it from the depths in the slowest table: the same pane at depth 0 and at depth 1). Two things make this hard to spot: the inflated count sits in the *totals* (~26 % too high here) while the *per-element* mean looks fine — in fact flattered, because the second pass over an already-realised subtree is cheaper, which is why the corrected per-element cost went **up** from 11.6 to 18.5 ms. So: deduplicate by handle (`None`/0 never skipped, first visit wins, subtree included), order the roots owner-first so depths are real, and report what was skipped. Anything that walks windows — #12's snapshot, Spy, healing candidate collection — needs this, and a number that cannot be decomposed into count × per-element should not be trusted.

- 2026-11-01 · #12 #16 · **`python -m some.module` makes two copies of that module, and
  `isinstance` then fails across them.** `ayna_agent/rpc.py` run as `python -m ayna_agent.rpc`
  is imported as `__main__`; the recognition backend then does
  `from ayna_agent.rpc import UiaUnavailable`, which imports the file *again* under its real
  name. The two copies have two different `UiaUnavailable` classes, so the backend's error
  sailed past the dispatcher's `except UiaUnavailable` and came out as `-32603 Internal error`
  instead of `-32001`. Nothing in the unit tests sees this: they import `ayna_agent.rpc`
  normally, and only the subprocess test that actually runs the CLI caught it. Fix, and the
  pattern for any `__main__` module that others import from:
  `if __name__ == "__main__": from ayna_agent.rpc import main as _main; sys.exit(_main())`.
- 2026-11-01 · #12 #161 · **A UIA walk's cost is dominated by how many properties you read,
  not by the framework.** The same KeePass 2 (WinForms) window that #161 measured at 2.26 s for
  114 elements with the #6 dump's 17 properties + 10 pattern probes walks in **819 ms** when it
  reads only the 12 properties the element descriptor stores (7.2 ms per element against 19.8).
  So a budget derived from the dump's reader is an upper bound for the snapshot's, with a lot of
  room in it.
- 2026-11-01 · #12 · **A window that stops pumping messages cannot be escaped from inside the
  walk, and the timer design works.** Measured against a Qt window whose GUI thread slept 40 s:
  the very first UIA read blocked, so no between-element clock check could ever fire, and the
  walk thread was still inside that call. Running the walk on its own daemon thread and having
  the caller `join(budget + 250 ms)` returned `-32002` after **2251 ms** of a 2 000 ms budget,
  twice in a row in the same process, and snapshots of that window worked again (58 ms) once it
  thawed. The cost is one leaked daemon thread per timeout, which is why the backend counts them
  and logs the count at shutdown.
- 2026-11-01 · hasan · #71 #16 #17 · **On Windows a TCP connect to a closed port on 127.0.0.1 can time out instead of being refused**, so "the service is not running" arrives as a *timeout*, not as "connection refused". Measured twice in a row on the project machine (Windows 11 26300, default Defender Firewall): `socket.connect` and `urllib.request.urlopen` to a port nobody listens on both raised `TimeoutError` after the full 2 s, where macOS/Linux raise `ECONNREFUSED` in microseconds — the SYN is dropped, not answered with RST. It is not deterministic: in one run of the ai suite the same free port was refused for one call and dropped for the next. Why it matters beyond a test: code that distinguishes "down" from "slow" by which exception fired gets the answer wrong on our deployment platform. In the AI service (#71) `ModelTimeout` maps to HTTP 504 `timeout` while `cannot reach` maps to 503 `server_error`, and `ai/API.md` tells the client to retry on 504 but to disable the panel on 503 — so a model server that is simply not running can tell the user to retry, after the whole request timeout has elapsed. The same shape is in the agent RPC handshake (#16/#135) and the client's agent process manager (#17). Rule: decide "unreachable" by whether the *connection* came up (a short `create_connection` probe, or a connect timeout separate from the read timeout), never by the exception type alone, and never let a liveness check inherit a 30 s request timeout.
- 2026-11-01 · omer · server · **After switching branches, run `./mvnw clean test`, not `./mvnw test`.** Maven never deletes resources that left `src/`, so a migration from another branch (here `V0003__accounts_and_tokens.cypher` from #60) stays in `target/classes`, neo4j-migrations applies it, and `GraphSchemaMigrationIntegrationTest` fails with unexpected labels (`User`, `AuthToken`) and an extra migration. CI is unaffected (fresh checkout).

- 2026-11-01 · omer · GitHub's "This branch has conflicts" ignores `.gitattributes`, so `merge=union` files (inboxes, journals, `learnings.md`, `decisions/README.md`) block a PR even though `git merge origin/main` locally resolves them silently. Fix: merge `main` into the branch and push the merge commit. To see what GitHub sees: `git --attr-source=4b825dc642cb6eb9a060e54bf8d69288fbee4904 merge-tree --write-tree --name-only origin/main <branch>` (empty tree as attribute source, git ≥ 2.40).

## 2026-11-01 — a Qt AutomationId is not unique inside an item view

Qt builds an AutomationId from the `objectName` chain, but an item view's children (table rows
and cells, list items, tree items) have no `objectName` of their own, so they inherit their
**container's** id verbatim. Measured two ways: each of KeePassXC's four `QListWidget`
ListItems carries its `List` parent's AutomationId exactly (`eval/spikes/uia-dumps/keepassxc.json`,
#6), and #150 measured the same for every cell of a Qt table.

Consequences, because this bites in three places: a "no duplicated AutomationId" test on the
sample app (#33) would fail on its own results grid, so it must exclude ListItem, DataItem and
TreeItem; the Spy (#24) and the element descriptor (#11) must not present an AutomationId as a
unique identifier inside an item view; and items are addressed by Name, or by row and cell from
step schema v0.2. Written into ADR `2026-10-31-pilot-apps-and-sample-app-technology` (#21).
- 2026-11-01 · omer · git · **A branch stacked on a PR that was squash-merged conflicts with `main` everywhere the base PR touched** (add/add on every new file), because `main` has the base PR's content but not its commits. Do not resolve by hand and do not merge the base branch's tip if it carries a revert. Find the last commit of the base branch your branch contains (or the merge commit where both histories meet, e.g. `acce05c` for #60), then `git merge origin/main`, `T=$(git merge-tree --write-tree --merge-base=<that commit> <branch> origin/main | head -1)`, `git restore --source=$T --staged --worktree :/`, fix only the remaining real conflicts, commit. Check: `git diff --name-only <that commit> <branch>` and `git diff --cached --name-only origin/main` list the same files.
- 2026-11-01 · #12 · **`Path.read_text(newline=...)` is Python 3.13 only; `write_text(newline=...)`
  is 3.10.** The asymmetry is easy to miss and both modules declare `requires-python = ">=3.11"`.
  My machine runs 3.13, so two tests passed locally and failed in CI, which uses 3.11.9. For a
  byte-exact comparison use `path.read_bytes().decode("utf-8")` anyway: it is version-proof and it
  is what "the same file" actually means. **General point: the only Python on this Windows machine
  is 3.13, so nothing here can verify the 3.11 floor — CI is the only check, and a green local run
  is not evidence that the version floor holds.**
- 2026-11-02 · galip · A repo under an iCloud-synced `~/Desktop` (macOS "Desktop & Documents" with "Optimize Mac Storage") gets files evicted to "dataless" placeholders, including `.venv` packages and `.git` loose objects and reflogs (`find . -flags +dataless`). Reading one blocks and then fails with `TimeoutError: [Errno 60]`. pytest fails on import; `git push` updates the remote but cannot append the local reflog, so `origin/*` goes stale; Finder sync leaves " 2" duplicates. `brctl download` did not restore them here. Keep the checkout outside iCloud folders. Until then, run the tests from a venv created outside them.
- 2026-11-03 · omer · #15 · **A shared schema the server reads must be listed in three places**: `server/pom.xml` (resources include), `server/Dockerfile` (COPY) and `server/Dockerfile.dockerignore` (`!schemas/...`). `./mvnw test` passes with only the pom entry; the Docker image then fails at startup because the bean cannot read the file. Build the image (`docker build -f server/Dockerfile .`) after adding one.
- 2026-11-03 · omer · #15 · **The compose Neo4j volume remembers migrations from other branches.** After running a branch that adds `V0003`, starting the server from a branch without it fails with "More migrations have been applied to the database than locally resolved". Not a bug in the branch: test against a throwaway Neo4j (`docker run --rm neo4j:5.26-community` on its own network) instead of wiping the shared volume.
- 2026-11-03 · omer · #185 · **Every `electron-vite dev` started from `client/` hot-reloads the renderer of the current checkout**, even instances started earlier from another branch (Vite takes the next free port, 5173 → 5174 → …). When the new renderer calls a bridge method the old preload lacks, that window goes blank. A second instance with the same `--remoteDebuggingPort` cannot bind it (`bind() failed`), and CDP silently reaches the *old* window. Before checking a branch: `ps -eo pid,lstart,command | grep electron-vite`, close old instances, and use a fresh debugging port.

- 2026-11-05 · omer · git · `git grep -E '\bfoo'` on macOS finds nothing and reports no error, because the system regex library has no `\b`: a search for references can look clean when it is not → use `git grep -P`, or spell out the boundary as `(^|[^A-Za-z0-9-])foo`. Also, git treats a row edited directly above a row another branch inserts as a conflict, even with no shared line: test with `git merge-tree --write-tree --name-only` before promising two PRs will not conflict.
- 2026-11-03 · omer · #15 · **A shared schema the server reads must be listed in three places**: `server/pom.xml` (resources include), `server/Dockerfile` (COPY) and `server/Dockerfile.dockerignore` (`!schemas/...`). `./mvnw test` passes with only the pom entry; the Docker image then fails at startup because the bean cannot read the file. Build the image (`docker build -f server/Dockerfile .`) after adding one.
- 2026-11-03 · omer · #15 · **The compose Neo4j volume remembers migrations from other branches.** After running a branch that adds `V0003`, starting the server from a branch without it fails with "More migrations have been applied to the database than locally resolved". Not a bug in the branch: test against a throwaway Neo4j (`docker run --rm neo4j:5.26-community` on its own network) instead of wiping the shared volume.
- 2026-11-05 · omer · #44 · Neo4j Community enforces composite uniqueness (`REQUIRE (n.a, n.b) IS UNIQUE`), and with it a losing concurrent write ends in `ClientException` code `Neo.ClientError.Schema.ConstraintValidationFailed`, which `executeWrite` does not retry → catch that code and read again if a repeat is legal (`RunService.writeResult`). Without the catch, 8 overlapping writes fail at once.
- 2026-11-05 · omer · #44 · Node's global WebSocket (undici, used in the Electron main process) sends no `Origin` header, so Spring's default same-origin WebSocket check lets it through with no `setAllowedOrigins`; the Bearer header passes the normal security chain because the upgrade is an ordinary GET.
- 2026-11-05 · omer · #170 · **A race can hide under CPU load.** `test_the_request_log_holds_no_instruction_text` failed 9 of 1 500 repeats on an idle machine and 0 of 300 under heavy load, so a load run proved nothing. To show a timing cause, inject a delay at the suspected point and compare the fix on the same setup. Also in zsh: `kill $pids` does not split a space-separated string, so background loops keep running; use an array and check with `ps` afterwards.

## 2026-11-07 — KeePass 2's entry list is a UIA List with no Grid or Table pattern (hasan, #150/#147)

Measured on Windows 11 Pro 26300 at 120 DPI, KeePass 2 from `C:\ayna-pilots\keepass2\` with the
demo database, raw UIA through pywinauto 0.6.9 after `eval/spikes/kp_state.py main`:

- `m_lvEntries` (`WindowsForms10.SysListView32…`) is a UIA **List** whose only patterns are
  `Selection` and `LegacyIAccessible`. **No Grid pattern, no Table pattern**, so `GridPattern`
  `RowCount`/`GetItem` and `TablePattern.GetColumnHeaders` are all unavailable on it.
- Its ControlView children are a `Header` (5 `HeaderItem`s: Title, User Name, Password, URL, Notes)
  and one `ListItem` per entry. So **the list has columns without having a TablePattern** — the
  reason `cell` is grid-only is the `column` definition (a TablePattern header Name), not "a list
  has no columns".
- Each `ListItem`'s `Name` is the **Title column only**, but it has **five `Text` children, one per
  column, in header order**, each carrying its column's text in `Name`. The #6 dump showed none of
  them because it was taken with the Add Entry dialog on top. So a per-column read on a
  pattern-less list is possible through those children — which is how #40 answers
  `rowExists {value}` and `{value, column}` on KeePass 2.
- **No ValuePattern anywhere** on the list, the items or the Text children. The v0.2 cell-text rule
  (non-empty ValuePattern value, else Name) therefore reads Name, which is correct — and means
  Name-first and Value-first are indistinguishable on every WinForms control we actually have.
- Source [9] of the v0.2 ADR (a `DataGridView` cell's Name is the column header plus the row index)
  stays **docs-only**: no pilot app has a `DataGridView` (KeePass 2 is SysListView32, HandBrake is
  WPF, Notepad++ is Win32, KeePassXC is Qt), so it cannot be checked until the sample app (#33).

## 2026-11-07 — Turkish search needs NFD diacritic stripping, not only the dotted/dotless i (hasan, #185/#184)

`foldText` in the client folded `İ`/`I`/`ı` to `i` — the subtle half, and right — but left `ş ğ ü ö ç`
alone, so "kullanici" found "Kullanıcı" while "giris" did **not** find "Giriş". Half a folded
keyboard is worse than none: the first success teaches the user to expect the second.
`.replace(/[İIı]/g,'i').normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase()` handles every
case — the five others decompose to a base letter plus a combining mark, while `ı` has no mark to
strip, which is why the explicit replace has to stay and has to come first.

## 2026-11-07 — `eval/` has two different `uia_dump.py` modules, and they collide (hasan)

`eval/apps/trial/uia_dump.py` (5.8 kB, the trial app's AutomationId check) and
`eval/spikes/uia_dump.py` (20.6 kB, the #6 tree dumper) are **different files with the same module
name**, and nothing packages either of them. Each tree is green on its own —
`pytest eval/apps/trial/tests` 12 passed, `pytest eval/spikes` 26 passed — but
**`pytest eval/` from the repo root fails 26 of 38**, because whichever `uia_dump` is imported first
shadows the other in `sys.modules`.

It is invisible today: `testpaths = ["apps/trial/tests"]` means the bare `pytest` never collects
`spikes/`, the documented command is `pytest eval/apps/trial/tests`, and CI runs the trial tests
only. So this is not a regression — but a plain `pytest eval/` looks like 26 real failures, and the
next person to widen `testpaths` or point CI at the whole folder will meet it.

Tracked as **#199**, with the three options (rename one module, `--import-mode=importlib`, or make
both trees packages); the fix touches omer's CI job, which is why it is an issue and not a quiet
change. **Always name the path when
running eval tests**, and treat a batch failure there as this collision until proved otherwise.

## 2026-11-07 — the agent had never actually been per-monitor-v2 DPI aware (hasan, #12)

`docs/agent-rpc.md` and `schemas/snapshot.schema.json` both promise bounds "as UI Automation
reports them to a **per-monitor-v2** DPI aware agent". Measured on this machine: the process was
**per-monitor-v1**, and nothing we wrote had set it.

Three mistakes stacked up, and each one hid the next:

1. `DPI_AWARENESS_CONTEXT` is a **pointer-sized handle**. `user32.SetProcessDpiAwarenessContext(-4)`
   through ctypes' default argument conversion truncates it to 32 bits, so on 64-bit Windows the
   call fails with **`ERROR_INVALID_PARAMETER` (87)**. Declaring `argtypes = [c_void_p]` and passing
   `c_void_p(-4)` makes it succeed.
2. The old code treated **87 the same as 5** (`ERROR_ACCESS_DENIED`, "awareness is already set") and
   logged `INFO  DPI awareness was already set before the backend started`. A malformed call looked
   like a benign one.
3. The very next statement in `setup()` imports pywinauto, **which sets the process to
   per-monitor-v1 itself**. So the process always ended up aware — just not the way the contract
   says — and the log line above was technically true by the time anyone read it.

**`GetAwarenessFromDpiAwarenessContext` cannot tell v1 from v2.** The `DPI_AWARENESS` enum has no
value of its own for v2, so both read as `PER_MONITOR_AWARE` (2). Comparing contexts with
**`AreDpiAwarenessContextsEqual`** is the only way to ask the question, and it is what
`recognition.uia.dpi_awareness()` now does.

**What it did and did not break.** v1 and v2 are both *unscaled*, so every bounds number measured so
far is still right and no stored snapshot is wrong. What v2 adds is per-monitor behaviour for
dialogs and child windows and DPI-scaled non-client areas — i.e. exactly the mixed-DPI case that is
still unmeasured (every number we have is from one 120-DPI display). So this was a latent
contract violation, not a wrong measurement.

**General point: a success log is not evidence.** This one said "already set" for weeks on a call
that had never worked. When an API's outcome is load-bearing for a contract, *read the state back*
and warn when it is not what was promised, rather than inferring it from a return value — which is
what the function does now, and what `test_setup_leaves_the_process_per_monitor_v2` pins in a fresh
interpreter (awareness can be set only once per process, so an in-process test cannot check it).

## 2026-11-07 — one window has three different rectangles, and we were reporting the wrong one (hasan, #16/#184)

Measured on the trial app at 150 % scaling, during the Windows session for #184:

```
Win32 GetWindowRect        472 x 261   <- what listWindows reported
DWM extended frame bounds  456 x 253   <- what a person sees
UIA BoundingRectangle      450 x 213   <- what snapshot reports (per element)
```

- **`GetWindowRect` is 8 px too big on the left, right and bottom.** Since Windows 10 a resizable
  window carries an **invisible** resize border outside its visible frame and `GetWindowRect`
  includes it. (The same effect makes a maximised browser report `[-11, -11, 1931, 1019]` on a
  1920×1080 screen — the negative origin is not a bug in the reader.) The border is DPI-scaled, so
  it is 8 px at 150 % and 11 px elsewhere; never hard-code it.
- **UIA's rectangle is 38 px short at the top**: no title bar. Right for an *element*, wrong for
  "the window".
- **`DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS, …)`** is the only one of the three that
  means "the window as it looks": invisible border out, title bar in.

The user spotted it the way a tester would — the Spy's red frame around a *window* sat outside the
window — while the frame around every *element* was exactly right. So `listWindows` now reports the
DWM rectangle and `docs/agent-rpc.md` says which rectangle it is, and says explicitly that it is
**not** the same as `snapshot`'s `window.bounds`. Both are called `bounds`, which is what let the
difference hide.

**General point: "bounds" is not one concept on Windows.** Any new coordinate consumer (#54's
screenshot crop, #23's win32 fallback, the overlay) has to say which of the three it means.

## 2026-11-08 — `--import-mode=importlib` does not fix duplicate module names (#199)

The two `uia_dump.py` modules under `eval/` (trial app and spikes) shadow each other for a whole
`pytest eval` run. `--import-mode=importlib` looked like the one-line fix and **is not**: measured,
`pytest eval -q --import-mode=importlib` still aborts collection with
`ImportError: cannot import name 'MAX_DEPTH' from 'uia_dump'`. The import mode governs how pytest
imports *test* modules; here the clash is between two *source* modules of the same name imported by
other source modules (`spikes/uia_probe.py`, `spikes/kp_state.py`). What decides the winner is
`apps/trial/tests/conftest.py` doing `sys.path.insert(0, …/apps/trial)`, which lasts for the whole
process, so a `pythonpath` entry for both folders would only re-create the ambiguity. The fix is a
unique module name (now `spikes/uia_tree_dump.py`) or real packages. Rule of thumb: inside one
pytest run, every module name under a tree must be unique, whatever the import mode.

- 2026-11-08 · omer · #208 · **On Windows, `docker compose up` publishes a host port that another program already holds, and says nothing.** hasan's machine had EnterpriseDB's Apache (`PEMHTTPD-x64`, auto-start) on IPv4 8080: the server started, the container's own `/api/health` said UP, and every `http://localhost:8080` request reached Apache (`http://[::1]:8080` reached the server, because Apache listened on IPv4 only) → set `AYNA_SERVER_PORT` in `.env` (Compose publishes `${AYNA_SERVER_PORT:-8080}`), and check who holds a port with `netstat -ano | findstr :8080` before a demo.
- 2026-11-08 · omer · #208 · Spring Boot: an `ApplicationListener<ApplicationFailedEvent>` that is a `@Component` hears about a failed start only if its bean was created before the bean that failed, and in our test it logged its line twice → register it in `META-INF/spring.factories` under `org.springframework.context.ApplicationListener` (once, whichever bean fails). A `FailureAnalyzer` prints a tidier block but logs the original stack trace only at DEBUG.

## 2026-11-08 — Merging `main` into a stacked branch after a squash merge can resurrect deleted files (omer, #186–#197)

After the PR below it is squash-merged, the next branch in a stack still carries the original
commits, so `git merge origin/main` uses an old merge base. Two things go wrong: (1) every line
the lower PR touched and the branch later changed again conflicts, and (2) worse, silently, a file
the branch **deleted** comes back, because relative to the old base `main` "added" it
(`VersionBar.tsx` on #188). What worked: when `main`'s tree equals a commit the branch already
contains (`git rev-parse origin/main^{tree}` = `<prev-branch-tip>^{tree}`), record the merge with
`git merge -s ours origin/main` — the branch's tree is exactly right. Otherwise re-merge each
conflicted file with an explicit base (`git merge-file ours <base> theirs`, base = the lower branch's
version the branch was built on). Always compare the merged tree with what you expect before
pushing, and regenerate `docs/api/openapi.yaml` instead of resolving it by hand.
- 2026-11-10 · omer · git · **GitHub ignores `merge=union`**: after one memory PR merged, the next PR touching `journal.md` showed CONFLICTING on GitHub although `git merge origin/main` locally was clean (#217 after #222). Merging `main` into the branch locally and pushing clears it. `active.md` is overwrite-only, so every open branch of the same person conflicts on it; take `main`'s side while merging a train of PRs and write the final `active.md` on the last branch to merge.
- 2026-11-08 · omer · #51 · **A second Compose stack can run beside the one you are using**, for a smoke test on the real image without stopping it: `docker compose -p <other-name> -f docker-compose.yml -f override.yml up -d --build`, where the override has `ports: !reset []` under `neo4j` and `ports: !override ["28080:8080"]` under `server`. The project name gives it its own containers and volumes; `down -v` with the same `-p` and files removes only those.

## 2026-11-12 — `Invoke` is not enough for a Click (hasan, #221's Windows check, for #40)

Driving HandBrake 1.11.2 (WPF) to open its queue, `IUIAutomationInvokePattern::Invoke` on the
toolbar **Queue** button threw `COMError -2147220992` while a real mouse click on the same
element worked. The element reported the Invoke pattern and was visible and enabled; it simply
refused to be invoked. Earlier in the same session the opposite happened on HandBrake's
"Check for updates?" dialog: `click_input()` left the dialog open and `invoke()` dismissed it.

→ **Playback (#40) cannot implement Click as one call.** Try the pattern, and on a `COMError`
fall back to a real click at the element's centre (and the reverse where a click does not land),
rather than reporting the step as failed. Two of our four pilot apps already disagree about which
one works, so this is the common case, not an edge case. The same applies to any Spy or recorder
action that "presses" something.

## 2026-11-12 — Where a teammate's Windows check gets written down (hasan, #221)

Running someone else's `needs-windows-test` check leaves notes that belong to **three** different
places, and the rules collide: the result is an issue comment, a gotcha belongs here, but the
session's own journal and `active.md` are mine while the branch under test is theirs — and
nothing of mine may be committed on their branch. What works: do the run on their branch, post
the result as an issue comment (that is the durable record and it needs no branch at all), and
put only append-only memory (`learnings.md`, `journal.md`) on a small branch of your own cut from
`main`, where `merge=union` keeps it conflict-free.

→ Do **not** reach for `active.md` for this: it is overwrite-merged, so a third divergent copy on
a third branch is a conflict waiting to happen. It can wait until one of your own PRs merges.
