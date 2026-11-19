# AYNA RS — Appendix C: Reference scenarios

| | |
|---|---|
| Issue | #34 — reference scenarios and functional requirements |
| Status | Final, part of RS 1.0 (#41), 2026-11-19; first drafted 2026-10-27 |
| Part of | Appendix C of the Requirements Specification, [`docs/rs/RS.md`](RS.md) (#35); included in full in the submitted PDF (#41) |
| Builds on | Use cases `UC-01`–`UC-16` (RS Appendix B, condensed from `docs/requirements-workshop.md`, #19, a draft awaiting the advisor) · ID conventions from RS §1.5 |

## C.1 How to read this appendix

- **IDs** follow RS §1.5: `SC-xx`, flat and two-digit, never reused or renumbered. A dropped scenario stays here, marked _Deleted_ with the reason. `UC-xx` are the use cases of RS Appendix B; C1–C4, RQ1–RQ5 and D1–D7 are the plan's. `#nn` is an issue.
- **Scenarios** are written as Given / When / Then (And continues the line above). Each one names its use cases, the application under test (C.2) and its kind: _main_ (the use case's main flow), _negative_ (an error or a rejected input) or _edge_ (a boundary condition).
- **Logical names** such as `login.userNameInput` follow the `screen.element` convention. They are the sample app's names (#33; `eval/nl/objects/sample.json` lists them); `main.customerSearchInput` in SC-12 is the new name the scenario gives an object. The settings tab items (`settings.notificationsTab`) share one AutomationId and are told apart by their Name.
- **One place per item.** This appendix holds the scenario texts only. Their summary table is RS §3.1; the requirements they exercise are in RS §3.2–§3.8, where every FR lists its scenarios; the traceability matrix is RS §5 and the open items are RS Appendix E.

## C.2 Applications under test

| Code | Application | What it is | Status |
|---|---|---|---|
| SA | Sample app v1.0 | PySide6 app with six screens: login, list with a grid, detail form, settings with tabs, dialog, wizard. Every control has an AutomationId; the version is shown in the title bar | Built: #33, version 1.0 |
| SA-C | Controlled-change versions of the sample app | One UI change each: rename, move, retype, re-parent, AutomationId removed, plus one combined. Each comes with a ground-truth mapping from old to new element | Built: #46 |
| SA-B | Bug-injected versions of the sample app | One functional bug each: wrong label (SC-21), disabled button (SC-19), wrong saved value (SC-20), missing validation (SC-34), and a list screen that has lost its search button (SC-31) | Built: #47 (`eval/apps/sample/bugs.md`); the SC-31 version replaces the first build's wrong navigation, see SC-31 |
| P1, P2 | Pilot apps | P1 HandBrake (WPF), P2 KeePass 2 (WinForms); KeePassXC (Qt Widgets) may join as a third | Chosen in D1 (#21) from the UIA dumps of #6 (TBD-1 closed) |

**Sample-app behaviour these scenarios assume** (the input #33 was built from; the app does all of it):

- Login screen: user-name field, password field, remember-me check box, login button and status label. `admin` / `admin` shows a welcome text that contains the user name; a wrong password shows an error text (as in the trial app, #9).
- List screen: search field, search button, results grid, Open button. After a search, the grid fills about 3 s later and the Open button is enabled only then; the delay is configurable (SC-18).
- Detail form: at least a name field, a combo box, Save and Back, and one validation rule (a required field) that the "missing validation" bug removes (SC-34). Leaving an edited form asks "discard changes?" in a modal dialog (SC-22).
- Settings: several tabs, one of them with an e-mail-notifications check box (SC-16).
- Wizard: three pages (a name field; a department combo box whose items have Turkish text such as "Kalite Güvence"; a summary label) with Next, Back and Finish. Finish opens a confirmation dialog with Yes and No (SC-20).

## C.3 Scenarios

### C.3.1 Setup, connection and accounts

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

### C.3.2 Object Spy and snapshots

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
UC-02 · AUT: P2 KeePass 2, or Notepad++ (the #23 fixture) if neither pilot has such a control · edge
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

### C.3.3 Object repository

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

### C.3.4 Test authoring and checkpoints

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

### C.3.5 Playback

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
- **Given** the sample app's wizard (C.2) and an empty test in the editor
- **When** the author builds and runs: Type `wizard.nameInput` "Ayşe Çelik"; Click `wizard.nextButton`; Select `wizard.departmentCombo` "Kalite Güvence"; Click `wizard.nextButton`; Verify `wizard.summaryLabel` name contains "Kalite Güvence"; Click `wizard.confirmCheck`; Click `wizard.finishButton`; Click `confirmDialog.yesButton`
- **Then** Select chooses the item by its text, the Yes button is found in the newly opened dialog window, and every step passes
- **And** the Turkish characters in the values appear unchanged in the app, in the step results and in the report
- **And** on the "wrong saved value" version (SA-B, `bug3`), whose summary shows the role where the department belongs, the Verify on `wizard.summaryLabel` fails with the category "assertion failed"

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

### C.3.6 Reports and failure triage

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

### C.3.7 Turkish NL assistant

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

### C.3.8 Self-healing

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
UC-12 · AUT: SA-B, "missing control" version · negative
- **Given** a test that logs in and then clicks `main.searchButton`, and the bug-injected version in which the list screen has lost its search button
- **When** the test is run
- **Then** `main.searchButton` is not found in the list screen, and the step ends as "repair proposed" with candidates from that screen, none of which is a search button
- **When** the reviewer rejects all candidates
- **Then** the step stays failed with the category "element not found", the repository and the rule book are unchanged, and the run counts as failed
- **And** the decision is logged. An automatically applied repair could have clicked a candidate and passed: this is the false pass that RQ5 measures (#86)
- **Note** A version in which logging in opens the wrong screen does not fit this scenario: the step's own window is then not in front, so the step fails as "unexpected window" and never heals (FR-29, FR-35), as in SC-22

### C.3.9 Change impact

#### SC-32 · Change impact between two versions
UC-05, UC-13 · AUT: SA, SA-C · main
- **Given** snapshots of version 1.0 and of a controlled-change version (captured as in SC-09), the reference tests of the sample app, and the pending healing proposal of SC-29
- **When** the test engineer chooses version 1.0 and the controlled-change version in the change-impact view
- **Then** the view lists the repository objects whose element changed, the tests that use them and the pending proposal, and the list of tests equals the ground truth of #46 exactly
- **And** each listed test links to that test in the editor
- **And** choosing the same version on both sides lists no change

### C.3.10 Continuous integration

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

### C.3.11 Installation and closed network

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
