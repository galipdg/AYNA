# AYNA — Reference scenarios and requirements

| | |
|---|---|
| Issue | #34 — reference scenarios and functional requirements |
| Status | Draft for team review, 2026-10-27 |
| Builds on | Use cases `UC-01`–`UC-16`, roles `ROLE-n` and constraints `CON-nn` from `docs/requirements-workshop.md` (#19, PR #138, a draft awaiting the advisor) · ID conventions, statement form and attributes from RS §1.5 in `docs/rs/RS.md` (#27, PR #137) |
| Goes into the RS (#35) | §3.1 scenario summary · §3.2 FR tables · §3.3–§3.8 NFR tables · §5 traceability · Appendix C (this file's scenarios in full) · Appendix E (the TBDs in §8) |

## 1. How to read this file

- **IDs** follow RS §1.5: `SC-xx`, `FR-xx`, `NFR-xx`, flat and two-digit, never reused or renumbered. A dropped item stays in its table, marked _Deleted_ with the reason. `UC-xx`, `ROLE-n` and `CON-nn` are the workshop's IDs; C1–C4, RQ1–RQ5, H1–H3, G0–G4 and D1–D7 are the plan's. `#nn` is an issue.
- **Scenarios** are written as Given / When / Then (And continues the line above). Each one names its use cases, the application under test (§2) and its kind: _main_ (the use case's main flow), _negative_ (an error or a rejected input) or _edge_ (a boundary condition).
- **Logical names** such as `login.userNameInput` follow the `screen.element` convention. They are examples until the sample app (#33) exists; #33 may rename them, and only the names change, not the scenarios.
- **Requirements** use the RS statement form ("The ‹component› shall …"). Columns: **Priority** is MoSCoW tied to the plan: _Must_ is semester-1 core that the plan never cuts, plus closed-network operation; _Should_ is semester 1 but on the plan's cut list (change-impact view, NL chat panel, rule-based triage, CLI runner and JUnit XML); _Could_ is semester 1 only if time allows; _Won't (S1)_ is semester 2 or later. **Source** is where the requirement comes from. **Verification** is T (test), D (demonstration), I (inspection) or A (analysis in `eval/`), with the planned evidence. FR rows list the **Scenarios** that exercise them; NFR rows name scenarios in the Verification column where a scenario is the evidence.
- **"(proposed, to confirm)"** marks a number the team proposes here; it is not yet in the plan or an issue. All of them are listed in §8 with an owner.
- **One place per item.** This file holds the scenarios. When #35 writes the RS, it moves the FR and NFR tables (§5, §6) into `docs/rs/RS.md` §3.2–§3.8 and leaves a pointer here, so each requirement is kept in one place.

## 2. Applications under test

| Code | Application | What it is | Status |
|---|---|---|---|
| SA | Sample app v1.0 | PySide6 app with six screens: login, list with a grid, detail form, settings with tabs, dialog, wizard. Every control has an AutomationId; the version is shown in the title bar | Planned: #33, week 4 |
| SA-C | Controlled-change versions of the sample app | One UI change each: rename, move, retype, re-parent, AutomationId removed, plus one combined. Each comes with a ground-truth mapping from old to new element | Planned: #46, week 6 |
| SA-B | Bug-injected versions of the sample app | One functional bug each: wrong label, disabled button, wrong saved value, missing validation, wrong navigation | Planned: #47, week 6 |
| P1, P2 | Pilot apps | Open-source Windows apps on UI technologies other than the sample app's (default: WinForms, WPF; D1) | **TBD-1**: chosen in D1 (#21) from the UIA dumps of #6 |

**Sample-app behaviour these scenarios assume** (input for #33; anything #33 builds differently changes only the scenario text):

- Login screen: user-name field, password field, remember-me check box, login button and status label. `admin` / `admin` shows a welcome text that contains the user name; a wrong password shows an error text (as in the trial app, #9).
- List screen: search field, search button, results grid, Open button. After a search, the grid fills about 3 s later and the Open button is enabled only then; the delay is configurable (SC-18).
- Detail form: at least a name field, a combo box, Save and Back, and one validation rule (a required field) that the "missing validation" bug removes (SC-34). Leaving an edited form asks "discard changes?" in a modal dialog (SC-22).
- Settings: several tabs, one of them with an e-mail-notifications check box (SC-16).
- Wizard: three pages (a name field; a department combo box whose items have Turkish text such as "Kalite Güvence"; a summary label) with Next, Back and Finish. Finish opens a confirmation dialog with Yes and No (SC-20).

## 3. Scenario summary

| ID | Title | UC | AUT | Kind |
|---|---|---|---|---|
| SC-01 | First run: connect, choose the application, add a version | UC-01 | — | main |
| SC-02 | Wrong server URL | UC-01 | — | negative |
| SC-03 | Accounts, roles and who did what | UC-15 | SA | main |
| SC-04 | Pick an element with the hotkey and highlight it from the tree | UC-02 | SA | main |
| SC-05 | Pick at 150 % display scaling | UC-02 | SA | edge |
| SC-06 | Inspect a pilot app built on another UI technology | UC-02 | P1 | main |
| SC-07 | win32 fallback for a control UI Automation cannot identify | UC-02 | P2 | edge |
| SC-08 | Agent crash and automatic restart | UC-02, UC-09 | SA | edge |
| SC-09 | Capture a window snapshot | UC-05 | SA | main |
| SC-10 | Add an element to the repository | UC-03 | SA | main |
| SC-11 | Duplicate or malformed logical name refused | UC-03 | SA | negative |
| SC-12 | Rename and edit an object that tests use | UC-04 | SA | main |
| SC-13 | Deleting an object that tests use is refused | UC-04 | SA | negative |
| SC-14 | Build the login test without typing JSON | UC-06, UC-07 | SA | main |
| SC-15 | Invalid steps are highlighted and refused | UC-06 | SA | negative |
| SC-16 | Checkpoint on a settings tab | UC-07 | SA | main |
| SC-17 | Run the login test and watch it live | UC-09 | SA | main |
| SC-18 | Smart wait for a control that appears late | UC-09 | SA | edge |
| SC-19 | A control that never becomes ready times out | UC-09, UC-11 | SA-B | negative |
| SC-20 | Wizard with Select and a confirmation dialog | UC-06, UC-09 | SA | main |
| SC-21 | A checkpoint catches a wrong label | UC-07, UC-09, UC-11 | SA-B | negative |
| SC-22 | An unexpected window interrupts the run | UC-09, UC-11 | SA | negative |
| SC-23 | Repeatable playback on the pilot apps | UC-09 | P1, P2 | main |
| SC-24 | Run report and run history | UC-10 | SA, SA-B | main |
| SC-25 | Failure categories and the decision log | UC-11 | SA, SA-B | main |
| SC-26 | Turkish description to approved steps | UC-08 | SA | main |
| SC-27 | The validator drops an unknown object and an unknown keyword | UC-08 | SA | negative |
| SC-28 | The AI service is down | UC-08, UC-09 | SA | negative |
| SC-29 | Element not found: the step ends as "repair proposed" | UC-09, UC-12 | SA-C | main |
| SC-30 | Approving a proposal repairs the repository and the next run passes | UC-12 | SA-C | main |
| SC-31 | Rejecting all candidates keeps a real bug visible | UC-12 | SA-B | negative |
| SC-32 | Change impact between two versions | UC-05, UC-13 | SA, SA-C | main |
| SC-33 | CLI run against the server with JUnit XML | UC-14 | SA | main |
| SC-34 | CLI run from a file fails the CI job on a bug-injected build | UC-14 | SA-B | negative |
| SC-35 | Install on a clean offline Windows machine | UC-16 | — | main |
| SC-36 | The whole chain with the network off | UC-08, UC-09, UC-10, UC-12, UC-16 | SA, SA-C | main |

## 4. Scenarios

### 4.1 Setup, connection and accounts

#### SC-01 · First run: connect, choose the application, add a version
UC-01 · AUT: — (client and server only) · main
- **Given** a newly installed client that has never connected, and an AYNA server on the closed network on which the application "AYNA Sample" has version 1.0
- **When** the test engineer enters the server's URL on the first-run screen, chooses "AYNA Sample" and adds version 1.1
- **Then** the client connects and shows versions 1.0 and 1.1 of "AYNA Sample", with 1.1 selected
- **And** after the client is closed and started again, it connects to the same server with "AYNA Sample" 1.1 selected, without asking
- **And** adding version 1.1 a second time is refused as a duplicate, and each version is still listed once

#### SC-02 · Wrong server URL
UC-01 · AUT: — · negative
- **Given** a newly installed client
- **When** the test engineer enters a URL where no AYNA server answers (a mistyped host name)
- **Then** the client shows an error that names the URL and says that no AYNA server answered there
- **And** it stays on the first-run screen and saves nothing
- **And** when the engineer corrects the URL, the client connects as in SC-01

#### SC-03 · Accounts, roles and who did what
UC-15 · AUT: SA · main
- **Given** a server with one admin account, and the login test of SC-14
- **When** the admin creates the account "ayse" with the role tester, and ayse logs in, changes a step of the login test and runs it
- **Then** the server stores ayse's user id with the edit and with the run, and the run list shows ayse as the user who ran it
- **And** when ayse opens user management, the client refuses with a message that only admins manage users, and the server refuses the same request sent directly to its API
- **And** ayse's password is stored as a bcrypt hash, not as the password itself

### 4.2 Object Spy and snapshots

#### SC-04 · Pick an element with the hotkey and highlight it from the tree
UC-02 · AUT: SA, login screen · main
- **Given** the sample app on its login screen, and the Object Spy open on the login window
- **When** the test author points the mouse at the user-name field and presses the pick hotkey
- **Then** within 300 ms the field is outlined on screen and selected in the element tree
- **And** the property panel shows every descriptor field: AutomationId, Name, ControlType, ClassName, FrameworkId, parent path, index in parent, nearest label (the user-name caption), enabled, offscreen and bounds
- **When** the author then selects the login button in the element tree
- **Then** a rectangle is drawn around the login button on screen

#### SC-05 · Pick at 150 % display scaling
UC-02 · AUT: SA, detail form · edge
- **Given** Windows display scaling set to 150 %, and the sample app on its detail form
- **When** the author picks 10 different controls of the form with the hotkey, one after the other
- **Then** each pick returns the control under the cursor (10 of 10), and each outline lies on the control's visible edges
- **And** the same 10 picks are correct at 100 % scaling

#### SC-06 · Inspect a pilot app built on another UI technology
UC-02 · AUT: P1 · main
- **Given** pilot app P1 running (chosen in D1, #21; not built with Qt), and the Spy open on its main window
- **When** the author picks each standard control of that window: text box, button, check box, combo box, list, tab and menu item, where present
- **Then** each pick returns a descriptor with ControlType, bounds and at least one identifying property (AutomationId, Name or nearest label), shown in the property panel
- **And** a control with none of these identifying properties is shown with those fields empty, so RQ1 (#64) can count it as unrecognised

#### SC-07 · win32 fallback for a control UI Automation cannot identify
UC-02 · AUT: P2 (or another WinForms or legacy app if neither pilot has such a control, #23) · edge
- **Given** a control in pilot app P2 for which UI Automation gives neither an AutomationId nor a Name
- **When** the author picks it with the hotkey
- **Then** the agent reads the same control through the win32 backend, and the descriptor shows the win32 properties (for example class name, control id and text), each marked as coming from win32
- **And** the author can add the control to the repository with those properties as its primary properties, as in SC-10

#### SC-08 · Agent crash and automatic restart
UC-02, UC-09 · AUT: SA · edge
- **Given** the client running with its local agent connected (status "connected")
- **When** the agent process is ended from Task Manager
- **Then** the status changes to "restarting", the client starts the agent again, the status returns to "connected", and the Spy picks elements again
- **When** the agent fails to start three times in a row (for example, its executable has been removed)
- **Then** the client stops trying, and the status shows "failed" with the reason
- **And** when the client is closed, no agent process is left running

#### SC-09 · Capture a window snapshot
UC-05 · AUT: SA, list screen · main
- **Given** the sample app on its list screen, and version 1.0 of "AYNA Sample" registered on the server
- **When** the test engineer captures a snapshot of the list window
- **Then** within 2 s the agent exports the window's whole element tree as one snapshot that validates against the snapshot schema
- **And** the server stores it under version 1.0 with the same number of elements as the snapshot file
- **And** importing the same snapshot again leaves the number of elements unchanged

### 4.3 Object repository

#### SC-10 · Add an element to the repository
UC-03 · AUT: SA, login screen · main
- **Given** the user-name field picked in the Spy (SC-04), with version 1.0 selected
- **When** the author chooses "Add to repository", enters the logical name `login.userNameInput`, keeps AutomationId as the primary property, adds Name, ControlType and nearest label as fallback properties, and saves
- **Then** the repository object `login.userNameInput` is stored and linked to the picked element for version 1.0
- **And** it appears in the repository view and in the editor's object picker

#### SC-11 · Duplicate or malformed logical name refused
UC-03 · AUT: SA, login screen · negative
- **Given** `login.userNameInput` already exists in "AYNA Sample"
- **When** the author tries to add the password field under the name `login.userNameInput`
- **Then** saving is refused with a message that names the existing object, and nothing is stored
- **And** a name that is not of the form `screen.element` (for example `Login Button`) is refused with a message that shows the expected form

#### SC-12 · Rename and edit an object that tests use
UC-04 · AUT: SA · main
- **Given** `main.searchInput` is the target of steps in 3 tests
- **When** the test engineer searches the repository view for "search", renames the object to `main.customerSearchInput` and adds Name as a fallback property
- **Then** the change is stored, and the view shows that 3 tests use the object
- **And** the 3 tests show the new name in their steps without being edited, and still pass on version 1.0

#### SC-13 · Deleting an object that tests use is refused
UC-04 · AUT: SA · negative
- **Given** `main.searchButton` is the target of steps in 2 tests, and `settings.themeCombo` is the target of none
- **When** the engineer deletes `main.searchButton`
- **Then** the deletion is refused with a message that names the 2 tests, and the object is unchanged
- **When** the engineer deletes `settings.themeCombo`
- **Then** it is removed from the repository

### 4.4 Test authoring and checkpoints

#### SC-14 · Build the login test without typing JSON
UC-06, UC-07 · AUT: SA, login screen · main
- **Given** repository objects for the login screen's user-name field, password field, login button and status label
- **When** the author creates the test "Login succeeds" in the editor and, choosing each keyword from the list and each target from the object picker, adds: Type `login.userNameInput` "admin"; Type `login.passwordInput` "admin"; Click `login.loginButton`; Verify `login.statusLabel` name contains "admin"
- **And** drags the Click step, which was added first by mistake, below the two Type steps, and saves
- **Then** the test is saved, and when it is closed and opened again it shows the same four steps in the same order
- **And** the exported JSON validates against the step schema and holds logical names only, no coordinates
- **And** importing the exported file as a new test gives identical steps

#### SC-15 · Invalid steps are highlighted and refused
UC-06 · AUT: SA · negative
- **Given** the login test open in the editor
- **When** the author adds a Select step with no value and a Verify step with no checkpoint, and tries to save
- **Then** both steps are highlighted, each with its reason (a Select step needs a value; a Verify step needs a checkpoint), and the test is not saved
- **And** when the same steps are sent to the server's tests API directly, the server rejects them with HTTP 400 and the path of each failing field

#### SC-16 · Checkpoint on a settings tab
UC-07 · AUT: SA, settings screen · main
- **Given** the sample app on its settings screen, where the e-mail-notifications check box on the Notifications tab is cleared
- **When** the author builds and runs: Click `settings.notificationsTab`; Click `settings.emailNotificationsCheck`; Verify `settings.emailNotificationsCheck` checked equals true
- **Then** all three steps pass
- **When** the expected value of the Verify step is changed to false and the test is run again
- **Then** the Verify step fails, and its result shows expected false and actual true

### 4.5 Playback

#### SC-17 · Run the login test and watch it live
UC-09 · AUT: SA, login screen · main
- **Given** the login test of SC-14, the sample app on its login screen, and a second client (on another test machine) with the same test open
- **When** the author presses Run
- **Then** each step's status appears live, in order, in the author's client and in the second client
- **And** each step result carries a PNG of the sample app's window taken after the step
- **And** the run and its four step results are stored on the server, and the run passes

#### SC-18 · Smart wait for a control that appears late
UC-09 · AUT: SA, list screen · edge
- **Given** the list screen, which fills its grid about 3 s after a search and enables its Open button only then
- **And** the test: Type `main.searchInput` "Yılmaz"; Click `main.searchButton`; Click `main.openButton`, with the default timeout
- **When** the test is run
- **Then** the agent waits until `main.openButton` exists, is visible and is enabled, then clicks it, and the step passes
- **And** the step's duration shows the wait of about 3 s, and the test contains no fixed sleep

#### SC-19 · A control that never becomes ready times out
UC-09, UC-11 · AUT: SA-B, "disabled button" version · negative
- **Given** the bug-injected version in which the detail form's Save button stays disabled
- **And** a test that changes a field on the detail form and then has Click `detail.saveButton` with `timeoutMs` 5000
- **When** the test is run
- **Then** the Click step fails after about 5 000 ms with a message that names `detail.saveButton`, the 5 000 ms waited and the condition that was not met (enabled)
- **And** the step's category is "timeout", the remaining steps are not run, and the run fails

#### SC-20 · Wizard with Select and a confirmation dialog
UC-06, UC-09 · AUT: SA, wizard and dialog · main
- **Given** the sample app's wizard (§2) and an empty test in the editor
- **When** the author builds and runs: Type `wizard.nameInput` "Ayşe Çelik"; Click `wizard.nextButton`; Select `wizard.departmentCombo` "Kalite Güvence"; Click `wizard.nextButton`; Verify `wizard.summaryLabel` name contains "Kalite Güvence"; Click `wizard.finishButton`; Click `confirmDialog.yesButton`
- **Then** Select chooses the item by its text, the Yes button is found in the newly opened dialog window, and every step passes
- **And** the Turkish characters in the values appear unchanged in the app, in the step results and in the report

#### SC-21 · A checkpoint catches a wrong label
UC-07, UC-09, UC-11 · AUT: SA-B, "wrong label" version · negative
- **Given** the login test of SC-14, and the bug-injected version that shows a wrong text in the login status label
- **When** the test is run
- **Then** the Verify step fails, and its result shows the expected and the actual text
- **And** the step's category is "assertion failed", no healing proposal is made (the element was found), and the run fails

#### SC-22 · An unexpected window interrupts the run
UC-09, UC-11 · AUT: SA, detail form · negative
- **Given** a test that changes the name field on the detail form, clicks Back without saving and then types into `main.searchInput`
- **And** the sample app asks "discard changes?" in a modal dialog when the user leaves an edited form
- **When** the test is run
- **Then** the step after Back fails because the list screen is not reached; its category is "unexpected window", and its result names the dialog's title
- **And** the agent clicks nothing in the dialog, and the run fails

#### SC-23 · Repeatable playback on the pilot apps
UC-09 · AUT: P1, P2 · main
- **Given** pilot app P1, repository objects for at least 5 of its controls, and a 5-step test built in the editor with Type, Select, Click and Verify
- **When** the test is run 10 times in a row, with the app returned to the same start state before each run
- **Then** all 10 runs pass with the same step results, with no manual fix between runs
- **And** the same holds for a 5-step test on pilot app P2

### 4.6 Reports and failure triage

#### SC-24 · Run report and run history
UC-10 · AUT: SA, SA-B · main
- **Given** three runs of the login test: two passed on version 1.0, and one failed on the "wrong label" version (SC-21)
- **When** the test engineer opens the run list, filters it by the login test and status failed, and opens the run
- **Then** the list shows each run's status, duration and the user who ran it, and the filter leaves only the failed run
- **And** the run's HTML report shows a summary, a step table with status, duration and error, and the screenshot of every step
- **And** the report, downloaded as one file, opens in a browser on a machine with the network off, with every screenshot visible

#### SC-25 · Failure categories and the decision log
UC-11 · AUT: SA, SA-B · main
- **Given** the failed runs of SC-19 (timeout), SC-21 (assertion failed), SC-22 (unexpected window) and SC-31 (element not found)
- **When** the test engineer opens each failed step and then exports the decision log
- **Then** every failed step shows exactly one category, the one its scenario names
- **And** the export is a JSONL file with one record per decision, each holding the step, the category, the logical name, the window title and the error message, ready to be labelled for semester 2

### 4.7 Turkish NL assistant

#### SC-26 · Turkish description to approved steps
UC-08 · AUT: SA, login screen · main
- **Given** the repository objects of the login screen, the AI service running, and an empty test open in the editor with the sample app on its login screen
- **When** the author types in the NL panel: "Kullanıcı adına admin yaz, şifreye admin yaz, Giriş'e tıkla, hoş geldin mesajının göründüğünü kontrol et"
- **Then** the panel shows suggested steps — Type `login.userNameInput` "admin", Type `login.passwordInput` "admin", Click `login.loginButton` and a Verify step on `login.statusLabel` — each with a short reason, and every target is an object in the repository
- **And** nothing has been added to the test yet
- **When** the author edits the Verify step's expected value, accepts the steps one by one and saves
- **Then** the test holds exactly the accepted steps, as ordinary steps, and it passes when run as in SC-17

#### SC-27 · The validator drops an unknown object and an unknown keyword
UC-08 · AUT: SA, login screen · negative
- **Given** a repository with no object for a "forgot password" link
- **When** the author types "Şifremi unuttum bağlantısına çift tıkla"
- **Then** no suggested step targets an object outside the repository or uses a keyword other than Click, Type, Select, Verify and Wait
- **And** the panel says that the description could not be turned into valid steps, with the reason (unknown object, unknown keyword)
- **And** in the AI service's automated test, a stub model that returns the keyword `DoubleClick` and the target `login.forgotPasswordLink` yields no suggested step and two dropped steps, each with its reason

#### SC-28 · The AI service is down
UC-08, UC-09 · AUT: SA · negative
- **Given** the AI service stopped, with the server, the client and the agent running
- **When** the author opens the NL panel
- **Then** the panel is disabled with a message that the AI service cannot be reached
- **And** the author can still pick an element in the Spy, add it to the repository, build the login test in the editor, run it and open its report, and the run passes

### 4.8 Self-healing

#### SC-29 · Element not found: the step ends as "repair proposed"
UC-09, UC-12 · AUT: SA-C · main
- **Given** the login test passing on version 1.0, and a controlled-change version (#46) in which none of `login.loginButton`'s primary or fallback properties match any longer
- **When** the test is run on the controlled-change version
- **Then** after the wait, the step Click `login.loginButton` ends as "repair proposed" with the 3 best candidate elements, each with its score and each property's contribution to that score, and the contributions add up to the score
- **And** the candidates are computed in under 1 s
- **And** the agent clicks none of the candidates, the remaining steps are not run, the run does not pass, and the proposal is stored on the server

#### SC-30 · Approving a proposal repairs the repository and the next run passes
UC-12 · AUT: SA-C · main
- **Given** the proposal of SC-29, with the true login button (ground truth of #46) among its candidates
- **When** the healing reviewer opens the proposal from the run report, selects that candidate — which is then outlined on the sample app's window — and approves it
- **Then** `login.loginButton` resolves to that element for the controlled-change version, and a rule linked to the proposal is stored with the reviewer's user id and the time
- **And** when the login test is run again on the same version, it passes, and no step of the test was edited

#### SC-31 · Rejecting all candidates keeps a real bug visible
UC-12 · AUT: SA-B, "wrong navigation" version · negative
- **Given** a test that logs in and then clicks `main.searchButton`, and the bug-injected version in which logging in opens the wrong screen
- **When** the test is run
- **Then** `main.searchButton` is not found, and the step ends as "repair proposed" with candidates from the wrong screen
- **When** the reviewer rejects all candidates
- **Then** the step stays failed with the category "element not found", the repository and the rule book are unchanged, and the run counts as failed
- **And** the decision is logged. An automatically applied repair could have clicked a candidate and passed: this is the false pass that RQ5 measures (#86)

### 4.9 Change impact

#### SC-32 · Change impact between two versions
UC-05, UC-13 · AUT: SA, SA-C · main
- **Given** snapshots of version 1.0 and of a controlled-change version (captured as in SC-09), the reference tests of the sample app, and the pending healing proposal of SC-29
- **When** the test engineer chooses version 1.0 and the controlled-change version in the change-impact view
- **Then** the view lists the repository objects whose element changed, the tests that use them and the pending proposal, and the list of tests equals the ground truth of #46 exactly
- **And** each listed test links to that test in the editor
- **And** choosing the same version on both sides lists no change

### 4.10 Continuous integration

#### SC-33 · CLI run against the server with JUnit XML
UC-14 · AUT: SA · main
- **Given** a suite "smoke" of three tests on the server, and a Windows CI runner that has started version 1.0 of the sample app
- **When** the pipeline runs `ayna run --server URL --suite smoke --junit out.xml`
- **Then** the headless agent runs the three tests without the client, and the command exits with 0
- **And** `out.xml` validates against the JUnit schema with three passed test cases, and the CI system's test reporter shows them
- **And** the three runs appear in the server's run list

#### SC-34 · CLI run from a file fails the CI job on a bug-injected build
UC-14 · AUT: SA-B, "missing validation" version · negative
- **Given** a suite that includes a test of the detail form's required field, exported as `suite.json` (export as in SC-14), and a CI job that starts the "missing validation" version, with no AYNA server
- **When** the job runs `ayna run --from-file suite.json --junit out.xml`
- **Then** the test of the required field fails, the command exits with 1, and the CI job fails
- **And** `out.xml` lists that test case as failed, with the failing step's message

### 4.11 Installation and closed network

#### SC-35 · Install on a clean offline Windows machine
UC-16 · AUT: — · main
- **Given** a clean Windows virtual machine with no development tools and no access outside the closed network, and an internal host with Docker
- **When** the administrator loads the offline backend bundle on the internal host and starts it with one `docker compose up`, runs the AYNA installer on the Windows machine and points the client at the server
- **Then** the client starts, starts its agent and connects to the server
- **And** after AYNA is uninstalled, no AYNA process is left running

#### SC-36 · The whole chain with the network off
UC-08, UC-09, UC-10, UC-12, UC-16 · AUT: SA, SA-C · main
- **Given** the installation of SC-35, the closed network cut off from every outside network, and a firewall that logs outbound connection attempts
- **When** the author builds a test from a Turkish description (SC-26), runs it (SC-17), runs it on a controlled-change version and approves the healing proposal (SC-29, SC-30), and opens the report (SC-24)
- **Then** every step succeeds as in the scenarios it refers to
- **And** the firewall log shows no connection attempt from any AYNA component to a host outside the closed network

## 5. Functional requirements

Grouped as in RS §3.2. Every FR lists at least one scenario.

### 5.1 Object recognition and Object Spy (RS §3.2.1)

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-01 | The agent shall return, for a given screen point, the element under it with its descriptor (AutomationId, Name, ControlType, ClassName, FrameworkId, parent path, index in parent, nearest label, enabled, offscreen) and its screen bounds. | Must | UC-02; Core 1; #11, #22 | T — Windows test (#22) | SC-04, SC-05, SC-06 |
| FR-02 | The client's Object Spy shall show the element tree of a chosen window and every descriptor field of the selected element, outline the selected element on screen, and select the element under the mouse cursor when the user presses the global pick hotkey. | Must | UC-02; #24 | D — weekly Windows session | SC-04, SC-05, SC-06 |
| FR-03 | When UI Automation gives an element neither an AutomationId nor a Name, the agent shall read the same element through the win32 backend and add the win32 properties to its descriptor, each marked with its source. | Must | UC-02; Core 1; #23 | T — Windows test (#23) | SC-07 |
| FR-04 | The system shall capture a window's whole element subtree as one snapshot that validates against `schemas/snapshot.schema.json` and store it as Window and Element nodes under an application version; importing the same snapshot id again shall leave the graph unchanged. | Must | UC-05; #12, #15 | T — agent test, server integration test | SC-09, SC-32 |
| FR-05 | The client shall start the local agent when it starts and stop it when it quits, restart it automatically up to 3 times after an unexpected exit, and show its status as connected, restarting or failed. | Must | UC-02, UC-09; CON-07; #17 | T + D | SC-08 |

### 5.2 Object repository (RS §3.2.2)

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-06 | The system shall let the user add a picked element to the repository under a logical name of the form `screen.element`, with primary and fallback property sets the user can edit before saving, and shall link the new repository object to that element for the current application version. | Must | UC-03; Core 2; #25 | T + D | SC-07, SC-10, SC-11 |
| FR-07 | The server shall reject a logical name that already exists in the same application, with a message that names the existing object. | Must | UC-03; #25 | T | SC-11 |
| FR-08 | The client's repository view shall let the user search, rename and edit repository objects, and shall show for each object the number of tests that use it, computed from the graph. | Must | UC-04; #30 | T + D | SC-12, SC-13 |
| FR-09 | The server shall refuse to delete a repository object that any test step targets, and the refusal shall name those tests. | Must | UC-04; #30 | T | SC-13 |
| FR-10 | The agent shall locate a step's target by the repository object's primary properties and, when they match no element, by its fallback properties; a test shall refer to its targets only by logical name, never by coordinates or raw UI Automation properties. | Must | UC-09; Core 2; #26; step schema (#13) | T | SC-12, SC-14, SC-17, SC-29 |

### 5.3 Test authoring: steps and codeless editor (RS §3.2.3)

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-11 | The system shall store every test as an ordered list of steps that validates against the versioned step schema (`schemas/step.schema.json`), whose keywords are Click, Type, Select, Verify and Wait. | Must | UC-06; Core 3; #13 | T + I | SC-14, SC-20, SC-26 |
| FR-12 | The client's editor shall let the user create a test and add, delete, edit and drag to reorder its steps, choosing each keyword from a list and each target from the repository, without typing JSON. | Must | UC-06; #38 | D | SC-14, SC-20 |
| FR-13 | The client shall highlight a step that does not validate against the step schema, with the reason, and the server shall reject such a step with HTTP 400 and the path of the failing field. | Must | UC-06; #38, #39 | T | SC-15 |
| FR-14 | The system shall export a test as a JSON file and import such a file; an export followed by an import shall give an identical test. | Must | UC-06, UC-14; #39 | T | SC-14, SC-34 |
| FR-15 | The system shall let the user add a Verify step with a property (name, value, enabled, visible, checked, selected), an operator (equals, notEquals, contains) and an expected value; the agent shall pass or fail the step on that comparison and, on failure, report the expected and the actual value. | Must | UC-07; Core 4; #13, #40 | T | SC-14, SC-16, SC-21 |

### 5.4 Playback, smart waits and checkpoints (RS §3.2.4)

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-16 | Before acting on a step, the agent shall wait until the target element exists, is visible and is enabled, for at most the step's `timeoutMs` or else the run's default timeout, by polling and never by a fixed sleep. | Must | UC-09; Core 4; #40 | T — includes a control that appears after 3 s (#40) | SC-18, SC-19, SC-20 |
| FR-17 | When the wait ends without a ready element, the agent shall fail the step with a message that names the logical name, the time waited in milliseconds and the readiness condition that was not met. | Must | UC-09; #40 | T | SC-19, SC-29 |
| FR-18 | The agent shall perform Click, Type (replacing the control's text), Select (choosing an item by its text) and Wait as defined in the step schema. | Must | UC-09; #40; step schema (#13) | T — one test per keyword (#40) | SC-17, SC-20, SC-23 |
| FR-19 | After each step the agent shall capture a PNG of the AUT's window, cropped to that window, and return it with the step result. | Must | UC-09, UC-10; #54 | T | SC-17, SC-24 |

### 5.5 Runs, reports and CLI runner (RS §3.2.5)

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-20 | The system shall run a test from the editor on the local agent, show each step's status live in the client, store the run and its step results on the server, and show the same live status in every other client that has the test open. | Must | UC-09; #44, #51 | T + D | SC-17 |
| FR-21 | The server shall produce an HTML report for every run — a summary, a step table with status, duration and error, and a screenshot per step — downloadable as one self-contained file that opens in a browser with no network. | Must | UC-10; Core 5; #59 | T | SC-24, SC-36 |
| FR-22 | The client shall list runs with their test, status, duration and user, filter them by test and status, and open a run's report. | Must | UC-10; #68 | D | SC-03, SC-24 |
| FR-23 | The CLI runner shall run a suite with a headless agent, either from the server (`--server URL --suite NAME`) or from a file (`--from-file`), exit with 0 when every test passes and 1 otherwise, and post the results to the server when one is given. | Should | UC-14; #61 | T | SC-33, SC-34 |
| FR-24 | The CLI runner shall write its results as JUnit XML that validates against the JUnit schema. | Should | UC-14; #66, #67 | T — schema check and the CI job of #67 | SC-33, SC-34 |

### 5.6 Turkish NL assistant, C1 (RS §3.2.6)

FR-25 and FR-26 are Must because the plan never cuts the offline NL measurement (RQ3), which needs them; the chat panel (FR-27) is second in the cut order, so it is Should.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-25 | The AI service shall turn a Turkish test description, given with the current application and screen, into suggested steps in the step schema, using the current screen's subgraph and the closest repository objects as context, and shall give a short reason for each step. | Must | UC-08; C1; CON-03; #58, #71 | T + A — RQ3 (#77) | SC-26, SC-36 |
| FR-26 | The AI service shall drop every generated step whose target is not an object in the application's repository or that does not validate against the step schema, and shall return only validated steps, with the reason for each dropped step. | Must | UC-08; CON-05; ADR LLM authoring-only; #71 | T — stub-model test | SC-27 |
| FR-27 | The client's NL panel shall show suggested steps for review, let the user edit them and accept them all or one by one, save nothing before the user accepts, and add accepted steps to the test as ordinary steps; while the AI service cannot be reached, the panel shall be disabled with a message that says so. | Should | UC-08; #78 | D | SC-26, SC-28 |
| FR-28 | The system shall provide every function other than NL step generation — Spy, repository, editor, runs, reports, healing, change impact and CLI runner — while the AI service is stopped. | Must | UC-08; CON-05; ADR LLM authoring-only | T + D | SC-28 |

### 5.7 Self-healing proposals and approval, C2 (RS §3.2.7)

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-29 | When no element matches a step's target after the wait, the agent shall score the candidate elements in the same window with a compatible control type using the weighted similarity S(c, t) = Σ wᵢ · simᵢ(c, t) / Σ wᵢ, and shall end the step as "repair proposed" with the top 3 candidates and each property's contribution to their scores. | Must | UC-12; C2; CON-06; #42, #43, #49, #73 | T — scorer unit tests (#49), A — RQ4 (#76) | SC-29, SC-31 |
| FR-30 | The agent shall never perform a step on a healing candidate: after a "repair proposed" step it shall stop the test, mark the remaining steps as not run (TBD-6), and send the proposal to the server. | Must | UC-12; CON-06; ADR approval-gated healing; #73 | T | SC-29, SC-31 |
| FR-31 | The client shall show a healing proposal — the failing step, the top 3 candidates with per-property contribution bars and an on-screen outline of the selected candidate — open it from the run report, and let the reviewer approve one candidate or reject all. | Must | UC-12; #75 | D | SC-30, SC-31 |
| FR-32 | When a proposal is approved, the server shall make the repository object resolve to the chosen element for that application version and create a Rule linked to the proposal; when all candidates are rejected, it shall keep the step failed and leave the repository unchanged. | Must | UC-12; CON-06; #74 | T | SC-30, SC-31 |

### 5.8 Change-impact analysis, C3 (RS §3.2.8)

The plan cuts the change-impact view first but keeps "the Cypher query and a text report", so the query (FR-33) is Must and the view (FR-34) is Should.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-33 | The server shall return, for two versions of an application, the repository objects whose element changed between their snapshots, the tests whose steps target those objects, and the pending healing proposals for those objects. | Must | UC-13; C3; #81 | T — against the ground truth of #46 | SC-32 |
| FR-34 | The client's change-impact view shall let the user choose two versions and show the result with a link to each affected test. | Should | UC-13; #81 | D | SC-32 |

### 5.9 Failure triage and decision log (RS §3.2.9)

The plan cuts rule-based triage third but keeps the decision log, so classification (FR-35) is Should and the log (FR-36) is Must.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-35 | The agent shall put every failed step in exactly one category — element not found, unexpected window, assertion failed or timeout (TBD-5) — and the client shall show the category with the step. | Should | UC-11; #63 | T | SC-19, SC-21, SC-22, SC-25 |
| FR-36 | The system shall log every failure decision (the failed step, its category, any healing proposal and its outcome) with its context, and shall export the log as JSONL. | Must | UC-11; ADR decision layer in semester 2; #63 | T | SC-25, SC-31 |

### 5.10 Projects, applications, users and settings (RS §3.2.10)

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-37 | On first run the client shall ask for the server URL, show an error that names the URL when no AYNA server answers there, and remember the server and the chosen application on that machine between restarts. | Must | UC-01; #32 | T + D | SC-01, SC-02 |
| FR-38 | The server shall create and list applications and their versions, and reject a duplicate application name or a duplicate version of one application with HTTP 409. | Must | UC-01; #128 | T — integration test | SC-01 |
| FR-39 | The server shall provide local user accounts with the role admin or tester, and allow only admins to create, change or remove accounts. | Must | UC-15; #60 | T | SC-03 |
| FR-40 | The server shall store the id of the acting user with every test edit, run and healing decision. | Must | UC-15; #60, #74 | T | SC-03, SC-30 |

## 6. Non-functional requirements

Grouped as in RS §3.3–§3.8. Numbers taken from an issue or the plan cite it; every other number is marked "(proposed, to confirm)".

### 6.1 Performance (RS §3.3)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-01 | The agent shall return the element under a screen point (Spy pick) within 300 ms. | Must | UC-02; #22 | T — Windows test (#22); SC-04 |
| NFR-02 | The agent shall export the snapshot of one sample-app window within 2 s. (#12 sets 2 s for the trial app; applying it to every sample-app window is proposed, to confirm.) | Must | UC-05; #12 | T — SC-09 |
| NFR-03 | Capturing a step's screenshot shall add less than 300 ms to the step. | Must | #54 | T |
| NFR-04 | Leaving out the smart wait and the screenshot, the agent shall complete a step within 500 ms (proposed, to confirm). | Must | UC-09 | T — timings in the playback tests (#40) |
| NFR-05 | A step without `timeoutMs` shall wait at most 10 000 ms (proposed, to confirm); the default shall be configurable per run, and `timeoutMs` per step from 0 to 600 000 ms. | Must | UC-09; #40; step schema (#13) | T |
| NFR-06 | A step's status shall appear in every client that has the test open within 1 s of the agent's step result (proposed, to confirm). | Must | UC-09; #44 | T + D — SC-17 |
| NFR-07 | The server shall answer 95 % of REST requests, other than report downloads and snapshot imports, within 500 ms under the load of NFR-08 (proposed, to confirm). | Must | Q5 (#19) | T — load test, planned in #35 |
| NFR-08 | One server shall serve at least 10 clients working at the same time, with at least 1 000 repository objects and 500 tests per application (proposed, to confirm). | Must | Q5 (#19); CON-04 | T — load test, planned in #35 |
| NFR-09 | The server shall generate the HTML report of a 50-step run within 5 s (proposed, to confirm). | Must | UC-10; #59 | T |
| NFR-10 | Healing candidates for one repository object shall be generated within 1 s. | Must | UC-12; #42 | T — SC-29 |
| NFR-11 | A retrieval query for NL context (vector top-k plus the current screen's subgraph) shall return within 200 ms. | Must | UC-08; #58 | T |
| NFR-12 | The p95 latency of NL step generation per scenario on team hardware shall be measured and reported; semester 1 commits to no target value. | Must | UC-08; plan success criteria; #71, #77 | A — RQ3 report (#77) |
| NFR-13 | The AI service shall run its quantised 7–8B model and its embedding model on a machine with 16 GB RAM and no GPU (proposed, to confirm; #7 measured about 5 GB per 8B Q4 model on a 16 GB laptop). | Must | D2; #7, #131 | A + D |

### 6.2 Usability (RS §3.4)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-14 | A user shall be able to inspect elements, maintain the repository, build tests with checkpoints, run them, read reports and decide on healing proposals in the client without writing code or typing JSON. | Must | brief; ROLE-1; UC-02–UC-04, UC-06, UC-07, UC-09, UC-10, UC-12 | D — SC-14, SC-17, SC-30 at the weekly session |
| NFR-15 | Every error shown to the user shall name the step, repository object, field or URL it concerns. | Must | #25, #32, #39, #40 | I — review of messages; T where an issue fixes the text (#39, #40) |
| NFR-16 | The system shall accept, store, show and replay Turkish characters (ç, ğ, ı, İ, ö, ş, ü) in test names, step values, expected values and NL descriptions without change. | Must | CON-03 | T — SC-20, SC-26 |
| NFR-17 | The client's labels and messages shall be in TBD-2 (Turkish, English or both; Q4). | Must | CON-03; Q4 (#19) | I |
| NFR-18 | In a SUS study with non-programmer users, AYNA shall score at least 68 (proposed, to confirm). | Won't (S1) | brief; #104 | A — SUS study, semester 2 (#104) |

### 6.3 Interfaces and portability (RS §3.5, §3.8.5)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-19 | The client and the agent shall run on 64-bit Windows TBD-3 (proposed: Windows 10 22H2 and Windows 11, to confirm), and the agent shall automate applications through UI Automation with the win32 fallback. | Must | CON-02; ADR Windows first | D — weekly Windows session, clean VM of #85 |
| NFR-20 | Picking, outlining and playback shall be correct at 100 % and 150 % display scaling. | Must | #22 | T — Windows test (#22); SC-05 |
| NFR-21 | The agent shall reach the application under test only through a driver interface, so that a web or mobile driver can be added without changing the step schema, the server or the client. | Must | CON-02; ADR Windows first; OOS-01 | I — SDD review (#45) |

### 6.4 Design constraints (RS §3.7)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-22 | The agent and the CLI runner shall call no language model and not the AI service during a run; a run shall give the same result with the AI service stopped. | Must | CON-05; ADR LLM authoring-only | I — code review; T — SC-28 |
| NFR-23 | Every component AYNA ships or needs at run time shall be free of per-user licence cost, and the model names and licences shall be documented. | Must | CON-04; #82 | I |
| NFR-24 | Neo4j Community Edition shall be the only database, and product code shall be written only in Python, TypeScript and Java. | Must | CON-07; ADRs stack, Neo4j, client TypeScript | I |

### 6.5 Reliability (RS §3.8.1)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-25 | Over 10 runs of each of at least 10 reference scenarios, the flaky rate shall be below 10 % at the end of semester 1 and below 5 % at the end of the project. | Must | RQ2; brief success criteria; #69 | A — RQ2 report with Wilson CI (#69) |
| NFR-26 | At least 10 reference scenarios built in the editor shall replay end to end without manual fixes by G2. | Must | RQ2; G2; #55, #62 | D + A — SC-17, SC-23; #55 |
| NFR-27 | At least 90 % of the standard controls in the pilot apps shall be recognised by multi-property identification. | Must | RQ1; brief success criteria; #64 | A — RQ1 report (#64); SC-06 |
| NFR-28 | The server shall store 100 consecutive runs, each step with a retrievable screenshot, without errors, and shall keep only the last N runs, N being configurable. | Must | #51 | T |

### 6.6 Security and closed-network operation (RS §3.8.3)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-29 | At run time no AYNA component (client, agent, CLI runner, server, Neo4j, AI service) shall connect to a host outside the closed network: no CDN, telemetry, auto-update, licence check or cloud model, and the client shall load all of its fonts, scripts and styles from the installed files. | Must | CON-01; brief; architecture | D — firewall log in the air-gapped test (#85), SC-36; I — client bundle |
| NFR-30 | The AI service shall start and generate steps with the network disabled, with the model weights and the embedding model bundled in its image and nothing downloaded at start. | Must | CON-01; #71, #82 | T — #82; D — SC-36 |
| NFR-31 | The agent shall listen on 127.0.0.1 only and refuse every connection that does not carry the per-session token (at least 16 characters, created by the client and passed in an environment variable, never in a command line or URL) in an `Authorization: Bearer` header. | Must | CON-07; #16 | T — agent RPC tests (#16) |
| NFR-32 | The server shall store passwords only as bcrypt hashes (#60) and refuse every REST and WebSocket request except login unless it carries a valid session (proposed, to confirm). | Must | UC-15; #60 | T |

### 6.7 Maintainability (RS §3.8.4)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-33 | Keeping tests passing after a UI change shall need changes to repository objects only, not to test steps. | Must | brief (Core 2); plan | D — SC-12, SC-30 |
| NFR-34 | The step, element and snapshot schemas, the REST API and the agent JSON-RPC contract shall carry a version, be frozen at G1 with contract tests in CI, and change only through an ADR. | Must | architecture "Contracts"; G1; #52 | I + T — contract tests (#52) |
| NFR-35 | Every module's tests and linters shall run in CI on every pull request, and a pull request shall merge only when CI is green. | Must | working agreement (#8); #3 | I — CI configuration |

### 6.8 Installation and operation (RS §3.8.6)

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-36 | One Windows installer shall install the client and the agent on a clean Windows machine with no development tools and no internet access, uninstalling shall leave no AYNA process running, and the backend shall start with one `docker compose up` from an offline bundle. | Must | UC-16; CON-01; #84, #85 | D — SC-35 on a clean VM |

## 7. Traceability check

### 7.1 Use cases → scenarios and functional requirements

| UC | Use case | Scenarios | FRs (from the Source column) |
|---|---|---|---|
| UC-01 | Connect to the server and register an application version | SC-01, SC-02 | FR-37, FR-38 |
| UC-02 | Inspect an element with the Object Spy | SC-04, SC-05, SC-06, SC-07, SC-08 | FR-01, FR-02, FR-03, FR-05 |
| UC-03 | Add an element to the object repository | SC-10, SC-11 | FR-06, FR-07 |
| UC-04 | Maintain the object repository | SC-12, SC-13 | FR-08, FR-09 |
| UC-05 | Capture a snapshot of an application version | SC-09, SC-32 | FR-04 |
| UC-06 | Build a test in the codeless editor | SC-14, SC-15, SC-20 | FR-11, FR-12, FR-13, FR-14 |
| UC-07 | Add a property checkpoint | SC-14, SC-16, SC-21 | FR-15 |
| UC-08 | Write steps from a Turkish description | SC-26, SC-27, SC-28, SC-36 | FR-25, FR-26, FR-27, FR-28 |
| UC-09 | Run a test and watch it live | SC-08, SC-17, SC-18, SC-19, SC-20, SC-21, SC-22, SC-23, SC-28, SC-29, SC-36 | FR-05, FR-10, FR-16, FR-17, FR-18, FR-19, FR-20 |
| UC-10 | Read the run report and run history | SC-24, SC-36 | FR-19, FR-21, FR-22 |
| UC-11 | See the failure category of a failed step | SC-19, SC-21, SC-22, SC-25 | FR-35, FR-36 |
| UC-12 | Approve or reject a healing proposal | SC-29, SC-30, SC-31, SC-36 | FR-29, FR-30, FR-31, FR-32 |
| UC-13 | See which tests a new version affects | SC-32 | FR-33, FR-34 |
| UC-14 | Run a suite headless in CI | SC-33, SC-34 | FR-14, FR-23, FR-24 |
| UC-15 | Manage user accounts | SC-03 | FR-39, FR-40 |
| UC-16 | Install and run AYNA on a closed network | SC-35, SC-36 | none — covered by NFR-29, NFR-30 and NFR-36 |

### 7.2 Coverage

Checked on 2026-10-27 by parsing this file's tables (a one-off script, not committed):

- **36 scenarios** (SC-01–SC-36): 21 main, 11 negative, 4 edge. Every scenario has Given, When and Then. 30 run on the sample app or its versions, 3 on the pilot apps and 3 on the client, server and installer alone.
- **40 functional requirements** (FR-01–FR-40): 35 Must, 5 Should. **Every FR lists at least one scenario, and every scenario it lists exists.**
- **36 non-functional requirements** (NFR-01–NFR-36): 35 Must, 1 Won't (S1). Closed-network operation: NFR-29, NFR-30, NFR-36. Response times: NFR-01–NFR-12.
- **Every use case UC-01–UC-16 has at least one scenario.** Every use case except UC-16 has at least one FR; UC-16 (installation and closed-network operation) is a quality requirement and is covered by NFR-29, NFR-30 and NFR-36.
- **Every scenario is the evidence for at least one requirement.** SC-35 is listed by no FR; it is the evidence for NFR-36.

## 8. Open items (TBD)

These go into RS Appendix E (#35 continues the numbering from TBD-7).

| ID | Item | Where it is used | Owner | Closes in |
|---|---|---|---|---|
| TBD-1 | Pilot apps P1 and P2 (product and UI technology) | §2; SC-06, SC-07, SC-23; NFR-27 | hasan | D1, #21 (after #6) |
| TBD-2 | Client UI language: Turkish, English or both | NFR-17 | galip (advisor, Q4) | #19 §7 |
| TBD-3 | Supported Windows versions of the test machines | NFR-19 | hasan, omer | #35 |
| TBD-4 | Numbers marked "(proposed, to confirm)": NFR-02 (2 s for every sample-app window), NFR-04 (500 ms per step), NFR-05 (10 000 ms default timeout), NFR-06 (1 s live status), NFR-07 (500 ms p95 REST), NFR-08 (10 clients, 1 000 objects, 500 tests), NFR-09 (5 s report), NFR-13 (16 GB RAM, no GPU), NFR-18 (SUS ≥ 68), NFR-19 (Windows versions), NFR-32 (session required on every request) | §6 | hasan: NFR-02, NFR-04, NFR-05 · omer: NFR-06–NFR-09, NFR-32 · galip: NFR-13, NFR-18 | Q5 at the advisor meeting; #35 |
| TBD-5 | Boundary between "element not found" and "timeout": proposed — "element not found" when no element matches the primary or fallback properties by the end of the wait (healing starts); "timeout" when an element matches but does not become visible and enabled in time (no healing) | FR-35; SC-19, SC-25, SC-29 | hasan | #40, #63 |
| TBD-6 | After a "repair proposed" step: proposed — the test stops and its remaining steps are marked "not run" | FR-30; SC-29, SC-31 | hasan | #73 |
