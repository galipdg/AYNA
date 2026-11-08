# AYNA client wireframes

Draft for the #183 team review. One wireframe per screen of RS §3.5.1, at 1280 × 720. Boxes show layout and words, not exact pixels; colours and components are in [style-guide.md](style-guide.md), the moves between screens in [flows.md](flows.md). Example data comes from the PySide6 trial app (#9).

Legend: `[ Button ]` main action · `[ Button ]` secondary (the text says which) · `▾` menu · `( )` / `(•)` radio · `[ ]` / `[x]` checkbox · `⌕` search field · `›` / `▾` folded / open tree node · `░` disabled or unavailable.

| # | Screen | Requirements | Built in |
|---|---|---|---|
| [0](#0-shell) | Shell: top bar, navigation, agent status | FR-05, FR-38 | #183 |
| [1](#1-server-settings-first-run) | Server settings (first run) | FR-37 | #32 → restyled in #183 |
| [2](#2-log-in) | Log in | FR-39 | #60 → restyled in #183 |
| [3](#3-choose-application) | Choose application | FR-37, FR-38 | #32 → restyled in #183 |
| [4](#4-object-spy) | Object Spy and Add to repository | FR-02, FR-03, FR-06, FR-07 | #24, #25 → layout in #184 |
| [5](#5-repository) | Repository | FR-08, FR-09 | #30 |
| [6](#6-tests-list-and-editor) | Tests: list and editor | FR-11–FR-15 | #38, #39 |
| [7](#7-nl-panel) | NL panel | FR-27, FR-28 | #78 |
| [8](#8-live-run-status) | Live run status | FR-20, FR-35 | #44 |
| [9](#9-runs-history-and-details) | Runs: history and details | FR-21, FR-22 | #59, #68 |
| [10](#10-repairs-healing-approval) | Repairs (healing approval) | FR-31, FR-32 | #75 |
| [11](#11-changes-change-impact) | Changes (change impact) | FR-33, FR-34 | #81 |
| [12](#12-users-and-api-tokens) | Users and API tokens | FR-39 | #60 → restyled in #183 |
| [13](#13-settings) | Settings | FR-37, NFR-17 | #183 |
| [14](#14-unavailable-place) | Unavailable place | — | #183 |

---

## 0 Shell

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ AYNA │ Trial App ▾ │ Version 1.2 ▾ │                        ● Agent ready │ EN ▾ │ omer ▾   │
├──────────────────┬──────────────────────────────────────────────────────────────────────────┤
│ ⌖ Object Spy     │ Object Spy                                                               │
│ ≡ Repository     │ Find the elements of Trial App and save them for tests.                  │
│ ☰ Tests          ├──────────────────────────────────────────────────────────────────────────┤
│ ▶ Runs           │                                                                          │
│ ⚒ Repairs    (2) │                         (work area of the screen)                        │
│ ⇄ Changes  Later │                                                                          │
│                  │                                                                          │
│                  │                                                                          │
│                  │                                                                          │
│ ──────────────── │                                                                          │
│ ⚇ Users          │                                                                          │
│ ⚙ Settings       │                                                                          │
└──────────────────┴──────────────────────────────────────────────────────────────────────────┘
```

**Top bar, left to right**

- **AYNA** — the name; no action.
- **Application menu** `Trial App ▾` — the list of applications with their technology, a search field when there are more than 8, and **Add application…** at the bottom. Choosing one keeps the current place and loads its data.
- **Version menu** `Version 1.2 ▾` — the versions of this application, newest first, and **Add version…** (a small inline field inside the menu: "Version, e.g. 1.3" + `[ Add ]`). This is the only place where the version is chosen; every screen uses it.
  - No version yet: the button reads `+ Add the version you are testing` with `--warning` outline, and screens that need a version say so and point here.
- **Agent pill** — `● Agent ready` / `◌ Agent starting…` / `↻ Agent restarting (2 of 3)` / `✕ Agent not running`. Click: a small panel with the state, the last error in plain words, and `[ Start again ]` when it has failed (FR-05, #17).
- **Language** `TR ▾` — Türkçe / English, each named in its own language (#185). The switch applies at once and is kept across restarts; the same menu sits in the top-right corner of the screens before login. First run: the system language if Turkish or English, else Turkish.
- **User menu** `omer ▾` — "Logged in as omer (Admin) to http://ayna-server:8080", **Log out**.

**Navigation**

- Places in task order: Object Spy, Repository, Tests, Runs, Repairs, Changes. Below a divider: Users (admins only), Settings.
- The current place has `--selected` background and the accent bar. Repairs shows the number of repair suggestions waiting for review.
- Places not built yet are muted with a **Later** pill and open [screen 14](#14-unavailable-place).
- Collapses to icons below 1180 px.

**Page header** — title, one sentence of help, page actions on the right. The help sentence can be hidden per screen ("Hide tip") once the user knows the screen.

---

## 1 Server settings (first run)

No shell before login: a centred card. The same card opens from Settings → Server.

```
                         AYNA
          Codeless UI testing for Windows applications

        ┌──────────────────────────────────────────────┐
        │ Connect to the AYNA server                   │
        │                                              │
        │ Server address                               │
        │ ┌──────────────────────────────────────────┐ │
        │ │ http://ayna-server:8080                  │ │
        │ └──────────────────────────────────────────┘ │
        │ Ask your administrator if you do not know it.│
        │                                              │
        │                          [ Connect ]         │
        └──────────────────────────────────────────────┘
```

- **Error** (under the field, the field keeps its value): "Could not reach http://ayna-serve:8080. Check the address and that the server is running." / "…did not answer within 5 seconds." / "…answered, but it is not an AYNA server." / "The AYNA server at … is running but cannot reach its database."
- **Busy:** `[ Connecting… ]`, field read-only.
- **Opened from Settings:** a `[ Cancel ]` returns to the shell unchanged.

## 2 Log in

```
                         AYNA

        ┌──────────────────────────────────────────────┐
        │ Log in                                       │
        │ to http://ayna-server:8080   Change server   │
        │                                              │
        │ User name                                    │
        │ ┌──────────────────────────────────────────┐ │
        │ │ omer                                     │ │
        │ └──────────────────────────────────────────┘ │
        │ Password                                     │
        │ ┌──────────────────────────────────────────┐ │
        │ │ ••••••••                                 │ │
        │ └──────────────────────────────────────────┘ │
        │                                              │
        │                           [ Log in ]         │
        └──────────────────────────────────────────────┘
```

- **Error** in a panel message above the fields: "Wrong user name or password." The password field is cleared, the user name kept.
- **Session ended later** (F7): the same card as a dialog over the current screen, with "Your session has ended. Log in again." on top; after login the user is back where they were.

## 3 Choose application

First time only as a centred card; later the top bar's application menu does the same.

```
        ┌──────────────────────────────────────────────────────┐
        │ Which application do you test on this computer?      │
        │                                                      │
        │ ⌕ Search applications                                │
        │ ┌──────────────────────────────────────────────────┐ │
        │ │ (•) Trial App                    PySide6 / Qt    │ │
        │ │ ( ) Notepad                      Win32           │ │
        │ │ ( ) Stok Takip                   WinForms        │ │
        │ └──────────────────────────────────────────────────┘ │
        │ + Add an application                                 │
        │                                                      │
        │                                   [ Continue ]       │
        └──────────────────────────────────────────────────────┘

  "+ Add an application" opens inline:
        │ Name                      Technology                 │
        │ ┌──────────────────────┐  ┌───────────────────────┐  │
        │ │ Stok Takip           │  │ WinForms            ▾ │  │
        │ └──────────────────────┘  └───────────────────────┘  │
        │                         [ Cancel ]  [ Add and use ]  │
```

- **Technology** becomes a menu (Win32, WinForms, WPF, Qt, Java, Other) instead of free text.
- **Empty:** "There are no applications on this server yet. Add the first one." with the add form open.
- **The saved one is gone:** panel message "The application you used before is no longer on this server. Choose another."
- **Duplicate name:** field error "Stok Takip already exists. Choose it from the list."

---

## 4 Object Spy

The three-panel layout is built in #184; #183 moves the current Spy into the shell. Below: an element chosen, then Add to repository open in the right panel.

```
│ Object Spy                                         Press Ctrl+Shift+A over an element to pick it │
├────────────────────────┬──────────────────────────────────┬──────────────────────────────────────┤
│ Windows      [Refresh] │ Login — Trial App [Capture again]│ "Kullanıcı adı" text box             │
│ ⌕ Search windows       │ ⌕ Search by name, type or id     │ Text box · in Login — Trial App      │
│ ┌────────────────────┐ │ ▾ Login — Trial App      Window  │                                      │
│ │▌Login — Trial App  │ │   ▾ Giriş                Group   │ How AYNA finds it                    │
│ │  trial_app.exe     │ │     · Kullanıcı adı      Label   │   Label next to it   Kullanıcı adı   │
│ │ Untitled — Notepad │ │    ▌· (Kullanıcı adı)    Text box│   Type               Text box        │
│ │  notepad.exe       │ │     · Şifre              Label   │   Window             Login — Trial … │
│ │ AYNA               │ │     · (Şifre)            Text box│                                      │
│ │  ayna.exe          │ │     · Giriş yap          Button  │ Where it is                          │
│ │                    │ │     · İptal              Button  │   Position  412, 288 · 240 × 24 px   │
│ │                    │ │   › Menu bar             Menu bar│                                      │
│ │                    │ │                                  │ State                                │
│ │                    │ │                                  │   Enabled ✓   Visible ✓              │
│ └────────────────────┘ │ 14 elements · captured 10:42 in  │                                      │
│                        │ 340 ms                           │ ▸ Advanced  AutomationId, class, …   │
│                        │                                  │                                      │
│                        │                                  │         [ Add to repository ]        │
└────────────────────────┴──────────────────────────────────┴──────────────────────────────────────┘
```

```
                                                             ┌──────────────────────────────────────┐
  (left and middle panels stay as they are)                  │ ← Add to repository                  │
                                                             │                                      │
                                                             │ Element name                         │
                                                             │ ┌──────────────────────────────────┐ │
                                                             │ │ login.kullaniciAdiInput          │ │
                                                             │ └──────────────────────────────────┘ │
                                                             │ Tests use this name. Write the       │
                                                             │ screen, a dot, then the element.     │
                                                             │                                      │
                                                             │ AYNA finds it by                     │
                                                             │   ✓ Label next to it: Kullanıcı adı  │
                                                             │   ✓ Type: Text box                   │
                                                             │ If the screen changes, it also tries │
                                                             │ the position in the window.          │
                                                             │ ✓ Only this element matches.         │
                                                             │                                      │
                                                             │ ▸ Advanced  change what AYNA uses    │
                                                             │                                      │
                                                             │ Saved under Trial App · Version 1.2  │
                                                             │              [ Cancel ]  [ Save ]    │
                                                             └──────────────────────────────────────┘
```

- **Left:** windows the agent sees (title, process); search; Refresh. Choosing one captures it.
- **Middle:** the window's element tree; nodes show the element's text and its type in plain words; search filters by name, type or AutomationId; the chosen node stays in view. Footer: capture size and time; a `--warning` line when some properties could not be read.
- **Right:** the chosen element in groups (how it is found, where it is, state); internal fields under Advanced; **Add to repository** replaces the properties in the same panel with a back arrow. When the window itself is chosen, the right panel shows the window's properties.
- **The version** is shown, not chosen: "Saved under Trial App · Version 1.2". With no version, Save is disabled with "Add the version you are testing in the top bar first."
- **States:** agent not running (page message + Start again); not on Windows (page message "The Spy works on Windows only."); no windows ("The agent sees no open windows. Open the application, then Refresh."); window closed; capture took too long; hotkey taken by another program (hint turns `--warning`).

## 5 Repository

```
│ Repository                                                        [ Open Object Spy ]          │
│ Elements of Trial App that tests use by name.                                                  │
├────────────────────────────────┬───────────────────────────────────────────────────────────────┤
│ ⌕ Search saved elements        │ login.kullaniciAdiInput                          [ Rename ]   │
│ 23 elements                    │ Text box · Login — Trial App · Version 1.2                    │
│ ▾ login                    (5) │                                                               │
│  ▌kullaniciAdiInput   2 tests  │ Used by 2 tests                                               │
│   sifreInput          2 tests  │   Login works with valid user · Login rejects empty password  │
│   girisButton         3 tests  │                                                               │
│   iptalButton         0 tests  │ AYNA finds it by                                              │
│   hataLabel           1 test   │   Label next to it   Kullanıcı adı                            │
│ ▸ main                    (12) │   Type               Text box                                 │
│ ▸ stok                     (6) │ Backup                                                        │
│                                │   Position in window 3                                        │
│                                │                                                [ Edit ]       │
│                                │                                                               │
│                                │ Seen in versions   1.2 ✓   1.1 ✓   1.0 –                      │
│                                │                                                               │
│                                │ ▸ Advanced  AutomationId, class, parent path, ids             │
│                                │                                                               │
│                                │                                        [ Remove ]             │
└────────────────────────────────┴───────────────────────────────────────────────────────────────┘
```

- **Left:** saved elements grouped by screen (the part before the dot), each with how many tests use it (FR-08). Search by name, label or type.
- **Right:** details of the chosen element. **Rename** edits the name in place; steps keep working (FR-08). **Edit** turns "Find by / Backup" into the same editor as Add to repository. **Used by** links open each test.
- **Remove** asks for confirmation; when tests still use the element, the server refuses and the message names them (FR-09): "login.girisButton is used by 3 tests: Login works…, … Change those steps first."
- **Empty:** "No saved elements yet. Pick an element in the Object Spy and add it here." `[ Open Object Spy ]`.

## 6 Tests: list and editor

```
│ Tests                                                      [ Import ]  [ + New test ]          │
├──────────────────────────────┬─────────────────────────────────────────────────────────────────┤
│ ⌕ Search tests               │ Login works with valid user                     ✓ Passed 10:51  │
│ ▌Login works with valid user │ [ ▶ Run ]  [ Save ]   Export   Describe in Turkish ▸   Unsaved •│
│  ✓ 10:51 · 6 steps           ├───┬──────────────┬─────────────────────────┬───────────┬────────┤
│  Login rejects empty password│ # │ Action       │ Element                 │ Value     │ Wait up│
│  ✕ yesterday · 4 steps       ├───┼──────────────┼─────────────────────────┼───────────┼────────┤
│  Stock entry adds a row      │⠿1 │ Type text  ▾ │ login.kullaniciAdiInput▾│ admin     │        │
│  – never run · 9 steps       │⠿2 │ Type text  ▾ │ login.sifreInput      ▾ │ ••••••    │        │
│                              │⠿3 │ Click      ▾ │ login.girisButton     ▾ │           │        │
│                              │⠿4 │ Wait for   ▾ │ main.anaMenu          ▾ │           │ 20 s   │
│                              │⠿5 │ Check      ▾ │ main.hosgeldinLabel   ▾ │ Text is  ▾│        │
│                              │   │              │                         │ Hoş geldin│        │
│                              │⠿6 │ Click      ▾ │ ✕ choose an element   ▾ │           │        │
│                              │   │ ✕ Step 6 needs an element.                                  │
│                              │ + Add step                                                      │
└──────────────────────────────┴─────────────────────────────────────────────────────────────────┘
```

- **Left:** tests of this application with their last result, time and step count. Search by name.
- **Editor:** one row per step; drag ⠿ to reorder; `Delete` key or row menu (⋯) to delete, duplicate, insert above. **Action** from a menu (Click, Type text, Choose item, Choose row, Check, Wait for). **Element** from a searchable menu of saved elements grouped by screen, with "Pick in Object Spy…" at the bottom. **Value** depends on the action: text for Type text, item text for Choose item, the row for Choose row (its number, or the text of one of its cells with an optional column; #205), property + comparison + expected value for Check (FR-15; a table's cell, whether a row is listed, or the number of rows take a row, a column or a count, and the element menu then lists only tables and lists), nothing for Wait for (it only waits until the element is ready). **Wait up to** is empty for the default (10 s).
- **Validation:** a wrong step gets a red mark and one line under it with the reason (FR-13); Save and Run stay enabled for valid tests only, with a tooltip naming the first wrong step.
- **Unsaved changes:** a dot next to the title; leaving asks "Save changes to Login works…?".
- **Import / Export:** JSON files via the system file dialog; the user never sees the JSON (FR-14).
- **Empty:** "No tests yet. Create one and add steps, or describe it in Turkish." `[ + New test ]`.

## 7 NL panel

Opened with **Describe in Turkish ▸** in the editor; it takes the right part of the work area, the step table narrows.

```
├──────────────────────────────┬──────────────────────────────────┬──────────────────────────────┤
│ (test list)                  │ (step table, narrower)           │ Describe in Turkish       ✕  │
│                              │                                  │ Screen  login ▾              │
│                              │                                  │ ┌──────────────────────────┐ │
│                              │                                  │ │ Kullanıcı adına admin,   │ │
│                              │                                  │ │ şifreye 1234 yaz ve giriş│ │
│                              │                                  │ │ yap butonuna tıkla.      │ │
│                              │                                  │ └──────────────────────────┘ │
│                              │                                  │           [ Suggest steps ]  │
│                              │                                  │ ──────────────────────────── │
│                              │                                  │ 3 suggested steps            │
│                              │                                  │ [x] Type text · login.kull…  │
│                              │                                  │     "admin"                  │
│                              │                                  │     Why: "kullanıcı adına"   │
│                              │                                  │ [x] Type text · login.sifre… │
│                              │                                  │ [x] Click · login.girisBut…  │
│                              │                                  │ 1 part could not be used:    │
│                              │                                  │   "OK'a bas" — no element    │
│                              │                                  │   fits on this screen.       │
│                              │                                  │ [ Add 3 steps to the test ]  │
└──────────────────────────────┴──────────────────────────────────┴──────────────────────────────┘
```

- Each suggestion can be edited before it is added; nothing is saved until **Add … to the test**; added steps are ordinary steps (FR-27).
- Dropped parts are listed with their reason in plain words (FR-26); the "12-step limit reached" notice appears when the service says so.
- **Busy:** "Writing steps… this can take up to 30 s." with `[ Cancel ]`.
- **AI service unreachable:** the panel shows "The Turkish assistant is not available right now. You can still add steps by hand." and the button is disabled; nothing else in the client changes (FR-28).

## 8 Live run status

The editor during and after a run. Other clients with the same test open see the same (FR-20, NFR-06).

```
│ Login works with valid user                                                                    │
│ ● Running on TEST-PC-03 by omer · step 4 of 6 · 0:07                         [ ■ Stop ]        │
├───┬──────────────┬─────────────────────────┬───────────┬───────────────────────────────────────┤
│ # │ Action       │ Element                 │ Value     │ Result                                │
├───┼──────────────┼─────────────────────────┼───────────┼───────────────────────────────────────┤
│ 1 │ Type text    │ login.kullaniciAdiInput │ admin     │ ✓ 0.4 s                               │
│ 2 │ Type text    │ login.sifreInput        │ ••••••    │ ✓ 0.3 s                               │
│ 3 │ Click        │ login.girisButton       │           │ ✓ 0.2 s                               │
│ 4 │ Wait for     │ main.anaMenu            │           │ ● waiting… 2.1 s of 20 s              │
│ 5 │ Check        │ main.hosgeldinLabel     │ is Hoş ge…│ ·                                     │
│ 6 │ Click        │ main.cikisButton        │           │ ·                                     │
└───┴──────────────┴─────────────────────────┴───────────┴───────────────────────────────────────┘

 After a failure, the run bar becomes:
│ ✕ Failed at step 5 · Check failed: expected "Hoş geldin", got "Hoşgeldin" · [ Run details ]    │
 After a repair suggestion:
│ ! Needs review at step 4 · Element not found · AYNA suggests 3 similar elements · [ Review ]   │
```

- The steps are read-only during the run; the table keeps its place.
- Failure categories in plain words (FR-35); the failing row shows the message under it.
- Steps after a failure or repair suggestion show "– Skipped" (FR-30).

## 9 Runs: history and details

```
│ Runs                                                                                           │
│ Test ⌕ [ all tests        ▾]  Status [ all ▾]  Version [ 1.2 ▾]                                │
├──────────────────────────────────────────┬─────────┬──────────┬───────────┬──────────┬─────────┤
│ Test                                     │ Status  │ Started  │ Duration  │ By       │ Version │
├──────────────────────────────────────────┼─────────┼──────────┼───────────┼──────────┼─────────┤
│▌Login works with valid user              │ ✓ Passed│ 10:51    │    3.8 s  │ omer     │ 1.2     │
│ Login rejects empty password             │ ! Review│ 10:12    │    2.1 s  │ hasan    │ 1.2     │
│ Stock entry adds a row                   │ ✕ Failed│ yesterday│   12.4 s  │ CI       │ 1.2     │
└──────────────────────────────────────────┴─────────┴──────────┴───────────┴──────────┴─────────┘
```

```
│ ← Runs   Stock entry adds a row · ✕ Failed · yesterday 17:20 · 12.4 s · CI                     │
│                                                         [ Open report ]  [ Download report ]   │
├───────────────────────────────────────────────────────┬────────────────────────────────────────┤
│ ✓ 1 Click    main.stokMenu                     0.3 s  │ Step 4 · Check failed                  │
│ ✓ 2 Click    stok.yeniButton                   0.2 s  │ main.toplamLabel: expected "12",       │
│ ✓ 3 Type     stok.miktarInput   "5"            0.4 s  │ got "11"                               │
│▌✕ 4 Check    main.toplamLabel   Text is "12"   0.1 s  │ ┌────────────────────────────────────┐ │
│ – 5 Click    stok.kaydetButton            Skipped     │ │                                    │ │
│                                                       │ │    screenshot after step 4         │ │
│                                                       │ │                                    │ │
│                                                       │ └────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┴────────────────────────────────────────┘
```

- Filters by test, status and version; the version filter starts at the top bar's version and can show all (FR-22).
- Run details: steps on the left, the chosen step's message and screenshot on the right (FR-19). **Open report** opens the HTML report in the system browser; **Download report** saves the one-file report (FR-21).
- **Empty:** "No runs yet. Open a test and press Run."

## 10 Repairs (healing approval)

The Repairs place lists suggestions waiting for review; one opens from a run too.

```
│ Repairs                                                                                         │
│ AYNA could not find an element during a run and suggests similar ones. Nothing changes until    │
│ you choose.                                                                                     │
├──────────────────────────────┬──────────────────────────────────────────────────────────────────┤
│ Waiting (2)  Decided         │ login.girisButton was not found                                  │
│ ▌login.girisButton           │ Step 3 of "Login works with valid user" · run 10:12 · Version 1.3│
│  Login works… · 10:12        │ It was: Button "Giriş yap", next to "Şifre"                      │
│  stok.kaydetButton           │                                                                  │
│  Stock entry… · yesterday    │ Suggested elements                                               │
│                              │ ┌────────────────────┐ ┌────────────────────┐ ┌────────────────┐ │
│                              │ │(•) Button "Oturum  │ │( ) Button "İptal"  │ │( ) Link "Giriş │ │
│                              │ │    aç"             │ │                    │ │    yardımı"    │ │
│                              │ │ Match  86 %        │ │ Match  41 %        │ │ Match  33 %    │ │
│                              │ └────────────────────┘ └────────────────────┘ └────────────────┘ │
│                              │ Why "Oturum aç" matches                                          │
│                              │   Type           ██████████  same                                │
│                              │   Window         ██████████  same                                │
│                              │   Label next to  ████████░░  "Şifre" — same                      │
│                              │   Position       ███████░░░  moved 8 px                          │
│                              │   Text           ███░░░░░░░  "Giriş yap" → "Oturum aç"           │
│                              │ ▸ Advanced  score, weights, raw similarities                     │
│                              │                                                                  │
│                              │  Show on screen     [ None of these ]  [ Use this element ]      │
└──────────────────────────────┴──────────────────────────────────────────────────────────────────┘
```

- Three suggested elements side by side; the chosen one shows its per-property bars, biggest contribution first (FR-31). **Show on screen** outlines it on the running application (and on the run's screenshot when the application is not open).
- **Use this element** asks: "login.girisButton will find Button "Oturum aç" in Version 1.3. Tests that use it will use the new element." → `[ Use this element ]`. Then: "✓ Repository updated. Run the test again?" `[ Run again ]` (FR-32).
- **None of these** keeps the step failed and leaves the repository unchanged.
- **Decided** tab: earlier decisions with who decided and when (FR-40).

## 11 Changes (change impact)

```
│ Changes                                                                                        │
│ Compare Version 1.3 (top bar) with  [ Version 1.2 ▾ ]                    [ Compare ]           │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3 saved elements changed · 5 tests use them · 1 repair waiting                                 │
│                                                                                                │
│ ▾ login.girisButton        Text "Giriş yap" → "Oturum aç"                                      │
│     Tests: Login works with valid user · Login rejects empty password                          │
│     Repair waiting: Review                                                                     │
│ ▾ stok.miktarInput         Moved 40 px down                                                    │
│     Tests: Stock entry adds a row                                                              │
│ ▸ main.hosgeldinLabel      No longer found in 1.3                                              │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- The first version is the top bar's; the screen only chooses the version to compare with (FR-34). Each test and repair is a link.
- **Empty result:** "No saved element changed between 1.2 and 1.3."
- **Only one version:** "Add a second version in the top bar to compare."

## 12 Users and API tokens

Admins only. Testers do not see the place.

```
│ Users                                                                     [ + Add user ]       │
│ Accounts that can log in to this server.                                                       │
├──────────────────────────────────────────────────┬─────────────────────────────────────────────┤
│ ⌕ Search users                                   │ hasan                                       │
│ Name           Role        Since                 │ Tester · since 31 Oct 2026                  │
│ omer (you)     Admin       31 Oct 2026           │                                             │
│▌hasan          Tester      31 Oct 2026           │ Role   ( ) Admin  (•) Tester                │
│ galip          Tester      31 Oct 2026           │                                             │
│ ci-jenkins     Tester      1 Nov 2026            │ [ Set password ]                            │
│                                                  │                                             │
│                                                  │ API tokens (for CI)                         │
│                                                  │   No API tokens yet.   [ Create token ]     │
│                                                  │                                             │
│                                                  │                         [ Remove user ]     │
└──────────────────────────────────────────────────┴─────────────────────────────────────────────┘
```

- Add user opens in the right panel (name, role, password with its rule as a hint).
- A CI service account is an ordinary tester account with API tokens (ADR accounts and tokens); the list shows a small "API token" mark next to such accounts.
- A new token is shown once in a read-only field with "Select and copy it now; it will not be shown again." and `[ Done ]`.
- Remove and Revoke confirm in a dialog that names the user or token.

## 13 Settings

```
│ Settings                                                                                       │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Server        http://ayna-server:8080 · connected                    [ Change server ]         │
│ Language      [ Türkçe ] [ English ]                                 (#185)                    │
│ Pick hotkey   Ctrl+Shift+A                                                                     │
│ Agent         ● Ready · Python 3.12 · agent 0.1                      [ Restart agent ]         │
│                                                                                                │
│ ▸ About AYNA   client 0.1.0 · Electron 45 · Chromium · Node · Windows 11                       │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- Replaces today's "Runtime" card, which moves under About.
- Change server opens [screen 1](#1-server-settings-first-run) with Cancel.

## 14 Unavailable place

```
│ Changes                                                                          Later         │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                │
│                      Compare two versions of the application and see                           │
│                       which saved elements and tests the new build affects.                    │
│                                                                                                │
│                               This screen comes in a later version (#81).                      │
│                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Shown for every navigation place whose issue has not been built, so the advisor and the team see the whole product from the first demo.
