# Requirements workshop: roles, use cases, constraints

> **Status: DRAFT for the advisor meeting on Tuesday 27 Oct 2026. Not yet agreed.**
> This is the team's proposal, written from the project plan, the [brief](../memory-bank/project/brief.md) and the [decisions](../memory-bank/decisions/README.md). It becomes the agreed basis for the Requirements Specification only after [§7](#7-advisors-answers-and-agreed-changes) is filled in.
> Issue: #19.

The RS outline (#27), the reference scenarios and functional requirements (#34) and the RS draft (#35) trace back to the IDs below: `ROLE-n`, `UC-nn`, `CON-nn`, `OOS-nn`, `Qn`. IDs are stable. If an item is dropped, it is marked *withdrawn* and its ID is not reused.

## 1. Scope in one paragraph

AYNA lets testers build, run and maintain UI regression tests for **Windows desktop applications** without writing code. It runs **on a closed network**, is hosted in-house and has no per-user licence. Semester 1 (20 Oct 2026 – 25 Jan 2027) delivers this chain: Object Spy → graph object repository → codeless editor → smart-wait playback → HTML report and JUnit XML. It also delivers two measured AI features. The first turns **Turkish** text into steps with a local model, and only while a test is being written. The second is explainable self-healing that waits for a person's approval.

## 2. User roles

| ID | Role | Who | What they do in AYNA | Account role (#60) |
|---|---|---|---|---|
| ROLE-1 | Test author | A tester or domain expert who does not need to program | Inspects screens with the Spy, names elements, builds tests in the editor or from Turkish text, runs them | tester |
| ROLE-2 | Test engineer | Owner of the tests for one application under test (AUT) | Registers app versions, maintains the repository, runs tests, reads reports and failure categories, checks what a new version affects, sets up CI | tester |
| ROLE-3 | Healing reviewer | A test engineer who decides on repairs | Approves or rejects healing proposals. An approval changes the repository and becomes a rule | tester (see Q1) |
| ROLE-4 | Administrator | The person who installs and runs AYNA for a test unit | Installs and operates the server, the database, the AI service and the clients on the closed network; manages user accounts | admin |
| ROLE-5 | CI pipeline | System actor | Runs a suite with the CLI runner and a headless agent on every build, and reads the JUnit XML | none (no interactive login) |

- In semester 1, ROLE-1 to ROLE-3 are responsibilities, not separate accounts. One person may hold all three. #60 plans two account roles, admin and tester, and records who made each edit, run and approval.
- The **application under test** is a passive system actor. Only the local agent touches it.
- Some stakeholders do not use AYNA directly:
  - the **advisor**, who accepts the RS and the SDD;
  - the **HAVELSAN mentor**, who may set the target UI technology and the pilot app (D5);
  - the **development teams of the applications under test**, who receive the testability guideline (#94);
  - **researchers** who reuse the open evaluation set (C4).

## 3. Use cases

**Prio** comes from the plan's fixed cut order ("If we fall behind"). **M** means the use case is not in the cut order. **S1–S4** give its position in the cut order; S1 is cut first.

| ID | Use case | Actor | Goal | Main flow | Prio | Traces to |
|---|---|---|---|---|---|---|
| UC-01 | Connect to the server and register an application version | ROLE-2 | Work against a named application and build | Set the server URL on first run → choose or create the Application → add an AppVersion for the build under test → the choice is remembered on this machine | M | [graph model](graph-model.md); #32, #128 |
| UC-02 | Inspect an element with the Object Spy | ROLE-1 | See how AYNA recognises a control | Start the AUT → open the Spy and choose a window: element tree and property panel → press the hotkey over a control → the control is outlined on screen and selected in the tree. The panel shows its descriptor: AutomationId, Name, ControlType, ClassName, parent path, nearest label and bounds | M | Core 1; RQ1; [ADR client/server][adr-cs]; #11, #22, #24 |
| UC-03 | Add an element to the object repository | ROLE-1 | Give a control a stable name that tests can use | In the Spy, choose "Add to repository" → enter a logical name (`screen.element`, e.g. `login.userNameInput`) → edit the primary and fallback properties → save. A logical name that already exists in the app is rejected | M | Core 2; [ADR Neo4j][adr-neo]; #25 |
| UC-04 | Maintain the object repository | ROLE-2 | Keep logical names and properties correct as the UI changes | Open the repository view → search → rename an object or edit its properties → see how many tests use each object. AYNA blocks deleting an object that a test uses | M | Core 2; #30 |
| UC-05 | Capture a snapshot of an application version | ROLE-2 | Store a build's whole window tree for healing and impact analysis | Choose a window → the agent exports its subtree as one snapshot → the server imports it under the AppVersion | M | Core 1; C2, C3; #12, #15 |
| UC-06 | Build a test in the codeless editor | ROLE-1 | Create a test without writing code | Create a test → add steps from the keyword list (Click, Type, Select, Verify, Wait) → pick each target from the repository → enter a value and, if needed, a timeout → drag steps to reorder them → invalid steps are highlighted with the reason → save | M | Core 3, 5; #13, #38, #39 |
| UC-07 | Add a property checkpoint | ROLE-1 | Check that the screen shows the expected result | Add a Verify step → pick the target → choose a property, an operator and the expected value → during a run, the step passes or fails on that comparison | M | Core 4; #13, #40 |
| UC-08 | Write steps from a Turkish description | ROLE-1 | Get draft steps from plain Turkish | Type a description in the NL panel, e.g. "Kullanıcı adına admin yaz, Giriş'e tıkla, ana menünün açıldığını kontrol et" → the server retrieves the current screen's subgraph and the closest repository objects → the local model returns steps in the step schema → steps whose target is not in the repository are rejected → the author edits and approves the steps → they join the test. If the AI service is down, everything else still works | S2 | C1; RQ3, H2; [ADR LLM][adr-llm]; #37, #58, #71, #78 |
| UC-09 | Run a test and watch it live | ROLE-1, ROLE-2 | Replay a test on the current build | Press Run → the client sends the steps to the local agent → before each step, the agent waits until the element exists, is visible and is enabled (configurable timeout) → it runs the step and takes a screenshot → each step's status appears live, also in other clients watching the test → the run is stored on the server | M | Core 4; RQ2; #26, #40, #44, #51, #54 |
| UC-10 | Read the run report and run history | ROLE-2 | See what passed and what failed | Open the run list (filter by test and status) → open a run → the HTML report shows a summary, a step table, a screenshot per step, durations and errors → download the report as one file that opens offline | M | Core 5; #59, #68 |
| UC-11 | See the failure category of a failed step | ROLE-2 | Know what kind of failure happened | Rules put each failed step in one category: element not found, unexpected window, assertion failed or timeout → the category is shown with the step → the decision is logged as a labelled example for semester 2 | S3 | [ADR decision layer][adr-dl]; #63 |
| UC-12 | Approve or reject a healing proposal | ROLE-3 | Repair a broken locator without hiding a real bug | When a step's element is not found, the step ends as "repair proposed" and the run never continues on a guessed element → open the proposal from the report: top 3 candidates with per-property contribution bars, each candidate outlined on screen → approve one: the repository is updated and a rule is written, so the next run passes; or reject all: the failure is treated as a bug | M | C2; RQ4/H1, RQ5/H3; [ADR healing][adr-heal]; #49, #73, #74, #75 |
| UC-13 | See which tests a new version affects | ROLE-2 | Know before a run which tests a UI change touches | Capture a snapshot of the new version (UC-05) → choose the old and the new version → the server lists the changed objects, the tests that use them and the pending healing proposals, with links to those tests | S1 | C3; #42, #81 |
| UC-14 | Run a suite headless in CI | ROLE-5 (set up by ROLE-2) | Run the regression suite on every build | The pipeline starts the AUT → `ayna run --server URL --suite NAME`, or `--from-file suite.json` without a server → the headless agent plays the steps → JUnit XML is written; the exit code is 0 if every test passes and 1 otherwise → results go to the server when one is given | S4 | Core 5; #61, #66, #67 |
| UC-15 | Manage user accounts | ROLE-4 | Control who can edit, run and approve | The admin creates accounts with the role admin or tester → users log in → AYNA stores the user id with every edit, run and approval. Only admins can manage users | M | #60 |
| UC-16 | Install and run AYNA on a closed network | ROLE-4 | Run AYNA with no internet access | Start the backend (server, Neo4j, AI service with bundled model weights) with one `docker compose up` on an internal host → install the Windows client and its agent from one installer on each test machine → point the clients at the server → the whole chain works with the network off and makes no outbound connections | M | CON-01; [ADR client/server][adr-cs]; #82, #84, #85 |

Notes:
- **What the cuts keep.** Cutting S1 keeps the Cypher query and a text report. Cutting S2 keeps the offline RQ3 measurement. Cutting S3 keeps the decision log. Cutting S4 moves the CLI runner and JUnit XML to semester 2.
- **Measurements are not use cases.** RQ1–RQ5 are team activities, not product use cases. They use UC-02, UC-05, UC-08, UC-09 and UC-12 as instruments.

## 4. Constraints

| ID | Constraint | What it means for the requirements | Source |
|---|---|---|---|
| CON-01 | **Closed network.** At run time, nothing calls a service outside the closed network: no CDN, no telemetry, no auto-update, no cloud model. Model weights are bundled. | Every use case works with the network off (UC-16). The NFRs in #34 include this | [brief](../memory-bank/project/brief.md), [architecture](../memory-bank/project/architecture.md). A project premise, not an ADR |
| CON-02 | **Windows desktop only in semester 1.** AYNA reaches the AUT through UI Automation, with a win32 fallback. The agent keeps a driver interface so web and mobile drivers can be added later | UC-02 to UC-14 assume a Windows AUT. Pilot apps cover different UI technologies (WinForms, WPF, Qt; D1, #21) | [ADR Windows first][adr-win] |
| CON-03 | **Turkish natural language.** The NL assistant takes Turkish test descriptions | UC-08. The NL dataset and the RQ3 evaluation are in Turkish (#36, #57, #77). Client UI language: Q4 | brief (C1) |
| CON-04 | **No licence cost.** AYNA is hosted in-house and has no per-user limit. It is built only on licence-free components (Neo4j Community Edition, an open-weight model) | Any number of engineers share one server (UC-01, UC-09). Model names and licences are documented (#82) | brief; [ADR stack][adr-stack], [ADR Neo4j][adr-neo] |
| CON-05 | **Language models only while a test is written.** The model only suggests steps, and the user approves them. Playback is deterministic and never calls a model. Generated steps may only target repository objects | UC-08 is the only use case that needs the AI service. UC-09 and UC-14 never call it | [ADR LLM][adr-llm] |
| CON-06 | **Self-healing proposes and never applies a fix during a run.** The repository changes only after a user approves. Each approval becomes a rule | UC-12. False passes are measured separately (RQ5) | [ADR healing][adr-heal] |
| CON-07 | **Fixed architecture.** Each test machine runs an Electron client with a local agent, because the Spy needs the AUT's screen. One central server serves everyone. Neo4j is the only database. Product code is written only in Python, TypeScript and Java | UC-02 runs on the AUT machine. Everyone shares one repository | [ADR client/server][adr-cs], [ADR Neo4j][adr-neo], [ADR stack][adr-stack], [ADR TypeScript][adr-ts] |
| CON-08 | **Schedule and capacity.** RS due 23 Nov 2026, SDD due 7 Dec 2026, demo on 19 Jan 2027. About 10 hours per person per week. The cut order is fixed in advance | The Prio column in §3 | plan; brief (Calendar) |

## 5. Out of scope

| ID | Item | Status | Source |
|---|---|---|---|
| OOS-01 | Web and mobile drivers (Selenium, Appium) | Later; the driver interface stays open | plan; [ADR Windows first][adr-win] |
| OOS-02 | Visual and OCR checkpoints | Not planned. A narrow visual fallback is added only if RQ1 finds more than 10% of controls unrecognised (D3, week 9, #65) | plan |
| OOS-03 | Code injection into the AUT to reach its internal objects (TestComplete's Open Applications) | Not planned | plan |
| OOS-04 | Script-based tests | Not planned | plan |
| OOS-05 | Distributed runs | Not planned | plan |
| OOS-06 | User-profile simulation | Not planned | plan |
| OOS-07 | RPA | Not planned; AYNA is for test automation only | plan |
| OOS-08 | Recorder (Click, Type, Select recorded into the step schema) | Semester 2 (#99), as in the HAVELSAN letter of intent | plan; brief |
| OOS-09 | Property checkpoints created from the Spy | Semester 2 (#100); in semester 1, checkpoints are added in the editor (UC-07) | plan |
| OOS-10 | Data-driven tests from CSV or Excel | Semester 2 (#101) | plan |
| OOS-11 | Calibrated decision layer and unexpected-window handling | Semester 2 (#102, #103). Semester 1 builds rule-based triage and logs every decision (UC-11) | [ADR decision layer][adr-dl] |
| OOS-12 | A full TestComplete clone | Not a goal; AYNA builds the core only | plan |

## 6. Questions for the advisor

- **Q1. Roles.** Are ROLE-1 to ROLE-5 right? For semester 1, are the account roles admin and tester (#60) enough? Or should only a separate approver permission be allowed to approve healing proposals (UC-12)?
- **Q2. Use cases.** Is UC-01 to UC-16 complete enough for the RS? Is the Prio column, taken from the plan's cut order, acceptable?
- **Q3. Out of scope.** Do you agree with §5, especially the recorder and data-driven tests in semester 2 (OOS-08, OOS-10)?
- **Q4. Language.** The NL assistant takes Turkish (CON-03). Should the client UI be in Turkish, in English or in both? May the RS be written in English?
- **Q5. NFR figures.** Which response times and capacity should the RS commit to? Our proposal comes from the issues: Spy pick under 300 ms (#22) and a window snapshot under 2 s (#12). NL latency would be reported, not promised (plan). How many clients working at the same time should one server support?
- **Q6. RS format.** Does the course give an RS template, or is the ISO/IEC/IEEE 29148 structure acceptable (#27)?
- **Q7. Pilot apps and HAVELSAN.** Is there any input from the HAVELSAN mentor (D5) that changes the target technology? Should the RS name the pilot apps (D1, #21) or describe them only by UI technology?
- **Q8. Accounts.** On a closed network, are local username and password accounts (#60) enough?

## 7. Advisor's answers and agreed changes

*Galip fills this in after the meeting. Until then, nothing in §2–§5 is agreed.*

- Meeting date:
- Present:
- Roles (§2): agreed / changed:
- Use cases (§3): agreed / changed:
- Constraints (§4): agreed / changed:
- Out of scope (§5): agreed / changed:

| Question | Advisor's answer | Change made (section, ID) |
|---|---|---|
| Q1 | | |
| Q2 | | |
| Q3 | | |
| Q4 | | |
| Q5 | | |
| Q6 | | |
| Q7 | | |
| Q8 | | |

[adr-win]: ../memory-bank/decisions/2026-10-20-windows-desktop-first.md
[adr-llm]: ../memory-bank/decisions/2026-10-20-llm-authoring-only.md
[adr-heal]: ../memory-bank/decisions/2026-10-20-approval-gated-self-healing.md
[adr-dl]: ../memory-bank/decisions/2026-10-20-decision-layer-semester-2.md
[adr-cs]: ../memory-bank/decisions/2026-10-20-electron-client-central-server.md
[adr-neo]: ../memory-bank/decisions/2026-10-20-neo4j-single-database.md
[adr-stack]: ../memory-bank/decisions/2026-10-20-tech-stack.md
[adr-ts]: ../memory-bank/decisions/2026-10-25-client-typescript.md
