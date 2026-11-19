# AYNA — Requirements Specification (RS)

| | |
|---|---|
| Project | AYNA — Akıllı, Yerli, Nesne Tabanlı Arayüz Testi: codeless UI test automation for Windows desktop applications on a closed network |
| Course | COM 4061 Research Project I, Ankara University |
| Advisor | Prof. Dr. Gazi Erkan Bostancı |
| Team | Galip Enes Doğan · Ömerfaruk Sarıbal · Hasan Berk Yanıkkaya |
| Programme | HAVELSAN SUIT application |
| Document | Software Requirements Specification in the style of ISO/IEC/IEEE 29148:2018 §9.6 [40] |
| Version | 1.0 — submitted version (#41) |
| Date | 2026-11-19 |
| Status | Final for the course submission of 23 Nov 2026 (#41; PDF `docs/rs/RS-1.0.pdf`). Reviewed by Ömerfaruk and Hasan (#35, PR #143, and every later version's PR). The use cases remain the team's proposal: the requirements workshop with the advisor (#19) has not been held, so the eight questions of Appendix E.2 are still open and the items that depend on them are deferred, not closed |

## Document history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-10-27 | Galip | Outline (#27) |
| 0.5 | 2026-10-27 | Galip | Full draft (#35): every section filled; FR and NFR tables of #34 moved in from `docs/rs/scenarios.md`; NFR-37–NFR-44 added; use-case catalogue, traceability and open items. Review by Galip and Ömerfaruk pending |
| 0.6 | 2026-10-29 | Galip | Review comments of Ömerfaruk and Hasan on PR #143 (#35): FR-30 and FR-23 follow the healing-proposal-transport ADR (the client or CLI runner delivers results; CLI exit codes 0/1/2); API tokens for CI close TBD-10 (FR-23, FR-39, NFR-32); FR-08 keeps steps on rename; FR-35 gets a fifth category, "search incomplete", and FR-29 heals only after a complete search (TBD-5 closed); NFR-02, NFR-04, NFR-05 reworded; the owners' numbers team-confirmed (TBD-4); load test #152 (TBD-9 closed); TBD-6 closed; NFR-45 (result outbox) and NFR-46 (AI service port) added |
| 0.7 | 2026-10-31 | Galip | NFR-45: a result the server refuses as invalid is set aside and shown, not retried (Ömerfaruk's review of PR #164; ADR healing proposal transport) |
| 0.8 | 2026-11-02 | Galip | §2.2 project documents brought up to date: REST API v0 generated (#160, Ömerfaruk's #31 note), element, snapshot and healing-proposal schemas merged, SDD sections merged. NFR-32 names its public endpoints: login, health, the OpenAPI document and Swagger UI (Ömerfaruk, #60) |
| 0.9 | 2026-11-15 | Galip | TBD-2 closed: the client is in Turkish and English, chosen by the user (NFR-17; ADR client-ui-language, #185). NFR-07 and NFR-08 confirmed by the load test (#152, Ömerfaruk, 2026-11-10: 100.0 % of requests within 500 ms, p95 31.9 ms) |
| 1.0 | 2026-11-19 | Galip | Submitted version (#41). Step schema 0.2 in FR-11, FR-15 and FR-18 (`SelectRow` and the row checks, #147). FR-35 says how an ambiguous match, an unexpected window, a refused step and a rejected action are classified, as playback does it (#63, ADR failure-category); FR-29 never heals after an ambiguous match or outside the step's own window. Pilot apps named (TBD-1 closed, D1): P1 HandBrake, P2 KeePass 2. NFR-02 cites the #161 root cause; NFR-12 cites the Windows latency numbers (#162). SC-20 names the wrong-saved-value version and ticks the confirmation box the sample app asks for before Finish; SC-31 runs on a version that removes the target from the right window, so its candidates are real. §2.2 brought up to date. Every remaining TBD is closed or deferred with a reason (Appendix E) |

Approval: each version is approved in a pull request by the three team members; the advisor reviews the draft at the Tuesday meeting. Galip leads the RS (ADR windows-work-to-hasan); the plan still names Hasan (TBD-8).

## 1 Introduction

### 1.1 Purpose

This document states what AYNA must do and how well, at the end of semester 1 (19 January 2027), and which parts wait for semester 2. It is the agreed basis for the design (SDD, #45, #53), for the tests and measurements, and for the acceptance of the semester-1 system (§4.4).

Readers:
- the **advisor**, who accepts the RS;
- the **course jury**, who grade it as the COM 4061 requirements deliverable;
- the **HAVELSAN mentor**, who may adjust the target technology and pilot application (D5);
- the **team**, who design, build and verify against it.

Together with the SDD it forms the design baseline frozen at gate G1 (#56, week 7).

### 1.2 Scope

**AYNA** lets testers build, run and maintain UI regression tests for Windows desktop applications without writing code. It is hosted in-house, runs on a closed network and has no per-user licence, so any number of engineers can share it. It is not a full TestComplete clone (OOS-12). It builds the core of such a platform and adds three things existing tools do not offer in this form.

Semester 1 delivers this chain: Object Spy → graph object repository → codeless editor → smart-wait playback → HTML report and JUnit XML. On top of it, three contributions:
- **C1**: Turkish natural language → steps on a local open-weight model, used only while a test is written.
- **C2**: explainable self-healing. It proposes a repair with per-property reasons and never applies it during a run.
- **C3**: change-impact analysis from the graph.

C4, the open evaluation set, is a research output, not a product function.

**Goals and success criteria.** The project's success criteria, with the requirement that carries each:

| Criterion | End of semester 1 (19 Jan 2027) | End of project (June 2027) | RQ | Requirement |
|---|---|---|---|---|
| Recognition of standard controls in the pilot apps | ≥ 90 % | ≥ 90 % | RQ1 | NFR-27 |
| Replay without manual fixes | ≥ 10 reference scenarios from editor-built steps | ≥ 85 % of recorded scenarios | RQ2 | NFR-26 |
| Flaky result rate (10 runs per scenario) | < 10 % | < 5 % | RQ2 | NFR-25 |
| Turkish NL → steps | ≥ 60 % step-level accuracy on the held-out split; latency on team hardware reported | ≥ 70 % of scenarios need no manual fix | RQ3, H2 | NFR-37, NFR-12 |
| Self-healing under controlled UI changes | Offline experiment done, H1 tested | ≥ 80 % correct matches | RQ4, H1 | FR-29 (measured, no semester-1 target) |
| False passes on bug-injected versions | First measurement, approval-gated vs auto-applied | 0 with the decision layer | RQ5, H3 | FR-30, FR-32 (measured, no semester-1 target) |
| Closed-network operation | Full stack installed and run on a clean VM with the network off | Same, on a HAVELSAN-like environment | — | NFR-29, NFR-30, NFR-36 |
| CI integration | CLI runner writes JUnit XML; CI runs the sample suite | Runs in a real CI pipeline | — | FR-23, FR-24 |
| Usability | — | SUS score measured with non-programmer users [39] | — | NFR-18 |

**Out of scope.** IDs from the requirements workshop (#19):

| ID | Item | Status |
|---|---|---|
| OOS-01 | Web and mobile drivers (Selenium, Appium) | Later; the driver interface stays open (NFR-21) |
| OOS-02 | Visual and OCR checkpoints | Not planned; a narrow visual fallback only if RQ1 finds > 10 % of controls unrecognised (D3, #65) |
| OOS-03 | Code injection into the AUT (TestComplete's Open Applications) | Not planned |
| OOS-04 | Script-based tests | Not planned |
| OOS-05 | Distributed runs | Not planned |
| OOS-06 | User-profile simulation | Not planned |
| OOS-07 | RPA | Not planned; AYNA is for test automation only |
| OOS-08 | Recorder (Click, Type, Select into the step schema) | Semester 2 (#99), as in the HAVELSAN letter of intent |
| OOS-09 | Property checkpoints created from the Spy | Semester 2 (#100); in semester 1 they are added in the editor (UC-07) |
| OOS-10 | Data-driven tests from CSV or Excel | Semester 2 (#101) |
| OOS-11 | Calibrated decision layer and unexpected-window handling | Semester 2 (#102, #103); semester 1 builds rule-based triage and logs every decision (UC-11) |
| OOS-12 | A full TestComplete clone | Not a goal |

### 1.3 Product overview

#### 1.3.1 Product perspective

AYNA is a new, self-contained product. It has five components on one closed network:

```
 Each test machine (Windows)                          Shared host(s) on the closed network
┌──────────────────────────────────┐  REST + WebSocket ┌────────────────────────────────────┐
│ Electron client (TypeScript)     │◀─────────────────▶│ Server (Java, Spring Boot)         │
│ Spy, repository, editor, NL      │                   │ applications, repository, tests,   │
│ panel, runs, reports, healing    │                   │ runs, reports, rule book, users    │
└───────────────┬──────────────────┘                   └──────┬───────────────────┬─────────┘
  JSON-RPC over │ 127.0.0.1 WebSocket (token)            Bolt │                   │ HTTP, authoring time only
┌───────────────▼──────────────────┐                   ┌──────▼───────┐   ┌───────▼──────────────┐
│ Automation agent (Python)        │                   │ Neo4j CE     │   │ AI service (Python)  │
│ UI Automation + win32, waits,    │                   │ graph +      │   │ local 7–8B model +   │
│ snapshots, healing scorer        │                   │ vector index │   │ embeddings           │
└───────────────┬──────────────────┘                   └──────────────┘   └──────────────────────┘
  UI Automation │                                       CI runner (Windows): CLI runner + headless
 Application under test (AUT)                           agent; suites from the server or a file;
                                                        writes JUnit XML
```

- Only the agent touches the AUT, and it runs on the AUT's machine because the Spy needs that screen.
- The server is the only caller of the AI service, and only while a test is written. Playback never calls a model.
- No component calls anything outside the closed network.

**Relation to other tools.** The comparison matrix (`docs/tool-matrix.md`, #18) covers TestComplete, Ranorex and UFT One [2][4][5]. All three have a recorder, a spy, an object repository, keyword tests and reports, but they are licensed per seat or concurrent user. All three heal during the run, so a healed step can pass against the wrong object. TestComplete's OCR-based healing calls a SmartBear web service [6], which rules it out on a closed network. FlaUI and pywinauto [7][8] give programmatic UI Automation access with no repository, codeless editor or healing; AYNA uses pywinauto as its recognition layer. Most record/replay breakages come from how elements are located [9], so AYNA's tests refer to logical names in a repository, never to locators.

**State at the time of writing (week 5, version 1.0).** The walking skeleton ran end to end on Windows in week 3 (G0, #28): Spy, repository in Neo4j, playback by logical name. Since then the contracts were frozen as v1 (#52); playback has all six keywords with smart waits (#40), a screenshot per step (#54) and failure categories with a decision log (#63); the client runs a test from the editor with live step status (#44); the server writes the HTML run report (#59); and the CLI runner `ayna run` plays a suite headless (#61). The sample app and its controlled-change and bug-injected versions exist (#33, #46, #47). Healing (#42, #43, #73–#75), the NL assistant's end-to-end path (#71, #78) and change impact (#81) are still to come. The RS describes the semester-1 target, not this state.

#### 1.3.2 Product functions

- **Object recognition and Object Spy** (§3.2.1). The agent reads the AUT's UI Automation tree and describes each element by several properties (AutomationId, Name, ControlType, ClassName, parent path, nearest label, bounds), with a win32 fallback. In the client's Spy, the user picks an element with a hotkey and sees it outlined. A whole window can be captured as a snapshot of one application version.
- **Object repository** (§3.2.2). Elements get stable logical names (`screen.element`) with primary and fallback properties, stored in Neo4j. Tests refer only to these names, so a UI change means updating the repository, not the tests.
- **Test authoring** (§3.2.3). A test is an ordered list of steps in one versioned JSON schema with five keywords: Click, Type, Select, Verify, Wait. The codeless editor builds and checks them; tests can be exported and imported as files.
- **Playback** (§3.2.4). The agent plays steps by logical name. Before every step it waits until the element exists, is visible and is enabled, up to a timeout. It checks property checkpoints and takes a screenshot after each step.
- **Runs, reports and CLI runner** (§3.2.5). Live step status in every client that has the test open, run history, an HTML report with a screenshot per step, and a headless CLI runner that writes JUnit XML for CI.
- **Turkish NL assistant, C1** (§3.2.6). A Turkish description becomes suggested steps. They are grounded in the repository, validated against the schema and the repository, and saved only when the user accepts them.
- **Self-healing proposals, C2** (§3.2.7). When an element is not found, the step ends as "repair proposed" with the top 3 candidates and each property's contribution to their scores. The repository changes only when a reviewer approves.
- **Change-impact analysis, C3** (§3.2.8). Between two application versions: the changed objects, the tests that use them and the pending healing proposals.
- **Failure triage and decision log** (§3.2.9). Rules give each failed step one category. Every decision is logged as a labelled example for the semester-2 decision layer.
- **Applications, users and settings** (§3.2.10). Server connection, applications and versions, local accounts with the roles admin and tester.

#### 1.3.3 User characteristics

Users are Turkish-speaking testers and test engineers in a defence or public-sector test unit; most are not programmers. The roles (ROLE-n) are those of the requirements workshop (#19):

| ID | Role | Who and skill | What they do in AYNA | Account role (#60) |
|---|---|---|---|---|
| ROLE-1 | Test author | Tester or domain expert; knows the AUT, need not program | Inspects screens with the Spy, names elements, builds tests in the editor or from Turkish text, runs them | tester |
| ROLE-2 | Test engineer | Owns the tests of one AUT; comfortable with build versions and CI | Registers versions, maintains the repository, reads reports and failure categories, checks change impact, sets up CI | tester |
| ROLE-3 | Healing reviewer | A test engineer who decides on repairs | Approves or rejects healing proposals; an approval changes the repository and becomes a rule | tester (Q1) |
| ROLE-4 | Administrator | Runs IT for the test unit; Docker and Windows administration | Installs and operates the backend and the clients on the closed network; manages accounts | admin |
| ROLE-5 | CI pipeline | System actor | Runs a suite with the CLI runner and a headless agent on every build | service account with an API token (TBD-10, closed) |

- In semester 1, ROLE-1 to ROLE-3 are responsibilities, not separate accounts, and one person may hold all three.
- The AUT is a passive system actor.
- The advisor, the HAVELSAN mentor, the AUT's development teams (who receive the testability guideline, #94) and researchers reusing the evaluation set (C4) are stakeholders but not users.
- The client is in Turkish and English, chosen by the user (NFR-17; TBD-2 closed). Step values, expected values and NL descriptions are Turkish (NFR-16).

#### 1.3.4 Limitations

The constraints (CON-nn) from the requirements workshop (#19) bound every design choice:

| ID | Constraint | Where it shows in the requirements |
|---|---|---|
| CON-01 | Closed network: at run time nothing calls a service outside it; model weights are bundled | NFR-29, NFR-30, NFR-36; UC-16 |
| CON-02 | Windows desktop only in semester 1, through UI Automation with a win32 fallback; driver interface kept open | NFR-19, NFR-21; OOS-01 |
| CON-03 | Turkish natural language for the NL assistant and in test data | FR-25, NFR-16, NFR-17 |
| CON-04 | No licence cost: in-house hosting, licence-free components, no per-user limit | NFR-08, NFR-23 |
| CON-05 | Language models only while a test is written; playback deterministic; generated steps target only repository objects | FR-26, FR-28, NFR-22 |
| CON-06 | Self-healing proposes and never applies a fix during a run; the repository changes only after approval | FR-29–FR-32 |
| CON-07 | Fixed architecture: Electron client with a local agent per test machine, one central server, Neo4j as the only database, product code only in Python, TypeScript and Java | FR-05, NFR-24, NFR-31 |
| CON-08 | Schedule and capacity: RS 23 Nov 2026, SDD 7 Dec 2026, demo 19 Jan 2027; about 10 hours per person per week; fixed cut order | Priority attribute (§1.5, §1.3.6) |

#### 1.3.5 Assumptions and dependencies

The requirements are achievable only if the following hold. If one fails, the listed requirement or decision is revisited.

- **The AUTs expose usable UI Automation properties.** RQ1 measures this (NFR-27). If more than 10 % of standard controls are unrecognised, D3 (#65) adds a narrow visual fallback.
- **Team hardware runs a quantised 7–8B model.** #7 measured about 5 GB per 8B Q4 model on a 16 GB laptop (NFR-13). A department GPU is requested (D2, #131) but not required.
- **The pilot apps** are open-source Windows apps on UI technologies other than the sample app's, chosen in D1 (#21) from the UIA dumps of #6: P1 is HandBrake (WPF) and P2 is KeePass 2 (WinForms). KeePassXC (Qt Widgets) may join as a third pilot once the first two run end to end (TBD-1 closed, ADR pilot apps and sample-app technology).
- **Test machines run 64-bit Windows**: so far the team's Windows 11 machine and the CI runner's Windows Server image. The versions supported for delivery stay open in TBD-3.
- **The sample app (#33)** behaves as Appendix C.2 describes; it exists as version 1.0 (PySide6), with its controlled-change (#46) and bug-injected (#47) versions.
- **Playback has an unlocked, interactive desktop.** It sends real mouse and keyboard input, so the AUT's window must be on such a desktop during a run, also on the CI runner (#67).
- **The backend host.** The closed network has an internal host that runs Docker for the backend (UC-16).
- **The HAVELSAN mentor's input** (D5) may change the target UI technology or pilot app. The default stays Windows desktop with open-source pilots.
- **The advisor agrees** the roles, use cases, constraints and out-of-scope list (#19, Q1–Q8) and the 29148 structure (Q6).
- **Licences.** Every runtime component is licence-free (NFR-23). The project's own licence is open (TBD-7).

#### 1.3.6 Apportioning of requirements

Priority (§1.5) assigns every requirement to a semester:

| Priority | Meaning | Count |
|---|---|---|
| Must | Semester 1, never cut | 35 FR, 44 NFR |
| Should | Semester 1, on the plan's cut list | 5 FR |
| Could | Semester 1 if time allows | 1 NFR (NFR-44) |
| Won't (S1) | Semester 2 or later | 1 NFR (NFR-18) |

If the team falls behind, the plan's order of cuts is fixed in advance. Each cut keeps part of its feature, and that part is Must:

| Cut | What goes | Requirements cut (to semester 2) | What stays (Must) |
|---|---|---|---|
| 1 | Change-impact view in the client | FR-34 | FR-33: the query and a text report |
| 2 | NL chat panel in the editor | FR-27 | FR-25, FR-26, NFR-12, NFR-37: the offline RQ3 measurement |
| 3 | Rule-based triage | FR-35 | FR-36: the decision log |
| 4 | CLI runner and JUnit XML | FR-23, FR-24 | — |

Never cut: Spy, repository, editor, smart-wait playback, report, the self-healing experiment and the offline NL measurement.

Semester 2 adds the items OOS-08 to OOS-11 and the issues #99–#108: recorder, checkpoints from the Spy, data-driven tests, unexpected-window handling, the calibrated decision layer (D7), the SUS study (NFR-18), a pilot on a HAVELSAN app, a TestComplete comparison, a paper and release 1.0.

### 1.4 Definitions, acronyms and abbreviations

See Appendix A.

### 1.5 Document conventions

**Identifiers.** Numbers are zero-padded to two digits (`FR-07`; three digits after 99), never reused and never renumbered. A dropped requirement stays in its table marked _Deleted_ with the reason. IDs are flat; the section a requirement sits in gives its area, so moving it between areas does not change its ID.

| Prefix | Meaning | Defined in | Filled by |
|---|---|---|---|
| `UC-xx` | Use case | Appendix B (condensed from [`docs/requirements-workshop.md`](../requirements-workshop.md)); summary in §3.1 | #19, #35 |
| `SC-xx` | Reference scenario (given / when / then) | Appendix C ([`docs/rs/scenarios.md`](scenarios.md)); summary in §3.1 | #34 |
| `FR-xx` | Functional requirement | §3.2 | #34 |
| `NFR-xx` | Non-functional requirement: performance, usability, interface, data, design constraint, quality attribute | §3.3–§3.8 | #34, #35 |
| `TBD-n` | Open value or question | Appendix E | #34, #35 |

The workshop's IDs `ROLE-n` (§1.3.3), `CON-nn` (§1.3.4), `OOS-nn` (§1.2) and `Qn` (Appendix E.2) are cited as they are. IDs that already exist in the plan keep their meaning: C1–C4 (contributions), RQ1–RQ5, H1–H3, G0–G4 (gates), D1–D7 (decision points). Issue numbers (`#nn`) are links, never requirement IDs.

**Statement form** (29148 §5.2 [40]): _"The ‹system | client | agent | server | AI service› shall ‹capability› [‹condition›] [‹measurable criterion›]."_ One requirement per statement. _shall_ = binding, _should_ = desired, _may_ = optional. No unmeasured adjectives ("fast", "user-friendly", "robust"): give a number, or write `TBD-n` and list it in Appendix E. A number that the team proposes and that no issue or plan section fixes yet is marked **"(proposed, to confirm)"**; all of them are listed under TBD-4.

**Attributes.** Every FR and NFR row has these columns; FR rows add **Scenarios** (the `SC-xx` that exercise it).

| Attribute | Values |
|---|---|
| Priority | MoSCoW, tied to the plan: **Must** = semester-1 core the plan never cuts (Spy, repository, editor, smart-wait playback, report, self-healing experiment, offline NL measurement) and closed-network operation · **Should** = semester 1, on the plan's cut list (change-impact view, NL chat panel, rule-based triage, CLI + JUnit XML) · **Could** = semester 1 only if time allows · **Won't (S1)** = semester 2 or later |
| Source | Where the requirement comes from: `UC-xx`, `CON-nn`, workshop question `Qn`, brief / plan section, ADR, literature `[n]`, issue |
| Verification | T, D, I or A (§4.1), plus where the evidence will be |

Optional: **Rationale**, only when the reason is not obvious from the source.

FR table shape (used in every §3.2 subsection; NFR tables drop the Scenarios column):

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-xx | The agent shall … | Must | UC-xx | T | SC-xx, SC-yy |

## 2 References

### 2.1 External references

Numbers follow the plan's reference list ("AYNA – 14-Week Project Plan", [1]–[39]) so that the RS, SDD and report cite each source with the same number. This section lists only the sources the RS cites; new sources start at [40]. The literature review uses other numbers for now (TBD-11).

- [2] SmartBear, TestComplete. https://smartbear.com/product/testcomplete/
- [4] OpenText, UFT One. https://www.opentext.com/products/functional-testing
- [5] Ranorex Studio. https://www.ranorex.com
- [6] SmartBear, TestComplete docs: self-healing tests. https://support.smartbear.com/testcomplete/docs/testing-with/running/self-healing-tests.html
- [7] FlaUI. https://github.com/FlaUI/FlaUI
- [8] pywinauto (UI Automation backend for Python). https://github.com/pywinauto/pywinauto
- [9] M. Hammoudi, G. Rothermel, P. Tonella, "Why do record/replay tests of web applications break?," IEEE ICST, 2016.
- [10] Q. Luo, F. Hariri, L. Eloussi, D. Marinov, "An empirical analysis of flaky tests," ACM FSE, pp. 643–653, 2014.
- [13] R. Yandrapally, S. Thummalapenta, S. Sinha, S. Chandra, "Robust test automation using contextual clues," ACM ISSTA, 2014.
- [14] M. Nass, E. Alégroth, R. Feldt, M. Leotta, F. Ricca, "Similarity-based web element localization for robust test automation," ACM TOSEM, 32(3), Art. 75, 2023.
- [24] C. Zhang et al., "UFO: A UI-focused agent for Windows OS interaction," in Proc. NAACL 2025 (Long Papers), pp. 597–622, 2025. arXiv:2402.07939
- [30] Microsoft, UI Automation Overview. https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-overview
- [31] P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," NeurIPS, 2020.
- [32] Ollama. https://ollama.com
- [33] llama.cpp (GBNF grammar-constrained decoding). https://github.com/ggml-org/llama.cpp
- [34] V. I. Levenshtein, "Binary codes capable of correcting deletions, insertions, and reversals," Soviet Physics Doklady, 10(8), pp. 707–710, 1966.
- [36] Q. McNemar, "Note on the sampling error of the difference between correlated proportions or percentages," Psychometrika, 12(2), pp. 153–157, 1947.
- [37] E. B. Wilson, "Probable inference, the law of succession, and statistical inference," JASA, 22(158), pp. 209–212, 1927.
- [38] Neo4j, Community Edition advances for graph-powered AI (vector search in Community Edition); Cypher manual: vector indexes. https://neo4j.com/docs/cypher-manual/current/indexes/search-indexes/vector-indexes/
- [39] J. Brooke, "SUS: A 'quick and dirty' usability scale," in Usability Evaluation in Industry, Taylor & Francis, 1996.
- [40] ISO/IEC/IEEE 29148:2018, _Systems and software engineering — Life cycle processes — Requirements engineering_.
- [41] JSON Schema, Draft 2020-12. https://json-schema.org/draft/2020-12
- [42] JSON-RPC Working Group, JSON-RPC 2.0 Specification. https://www.jsonrpc.org/specification
- [43] OpenAPI Initiative, OpenAPI Specification, version 3. https://spec.openapis.org/oas/

### 2.2 Project documents

| Document | Path | Issue | Status on 2026-11-19 |
|---|---|---|---|
| Project brief | [`memory-bank/project/brief.md`](../../memory-bank/project/brief.md) | — | merged |
| Architecture | [`memory-bank/project/architecture.md`](../../memory-bank/project/architecture.md) | — | merged |
| Decisions (ADRs) | [`memory-bank/decisions/README.md`](../../memory-bank/decisions/README.md) | — | merged |
| Glossary | [`memory-bank/project/glossary.md`](../../memory-bank/project/glossary.md) | — | merged |
| Requirements workshop notes | [`docs/requirements-workshop.md`](../requirements-workshop.md) | #19 | merged; §7 awaits the advisor |
| Reference scenarios (Appendix C) | [`docs/rs/scenarios.md`](scenarios.md) | #34 | merged |
| Tool comparison matrix | [`docs/tool-matrix.md`](../tool-matrix.md) | #18 | merged |
| Literature review | `docs/literature.md` | #10, #20 | PR #126 (draft) |
| Graph model | [`docs/graph-model.md`](../graph-model.md) | #14 | merged |
| Step schema | [`schemas/step.schema.json`](../../schemas/step.schema.json) | #13, #147 | 0.2 merged (#150) |
| Element and snapshot schemas | [`schemas/element.schema.json`](../../schemas/element.schema.json), [`schemas/snapshot.schema.json`](../../schemas/snapshot.schema.json) | #11, #12 | 0.1 merged (#175, #180) |
| Healing proposal schema | [`schemas/healing-proposal.schema.json`](../../schemas/healing-proposal.schema.json) | #149 | 0.2 merged (#174) |
| Agent JSON-RPC contract | [`schemas/agent-rpc.schema.json`](../../schemas/agent-rpc.schema.json), [`docs/agent-rpc.md`](../agent-rpc.md) | #16, #52 | frozen as 1.0 (#52); 1.1 adds a failed step's category (#63), 1.2 its screenshot (#54) |
| WebSocket run updates | [`schemas/ws-runs.schema.json`](../../schemas/ws-runs.schema.json) | #44, #52 | frozen as 1.0 (#52); 1.1 adds the category (#63) |
| REST API (generated) | [`docs/api/openapi.yaml`](../api/openapi.yaml) | #31, #52 | frozen as v1 (#52); additive changes since |
| Software Design Description | [`docs/sdd/SDD.md`](../sdd/SDD.md) | #45, #48, #50, #53 | v0.5 merged (#242); final due 7 Dec (#53) |
| Sample app and its versions | [`eval/apps/sample/`](../../eval/apps/sample/README.md) | #33, #46, #47 | 1.0 merged, with the controlled-change and bug-injected versions |
| NL dataset and guideline | [`eval/nl/guideline.md`](../../eval/nl/guideline.md) | #36, #57 | guideline merged; the 40 sample-app pairs in progress (#36) |
| RQ1 recognition report | [`eval/rq1/report.md`](../../eval/rq1/report.md) | #64 | first report merged (#253) |
| NL latency on Windows | [`eval/llm-latency/report.md`](../../eval/llm-latency/report.md) | #162 | merged (#235) |

## 3 Requirements

### 3.1 Use cases and reference scenarios

The full use cases are in Appendix B and the full scenarios in Appendix C. Priority: **Must** use cases are not in the plan's cut order. For a **Should** use case, the cut number gives its place in that order (§1.3.6).

| ID | Use case | Primary actor | Priority |
|---|---|---|---|
| UC-01 | Connect to the server and register an application version | ROLE-2 | Must |
| UC-02 | Inspect an element with the Object Spy | ROLE-1 | Must |
| UC-03 | Add an element to the object repository | ROLE-1 | Must |
| UC-04 | Maintain the object repository | ROLE-2 | Must |
| UC-05 | Capture a snapshot of an application version | ROLE-2 | Must |
| UC-06 | Build a test in the codeless editor | ROLE-1 | Must |
| UC-07 | Add a property checkpoint | ROLE-1 | Must |
| UC-08 | Write steps from a Turkish description | ROLE-1 | Should (cut 2; FR-25, FR-26 stay Must) |
| UC-09 | Run a test and watch it live | ROLE-1, ROLE-2 | Must |
| UC-10 | Read the run report and run history | ROLE-2 | Must |
| UC-11 | See the failure category of a failed step | ROLE-2 | Should (cut 3; FR-36 stays Must) |
| UC-12 | Approve or reject a healing proposal | ROLE-3 | Must |
| UC-13 | See which tests a new version affects | ROLE-2 | Should (cut 1; FR-33 stays Must) |
| UC-14 | Run a suite headless in CI | ROLE-5 | Should (cut 4) |
| UC-15 | Manage user accounts | ROLE-4 | Must |
| UC-16 | Install and run AYNA on a closed network | ROLE-4 | Must |

Reference scenarios. AUT codes (Appendix C.2): **SA** sample app v1.0 (#33), **SA-C** its controlled-change versions (#46), **SA-B** its bug-injected versions (#47), **P1, P2** pilot apps (#21). Kind: _main_ flow, _negative_ (an error or rejected input) or _edge_ (a boundary condition).

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

### 3.2 Functional requirements

Every FR lists at least one scenario (checked in §5.3).

#### 3.2.1 Object recognition and Object Spy

The agent reads the AUT through UI Automation [30] with pywinauto [8]; the Spy is the client's view of it.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-01 | The agent shall return, for a given screen point, the element under it with its descriptor (AutomationId, Name, ControlType, ClassName, FrameworkId, parent path, index in parent, nearest label, enabled, offscreen) and its screen bounds. | Must | UC-02; Core 1; #11, #22 | T — Windows test (#22) | SC-04, SC-05, SC-06 |
| FR-02 | The client's Object Spy shall show the element tree of a chosen window and every descriptor field of the selected element, outline the selected element on screen, and select the element under the mouse cursor when the user presses the global pick hotkey. | Must | UC-02; #24 | D — weekly Windows session | SC-04, SC-05, SC-06 |
| FR-03 | When UI Automation gives an element neither an AutomationId nor a Name, the agent shall read the same element through the win32 backend and add the win32 properties to its descriptor, each marked with its source. | Must | UC-02; Core 1; #23 | T — Windows test (#23) | SC-07 |
| FR-04 | The system shall capture a window's whole element subtree as one snapshot that validates against `schemas/snapshot.schema.json` and store it as Window and Element nodes under an application version; importing the same snapshot id again shall leave the graph unchanged. | Must | UC-05; #12, #15 | T — agent test, server integration test | SC-09, SC-32 |
| FR-05 | The client shall start the local agent when it starts and stop it when it quits, restart it automatically up to 3 times after an unexpected exit, and show its status as connected, restarting or failed. | Must | UC-02, UC-09; CON-07; #17 | T + D | SC-08 |

#### 3.2.2 Object repository

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-06 | The system shall let the user add a picked element to the repository under a logical name of the form `screen.element`, with primary and fallback property sets the user can edit before saving, and shall link the new repository object to that element for the current application version. | Must | UC-03; Core 2; #25 | T + D | SC-07, SC-10, SC-11 |
| FR-07 | The server shall reject a logical name that already exists in the same application, with a message that names the existing object. | Must | UC-03; ADR graph schema v0.1; #25 | T | SC-11 |
| FR-08 | The client's repository view shall let the user search, rename and edit repository objects, and shall show for each object the number of tests that use it, computed from the graph; renaming an object shall keep every step that targets it, without editing those steps. | Must | UC-04; ADR graph schema v0.1; #30, #39 | T + D | SC-12, SC-13 |
| FR-09 | The server shall refuse to delete a repository object that any test step targets, and the refusal shall name those tests. | Must | UC-04; #30 | T | SC-13 |
| FR-10 | The agent shall locate a step's target by the repository object's primary properties and, when they match no element, by its fallback properties; a test shall refer to its targets only by logical name, never by coordinates or raw UI Automation properties. | Must | UC-09; Core 2; #26; step schema (#13) | T | SC-12, SC-14, SC-17, SC-29 |

#### 3.2.3 Test authoring: steps and codeless editor

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-11 | The system shall store every test as an ordered list of steps that validates against the versioned step schema (`schemas/step.schema.json`), whose keywords are Click, Type, Select, SelectRow, Verify and Wait (schema 0.2; a 0.1 document becomes 0.2 by its version field alone). | Must | UC-06; Core 3; #13, #147 | T + I | SC-14, SC-20, SC-26 |
| FR-12 | The client's editor shall let the user create a test and add, delete, edit and drag to reorder its steps, choosing each keyword from a list and each target from the repository, without typing JSON. | Must | UC-06; #38 | D | SC-14, SC-20 |
| FR-13 | The client shall highlight a step that does not validate against the step schema, with the reason, and the server shall reject such a step with HTTP 400 and the path of the failing field. | Must | UC-06; #38, #39 | T | SC-15 |
| FR-14 | The system shall export a test as a JSON file and import such a file; an export followed by an import shall give an identical test. | Must | UC-06, UC-14; #39 | T | SC-14, SC-34 |
| FR-15 | The system shall let the user add a Verify step with a property of the target (name, value, enabled, visible, checked, selected) or of a grid or list target (the text of a cell addressed by row and column, whether a row exists, the number of rows), an operator (equals, notEquals, contains; only equals for booleans and the row count) and an expected value; the agent shall pass or fail the step on that comparison and, on failure, report the expected and the actual value. A row is addressed by its 1-based position or by the exact text of one of its cells. Row and cell checks are re-read until they hold, within the step's timeout. | Must | UC-07; Core 4; #13, #40, #147 | T | SC-14, SC-16, SC-21 |

#### 3.2.4 Playback, smart waits and checkpoints

Readiness-based waits replace fixed sleeps because timing is a leading cause of flaky results [10].

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-16 | Before acting on a step, the agent shall wait until the target element exists, is visible and is enabled, for at most the step's `timeoutMs` or else the run's default timeout, by polling and never by a fixed sleep. | Must | UC-09; Core 4; #40 | T — includes a control that appears after 3 s (#40) | SC-18, SC-19, SC-20 |
| FR-17 | When the wait ends without a ready element, the agent shall fail the step with a message that names the logical name, the time waited in milliseconds and the readiness condition that was not met. | Must | UC-09; #40 | T | SC-19, SC-29 |
| FR-18 | The agent shall perform Click, Type (replacing the control's text), Select (choosing an item by its text), SelectRow (selecting a grid or list row addressed as in FR-15, after waiting for the row within the step's timeout) and Wait as defined in the step schema. | Must | UC-09; #40; step schema (#13, #147) | T — one test per keyword (#40) | SC-17, SC-20, SC-23 |
| FR-19 | After each step the agent shall capture a PNG of the AUT's window, cropped to that window, and return it with the step result. | Must | UC-09, UC-10; #54 | T | SC-17, SC-24 |

#### 3.2.5 Runs, reports and CLI runner

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-20 | The system shall run a test from the editor on the local agent, show each step's status live in the client, store the run and its step results on the server, and show the same live status in every other client that has the test open. | Must | UC-09; #44, #51 | T + D | SC-17 |
| FR-21 | The server shall produce an HTML report for every run — a summary, a step table with status, duration and error, and a screenshot per step — downloadable as one self-contained file that opens in a browser with no network. | Must | UC-10; Core 5; #59 | T | SC-24, SC-36 |
| FR-22 | The client shall list runs with their test, status, duration and user, filter them by test and status, and open a run's report. | Must | UC-10; #68 | D | SC-03, SC-24 |
| FR-23 | The CLI runner shall run a suite with a headless agent, either from the server (`--server URL --suite NAME`) or from a file (`--from-file`). When a server is given, it shall authenticate with an API token passed in `AYNA_SERVER_TOKEN` as a Bearer token and post the results to that server. It shall exit with 0 when every test passes and every result is delivered, 1 when a test fails or proposes a repair, and 2 on an operational failure (results not delivered, token refused, server unreachable), even if every test passed. | Should | UC-14; ADR healing proposal transport; #60, #61 | T | SC-33, SC-34 |
| FR-24 | The CLI runner shall write its results as JUnit XML that validates against the JUnit schema. | Should | UC-14; #66, #67 | T — schema check and the CI job of #67 | SC-33, SC-34 |

#### 3.2.6 Turkish NL assistant (C1)

Generation is grounded in retrieved repository context [31] and constrained to the step schema [33]. FR-25 and FR-26 are Must because the plan never cuts the offline NL measurement (RQ3), which needs them. The chat panel (FR-27) is second in the cut order, so it is Should.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-25 | The AI service shall turn a Turkish test description, given with the current application and screen, into suggested steps in the step schema, using the current screen's subgraph and the closest repository objects as context, and shall give a short reason for each step. | Must | UC-08; C1; CON-03; #58, #71 | T + A — RQ3 (#77) | SC-26, SC-36 |
| FR-26 | The AI service shall drop every generated step whose target is not an object in the application's repository or that does not validate against the step schema, and shall return only validated steps, with the reason for each dropped step. | Must | UC-08; CON-05; ADR LLM authoring-only; #71 | T — stub-model test | SC-27 |
| FR-27 | The client's NL panel shall show suggested steps for review, let the user edit them and accept them all or one by one, save nothing before the user accepts, and add accepted steps to the test as ordinary steps; while the AI service cannot be reached, the panel shall be disabled with a message that says so. | Should | UC-08; #78 | D | SC-26, SC-28 |
| FR-28 | The system shall provide every function other than NL step generation — Spy, repository, editor, runs, reports, healing, change impact and CLI runner — while the AI service is stopped. | Must | UC-08; CON-05; ADR LLM authoring-only | T + D | SC-28 |

#### 3.2.7 Self-healing proposals and approval (C2)

The score follows Similo's weighted multi-property similarity [14]: Levenshtein text similarity [34] plus graph-context features such as parent, siblings and nearest label [13]. Unlike TestComplete [6], it is never applied during a run.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-29 | When no element matches a step's target after the wait and the search covered the whole of the step's own window, the agent shall score the candidate elements in the same window with a compatible control type using the weighted similarity S(c, t) = Σ wᵢ · simᵢ(c, t) / Σ wᵢ, and shall end the step as "repair proposed" with the top 3 candidates and each property's contribution to their scores. It shall never start healing when more than one element matches (an ambiguous match), when the step's window is not the one in front (unexpected window), on a timeout or after an incomplete search (FR-35). | Must | UC-12; C2; CON-06; #42, #43, #49, #73 | T — scorer unit tests (#49), A — RQ4 (#76) | SC-29, SC-31 |
| FR-30 | The agent shall never perform a step on a healing candidate: after a "repair proposed" step it shall stop the test, mark the remaining steps as not run (TBD-6), and hand the proposal with the step result to the client or the CLI runner, which delivers it to the server (FR-20, FR-23); the agent itself never connects to the server. | Must | UC-12; CON-06; ADR approval-gated healing; ADR healing proposal transport; #73 | T | SC-29, SC-31 |
| FR-31 | The client shall show a healing proposal — the failing step, the top 3 candidates with per-property contribution bars and an on-screen outline of the selected candidate — open it from the run report, and let the reviewer approve one candidate or reject all. | Must | UC-12; #75 | D | SC-30, SC-31 |
| FR-32 | When a proposal is approved, the server shall make the repository object resolve to the chosen element for that application version and create a Rule linked to the proposal; when all candidates are rejected, it shall keep the step failed and leave the repository unchanged. | Must | UC-12; CON-06; #74 | T | SC-30, SC-31 |

#### 3.2.8 Change-impact analysis (C3)

The plan cuts the change-impact view first but keeps "the Cypher query and a text report", so the query (FR-33) is Must and the view (FR-34) is Should.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-33 | The server shall return, for two versions of an application, the repository objects whose element changed between their snapshots, the tests whose steps target those objects, and the pending healing proposals for those objects. | Must | UC-13; C3; #81 | T — against the ground truth of #46 | SC-32 |
| FR-34 | The client's change-impact view shall let the user choose two versions and show the result with a link to each affected test. | Should | UC-13; #81 | D | SC-32 |

#### 3.2.9 Failure triage and decision log

The plan cuts rule-based triage third but keeps the decision log, so classification (FR-35) is Should and the log (FR-36) is Must.

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-35 | The agent shall put every failed step, except the two kinds named at the end of this requirement, in exactly one category — element not found, unexpected window, assertion failed, timeout or search incomplete (TBD-5) — and the client shall show the category with the step. "Search incomplete" means that the search for the target, or the window's snapshot, ran out of its time budget before it covered the whole window; such a step never starts healing. More than one matching element is "element not found", because playback never picks one of several. "Unexpected window" means that the step's own window is not open or not in front while another window of the application is, such as a modal dialog (SC-22); it takes precedence over "element not found". A step the agent refuses (a keyword or step document it cannot carry out) and an action the application rejects on a found, ready element are not evidence about the application under test, so they carry no category; the decision log records a finer reason for them (FR-36). | Should | UC-11; #63; ADR failure-category | T | SC-19, SC-21, SC-22, SC-25 |
| FR-36 | The system shall log every failure decision (the failed step, its category, any healing proposal and its outcome) with its context, and shall export the log as JSONL. | Must | UC-11; ADR decision layer in semester 2; #63 | T | SC-25, SC-31 |

#### 3.2.10 Projects, applications, users and settings

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-37 | On first run the client shall ask for the server URL, show an error that names the URL when no AYNA server answers there, and remember the server and the chosen application on that machine between restarts. | Must | UC-01; #32 | T + D | SC-01, SC-02 |
| FR-38 | The server shall create and list applications and their versions, and reject a duplicate application name or a duplicate version of one application with HTTP 409. | Must | UC-01; #128 | T — integration test | SC-01 |
| FR-39 | The server shall provide local user accounts with the role admin or tester, allow only admins to create, change or remove accounts, and allow admins to create and revoke API tokens for a CI service account. | Must | UC-15; #60 | T | SC-03 |
| FR-40 | The server shall store the id of the acting user with every test edit, run and healing decision. | Must | UC-15; #60, #74 | T | SC-03, SC-30 |

### 3.3 Performance requirements

Numbers taken from an issue or the plan cite it. Every other number is marked "(proposed, to confirm)" and listed under TBD-4, or "team-confirmed" with the issue where its owner confirmed it, until the advisor answers Q5. Memory is constrained only for the local model (NFR-13).

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-01 | The agent shall return the element under a screen point (Spy pick) within 300 ms. | Must | UC-02; #22 | T — Windows test (#22); SC-04 |
| NFR-02 | The agent shall export the snapshot of one sample-app window within 2 s (#12 sets 2 s for the trial app; for every sample-app window team-confirmed, #143; advisor Q5 pending). The bound is a property of the sample app, not of every application: the #6 dumps took 1.97 s for a 149-element WPF window and 278.5 s for a 106-element WinForms one. #161 traced that outlier to a modal message box left open in the application, which blocks cross-process UI Automation calls; a longer budget does not help there, and a walk that runs out of its budget ends as "search incomplete" (FR-35). | Must | UC-05; #6, #12, #161 | T — SC-09 |
| NFR-03 | Capturing a step's screenshot shall add less than 300 ms to the step. | Must | #54 | T |
| NFR-04 | Timed from the end of the smart wait to the return of the action, and leaving out the screenshot, the agent shall complete a step within 500 ms (proposed, to confirm). Re-reads of a checkpoint that is repeated until it holds, within the step's timeout (grid-row checks, #147), count as waiting, not as the step. | Must | UC-09 | T — timings in the playback tests (#40) |
| NFR-05 | A step without `timeoutMs` shall wait at most 10 000 ms (team-confirmed, #143; advisor Q5 pending); the default shall be configurable per run, and `timeoutMs` per step from 0 to 600 000 ms, where 0 means check once without waiting, not "use the default". | Must | UC-09; #40; step schema (#13) | T |
| NFR-06 | A step's status shall appear in every client that has the test open within 1 s of the agent's step result (team-confirmed, #140; advisor Q5 pending). | Must | UC-09; #44 | T + D — SC-17 |
| NFR-07 | The server shall answer 95 % of REST requests, other than report downloads, snapshot imports and screenshot uploads, within 500 ms under the load of NFR-08 (team-confirmed, #140; confirmed by the load test, #152; advisor Q5 pending). | Must | Q5 (#19) | T — load test (#152): met on 2026-11-10, 100.0 % within 500 ms, overall p95 31.9 ms, 0 errors (`server/loadtest/results/2026-11-10-apple-m3.md`; method in `server/loadtest/README.md`) |
| NFR-08 | One server shall serve at least 10 clients working at the same time, with at least 1 000 repository objects and 500 tests per application (team-confirmed, #140; confirmed by the load test, #152; advisor Q5 pending). | Must | Q5 (#19); CON-04 | T — load test (#152): 10 clients without pauses, 1 000 objects and 500 tests of 10 steps in one application, on one Apple M3 with server and Neo4j in 4 CPUs / 4.1 GiB (`server/loadtest/results/2026-11-10-apple-m3.md`). Not covered: WebSocket (NFR-06), and the load generator ran on the server's machine |
| NFR-09 | The server shall generate the HTML report of a 50-step run within 5 s (team-confirmed, #140; advisor Q5 pending). | Must | UC-10; #59 | T |
| NFR-10 | Healing candidates for one repository object shall be generated within 1 s. | Must | UC-12; #42 | T — SC-29 |
| NFR-11 | A retrieval query for NL context (vector top-k plus the current screen's subgraph) shall return within 200 ms. | Must | UC-08; #58 | T |
| NFR-12 | The p95 latency of NL step generation per scenario on team hardware shall be measured and reported; semester 1 commits to no target value. Measured so far on ten sentences, so indicative only: p95 25.3 s on an Apple M2 laptop under load (#71), and 41–43 s on a CPU-only Windows laptop with per-step reasons on (#162). The AI service's request deadline is therefore 60 s, not a latency target. | Must | UC-08; plan success criteria; #71, #77, #162 | A — RQ3 report (#77); `eval/llm-latency/report.md` (#162) |
| NFR-13 | The AI service shall run its quantised 7–8B model and its embedding model on a machine with 16 GB RAM and no GPU (proposed, to confirm; #7 measured about 5 GB per 8B Q4 model on a 16 GB laptop). | Must | D2; #7, #131 | A + D |
| NFR-37 | With repository context, NL step generation shall reach at least 60 % step-level accuracy on the frozen held-out split (30 of the 100 Turkish NL/step pairs) at the end of semester 1, step-level accuracy as defined in the dataset guideline (#36). | Must | UC-08; RQ3, H2; brief success criteria; #57, #77 | A — RQ3 report with Wilson CI (#77) |

### 3.4 Usability requirements

AYNA's users are mostly not programmers (§1.3.3), so the requirement is codeless operation end to end (NFR-14). Usability is measured with a SUS study [39] in semester 2 (#104); semester 1 checks it by demonstration at the weekly sessions and gates.

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-14 | A user shall be able to inspect elements, maintain the repository, build tests with checkpoints, run them, read reports and decide on healing proposals in the client without writing code or typing JSON. | Must | brief; ROLE-1; UC-02–UC-04, UC-06, UC-07, UC-09, UC-10, UC-12 | D — SC-14, SC-17, SC-30 at the weekly session |
| NFR-15 | Every error shown to the user shall name the step, repository object, field or URL it concerns. | Must | #25, #32, #39, #40 | I — review of messages; T where an issue fixes the text (#39, #40) |
| NFR-16 | The system shall accept, store, show and replay Turkish characters (ç, ğ, ı, İ, ö, ş, ü) in test names, step values, expected values and NL descriptions without change. | Must | CON-03 | T — SC-20, SC-26 |
| NFR-17 | The client's labels and messages shall be available in Turkish and in English, in the language the user chooses; the choice applies at once and is kept on the machine (TBD-2 closed: team decision 2026-11-03, ADR client-ui-language, #185). | Must | CON-03; Q4 (#19); #185 | I, T — a client test keeps the two dictionaries in step |
| NFR-18 | In a SUS study with non-programmer users, AYNA shall score at least 68 (proposed, to confirm). | Won't (S1) | brief; #104 | A — SUS study, semester 2 (#104) |

### 3.5 Interface requirements

This section states what crosses each interface and in which direction. The message formats are in the contract documents (§2.2) and the SDD.

#### 3.5.1 User interfaces

The client is one desktop window per test machine. The screens and the requirements behind them (layouts and wireframes are in the SDD):

| Screen | What the user does there | Requirements | Issue |
|---|---|---|---|
| First run and server settings | Enter the server URL, choose the application and version | FR-37, FR-38 | #32 |
| Login and user management | Log in; admins manage accounts | FR-39 | #60 |
| Object Spy | Pick with the hotkey, browse the element tree, read the descriptor, add to the repository | FR-02, FR-03, FR-06 | #24 |
| Repository view | Search, rename, edit, see usage | FR-08, FR-09 | #30 |
| Test editor | Build steps and checkpoints, pick targets, see validation errors, import and export | FR-12, FR-13, FR-14, FR-15 | #38, #39 |
| NL panel | Describe steps in Turkish, review, edit, accept | FR-27 | #78 |
| Live run status | Watch step status during a run | FR-20 | #44 |
| Run history and report | Filter runs, open and download the HTML report | FR-21, FR-22 | #59, #68 |
| Healing approval | Compare candidates, approve one or reject all | FR-31 | #75 |
| Change impact | Choose two versions, follow links to affected tests | FR-34 | #81 |
| Agent status indicator | See whether the local agent is connected | FR-05 | #17 |

Rules that apply to every screen: no code or JSON (NFR-14), errors that name their subject (NFR-15), Turkish text kept intact (NFR-16), one UI language at a time, the user's choice (NFR-17), and correct picking and outlining under display scaling:

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-20 | Picking, outlining and playback shall be correct at 100 % and 150 % display scaling. | Must | #22 | T — Windows test (#22); SC-05 |

#### 3.5.2 Hardware interfaces

AYNA needs no special hardware.
- **Test machine.** A standard x64 Windows PC with a display, keyboard and mouse, running the client, the agent and the AUT. Display scaling of 100 % and 150 % is supported (NFR-20). Several monitors, or monitors with different scaling, are not a semester-1 requirement.
- **Backend host.** An x64 machine on the closed network that runs Docker (UC-16).
- **AI service.** Runs on 16 GB RAM without a GPU (NFR-13). A GPU, if the department grants one (D2, #131), only shortens generation time (NFR-12).

#### 3.5.3 Software interfaces

| Software | Version | Used by | For |
|---|---|---|---|
| Windows, 64-bit | TBD-3 (NFR-19) | client, agent, AUT | Operating system of test machines and CI runners |
| Microsoft UI Automation [30] through pywinauto's `uia` backend, and win32 through its `win32` backend [8] | Pinned in `agent/pyproject.toml` when the recognition work adds it (#11, #12) | agent | Reading the AUT's element tree, input, properties (FR-01, FR-03, FR-18) |
| Neo4j Community Edition, including its vector index [38] | 5.26 (`neo4j:5.26-community` in `docker-compose.yml`) | server | The only database (NFR-24), over Bolt |
| Ollama [32] or llama.cpp [33] with a quantised 7–8B open-weight model and an embedding model | Model chosen in D4 (#80); names and licences documented (#82) | AI service | NL step generation with grammar-constrained JSON output; embeddings for retrieval (FR-25, NFR-11) |
| Docker Engine with Compose | Pinned in the offline bundle (#84) | backend host | One `docker compose up` for server, Neo4j and AI service (NFR-36) |
| CI systems that read JUnit XML; GitHub Actions with a Windows runner for AYNA's own CI | — | CLI runner | Test results in CI (FR-24, #67) |
| Web browser | Any current browser, offline | report reader | Opening the self-contained HTML report (FR-21) |

#### 3.5.4 Communication interfaces

Every interface stays inside the closed network (NFR-29). JSON is UTF-8.

| Interface | Direction and binding | What is exchanged | Contract | Requirements |
|---|---|---|---|---|
| Client ↔ server | REST over HTTP; WebSocket from server to clients for live run status; session after login | Applications and versions, repository objects, snapshots, tests, runs and step results, reports, healing proposals and decisions, change impact, users | `docs/api/openapi.yaml`, generated (#31), frozen as v1 (#52); live run status in `schemas/ws-runs.schema.json` | FR-20, FR-38, NFR-06, NFR-07, NFR-32, NFR-34 |
| Client ↔ agent | JSON-RPC 2.0 [42] over one WebSocket on 127.0.0.1; the client starts the agent and passes a per-session token in an environment variable; only the client's main process connects | Window list, element under a point, snapshots, highlight, steps to play, step results with screenshots | `schemas/agent-rpc.schema.json` and `docs/agent-rpc.md` (#16; frozen as 1.0 at #52, now 1.2: `ping`, `listWindows`, `snapshot`, `elementFromPoint`, `runSteps`) | FR-05, NFR-31, NFR-34 |
| Agent → server (through the client, or the CLI runner) | Documents in the element, snapshot and healing-proposal schemas; the agent never connects to the server itself | Snapshots of a window per application version; step results, with the healing proposal of a "repair proposed" step (`PUT /api/runs/{runId}/results/{stepIndex}`) | `schemas/element.schema.json`, `schemas/snapshot.schema.json` (#11, #12), `schemas/healing-proposal.schema.json`; ADR healing proposal transport | FR-04, FR-20, FR-30 |
| CLI runner ↔ server | REST, started by the CLI runner; an API token of a CI service account in `AYNA_SERVER_TOKEN`, sent as a Bearer token (#60) | Suites to run; results to store | REST contract | FR-23, NFR-32 |
| Server → AI service | HTTP, called only by the server and only while a test is written | Description, application and screen → suggested and dropped steps; texts → embeddings | Defined in the SDD AI sections (#50) | FR-25, FR-26, NFR-22 |
| Server ↔ Neo4j | Bolt, Spring Data Neo4j | The graph (§3.6) | [`docs/graph-model.md`](../graph-model.md) and the migrations (#14) | NFR-24, NFR-41 |

### 3.6 Logical database requirements

The graph ([`docs/graph-model.md`](../graph-model.md), #14) holds what AYNA must keep:
- applications and their versions;
- each version's windows and elements, as captured in snapshots;
- repository objects, with their per-version resolution and embeddings in Neo4j's vector index [38];
- tests and their ordered steps (shape: `schemas/step.schema.json`);
- runs and step results;
- healing proposals with their candidates, and rules;
- users.

Screenshots are files on the server disk.

Integrity rules stated elsewhere:
- a logical name is unique per application (FR-07);
- a used repository object cannot be deleted (FR-09);
- a snapshot import is idempotent (FR-04);
- every edit, run and decision records its user (FR-40);
- passwords are stored as bcrypt hashes (NFR-32);
- retention keeps the last N runs (NFR-28).

Expected volume per application: 1 000 repository objects and 500 tests (NFR-08).

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-38 | Every node in the graph shall have an `id` property holding a UUID generated by the server, unique per label; Neo4j's internal element id shall never be stored or exposed by an API. | Must | ADR graph schema v0; #14 | T — migration and repository tests (#14) |
| NFR-39 | The server shall keep the snapshots of each application version apart: importing a snapshot of one version shall not change or remove the Element nodes of any other version. | Must | UC-05, UC-13; C3; #15 | T — server integration test (#15); SC-32 |
| NFR-40 | The server shall store screenshots as files on its disk and only their paths in the graph; when the retention setting (NFR-28) removes a run, its screenshot files shall be removed with it. | Must | UC-10; ADR Neo4j; #51 | T (#51) |
| NFR-41 | The graph schema shall change only through new versioned migration files that the server applies automatically at start; an applied migration file shall never be edited. | Must | ADR graph schema v0; #14 | I — PR review; T — migration test (#14) |

### 3.7 Design constraints

The accepted decisions ([ADR index](../../memory-bank/decisions/README.md)) that bind the design, and where they become requirements:

| Decision | Requirements |
|---|---|
| Technology stack; client in TypeScript | NFR-24 |
| Neo4j as the single database | NFR-24, §3.6 |
| Electron client per test machine, one central server | FR-05, NFR-31 |
| Windows desktop only in semester 1 | NFR-19, NFR-21 |
| Language models only at authoring time (run-time model decisions, as in UFO [24], are not repeatable) | FR-26, FR-28, NFR-22 |
| Self-healing proposes, never applies mid-run | FR-29–FR-32 |
| Calibrated decision layer moves to semester 2 | FR-35, FR-36; OOS-11 |
| Graph schema v0: migrations and UUID ids | NFR-38, NFR-41 |

Contracts are frozen at G1 (NFR-34, #52). Standards complied with: 29148 for this document [40], and those in NFR-42.

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-22 | The agent and the CLI runner shall call no language model and not the AI service during a run; a run shall give the same result with the AI service stopped. | Must | CON-05; ADR LLM authoring-only | I — code review; T — SC-28 |
| NFR-23 | Every component AYNA ships or needs at run time shall be free of per-user licence cost, and the model names and licences shall be documented. | Must | CON-04; #82 | I |
| NFR-24 | Neo4j Community Edition shall be the only database, and product code shall be written only in Python, TypeScript and Java. | Must | CON-07; ADRs stack, Neo4j, client TypeScript | I |
| NFR-42 | The contracts shall use open standards: JSON Schema draft 2020-12 [41] for the step, element and snapshot schemas, JSON-RPC 2.0 [42] for the agent contract, an OpenAPI 3 document [43] generated from the server code for the REST contract, and JUnit XML for the CLI runner's results. | Must | architecture "Contracts"; #13, #16, #31, #66 | I — contract review at G1 (#52) |

### 3.8 Software system attributes

#### 3.8.1 Reliability

Playback is deterministic: no model at run time (NFR-22), smart waits instead of fixed sleeps (FR-16), and tests bound to logical names (FR-10).

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-25 | Over 10 runs of each of at least 10 reference scenarios, the flaky rate shall be below 10 % at the end of semester 1 and below 5 % at the end of the project. | Must | RQ2; brief success criteria; #69 | A — RQ2 report with Wilson CI (#69) |
| NFR-26 | At least 10 reference scenarios built in the editor shall replay end to end without manual fixes by G2. | Must | RQ2; G2; #55, #62 | D + A — SC-17, SC-23; #55 |
| NFR-27 | At least 90 % of the standard controls in the pilot apps shall be recognised by multi-property identification. | Must | RQ1; brief success criteria; #64 | A — RQ1 report (#64); SC-06 |
| NFR-28 | The server shall store 100 consecutive runs, each step with a retrievable screenshot, without errors, and shall keep only the last N runs, N being configurable. | Must | #51 | T |

#### 3.8.2 Availability

AYNA runs in-house for one test unit, so semester 1 sets no uptime percentage. What is required is that a failing part takes down as little as possible:
- **AI service down.** Everything except NL generation keeps working (FR-28), and the NL panel says the service is unreachable (FR-27).
- **Agent crash.** The client restarts it up to 3 times and then shows "failed" (FR-05).
- **Client crash.** The agent exits when the client's stdin pipe closes, which the OS does when the client quits or crashes, so no agent stays bound to the AUT (`docs/agent-rpc.md`; #17, #135).
- **Server unreachable during a run.** Playback goes on; the client keeps the finished results in its outbox and sends them when the server is back; a result the server refuses as invalid is set aside and shown, so it never blocks the ones behind it (NFR-45). The CLI runner keeps undelivered results in a file and exits with 2 (FR-23).
- **No server in CI.** A suite can still run from a file, without a server (FR-23).
- **Run history.** Bounded by the retention setting (NFR-28); backups are described in NFR-44.

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-45 | When the server cannot be reached, the client shall keep finished step results in a local outbox on disk, each with the server URL it belongs to, send them when that server is reachable again, also after a client restart, and show whether the server is reachable; a result the server refuses as invalid shall be set aside and shown to the user, not retried. | Must | UC-09; ADR healing proposal transport; #32, #44 | T + D — #44 |

#### 3.8.3 Security and closed-network operation

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-29 | At run time no AYNA component (client, agent, CLI runner, server, Neo4j, AI service) shall connect to a host outside the closed network: no CDN, telemetry, auto-update, licence check or cloud model, and the client shall load all of its fonts, scripts and styles from the installed files. | Must | CON-01; brief; architecture | D — firewall log in the air-gapped test (#85), SC-36; I — client bundle |
| NFR-30 | The AI service shall start and generate steps with the network disabled, with the model weights and the embedding model bundled in its image and nothing downloaded at start. | Must | CON-01; #71, #82 | T — #82; D — SC-36 |
| NFR-31 | The agent shall listen on 127.0.0.1 only and refuse every connection that does not carry the per-session token (at least 16 characters, created by the client and passed in an environment variable, never in a command line or URL) in an `Authorization: Bearer` header. | Must | CON-07; #16 | T — agent RPC tests (#16) |
| NFR-32 | The server shall store passwords only as bcrypt hashes (#60) and refuse every REST and WebSocket request unless it carries a valid session or a valid API token, except three public endpoints: login, the health check `GET /api/health` (the Compose healthcheck and the client's first-run server check, SC-02) and the OpenAPI document with Swagger UI (team-confirmed, #140; advisor Q8 pending). | Must | UC-15; #60; ADR accounts and tokens | T |
| NFR-46 | The AI service's port shall not be published on the backend host; only the server shall reach the AI service, over the Compose network. | Must | CON-01; #82 | I — review of `docker-compose.yml` (#82) |

#### 3.8.4 Maintainability

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-33 | Keeping tests passing after a UI change shall need changes to repository objects only, not to test steps. | Must | brief (Core 2); plan | D — SC-12, SC-30 |
| NFR-34 | The step, element and snapshot schemas, the REST API and the agent JSON-RPC contract shall carry a version, be frozen at G1 with contract tests in CI, and change only through an ADR. | Must | architecture "Contracts"; G1; #52 | I + T — contract tests (#52) |
| NFR-35 | Every module's tests and linters shall run in CI on every pull request, and a pull request shall merge only when CI is green. | Must | working agreement (#8); #3 | I — CI configuration |

#### 3.8.5 Portability

The backend runs wherever Docker runs (NFR-36). The client and the agent are Windows-only in semester 1.

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-19 | The client and the agent shall run on 64-bit Windows TBD-3 (proposed: Windows 10 22H2 and Windows 11, to confirm), and the agent shall automate applications through UI Automation with the win32 fallback. | Must | CON-02; ADR Windows first | D — weekly Windows session, clean VM of #85 |
| NFR-21 | The agent shall reach the application under test only through a driver interface, so that a web or mobile driver can be added without changing the step schema, the server or the client. | Must | CON-02; ADR Windows first; OOS-01 | I — SDD review (#45) |

#### 3.8.6 Installation and operation

These requirements also cover site adaptation, which is done through settings.

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| NFR-36 | One Windows installer shall install the client and the agent on a clean Windows machine with no development tools and no internet access, uninstalling shall leave no AYNA process running, and the backend shall start with one `docker compose up` from an offline bundle. | Must | UC-16; CON-01; #84, #85 | D — SC-35 on a clean VM |
| NFR-43 | Every site-specific setting of the backend (ports, Neo4j credentials, screenshot directory, run retention, AI-service address) shall be set through environment variables documented in `.env.example`, without rebuilding any component. | Must | conventions (configuration) | I — review of `.env.example` and `docker-compose.yml` |
| NFR-44 | The install guide shall describe how to back up and restore the Neo4j database and the screenshot store together, so that a restored backend shows the same runs with their screenshots. | Could | UC-16; #91 | D — one restore on a test backend |

### 3.9 Supporting information

The research questions are measured in `eval/` with analysis (A, §4.1). Their semester-1 targets are requirements only where the brief gives a number (§1.2). Paired comparisons use McNemar's test (α = 0.05) [36]; proportions get Wilson intervals [37].

| RQ | Question | Hypothesis | Requirements | Measured in | Semester-1 target |
|---|---|---|---|---|---|
| RQ1 | What share of standard controls in the pilot apps does multi-property UIA identification recognise? | — | NFR-27; FR-01, FR-03 | #29 (harness), #64; D3 (#65) | ≥ 90 % |
| RQ2 | With smart waits, what share of scenarios replays consistently without manual fixes? | — | NFR-25, NFR-26; FR-16 | #55, #62, #69 | ≥ 10 scenarios; flaky < 10 % |
| RQ3 | How accurately does a local model turn Turkish descriptions into runnable steps, given repository context? | H2: with context beats without | NFR-37, NFR-12; FR-25, FR-26 | #36, #57, #77; D4 (#80) | ≥ 60 % step-level accuracy; latency reported |
| RQ4 | Under controlled UI changes, does weighted similarity find more correct elements than single-property lookup? | H1 | FR-29, NFR-10 | #76, #79 | H1 tested; no number |
| RQ5 | On bug-injected versions, does approval-gated healing give fewer false passes than auto-applied healing? | H3 (full test in semester 2) | FR-30, FR-32; SC-31 | #86; semester 2 #103 | First measurement; no number |

## 4 Verification

### 4.1 Verification methods
The four methods of 29148 [40], as AYNA uses them:

| Code | Method | In AYNA |
|---|---|---|
| T | Test | Automated test in CI or in a `@pytest.mark.windows` run: pytest, JUnit, `node --test`, contract tests |
| D | Demonstration | Manual check at a gate or the weekly Windows session, recorded as an issue comment |
| I | Inspection | Review of a document, configuration, schema or code in a pull request |
| A | Analysis | Measurement and statistics in `eval/` (Wilson intervals, McNemar) — used for the RQ-based targets |

### 4.2 Verification environments

| Environment | What runs there | Verifies |
|---|---|---|
| CI, Linux runners (GitHub Actions `ubuntu-latest`) | Server build and tests with Neo4j in Testcontainers; client lint and build; AI-service and schema tests | T for the server, client, AI service and schemas |
| CI, Windows runner (`windows-latest`) | Agent lint and tests; the sample suite through the CLI runner `ayna run` (#61, #67) | T for the agent's non-UI logic; FR-23, FR-24 |
| Weekly Windows session (Hasan's machine; label `needs-windows-test`) | `@pytest.mark.windows` tests; Spy, editor, run and healing screens on Windows | T needing real UI Automation; D for client screens |
| Sample app (#33) with its controlled-change (#46) and bug-injected (#47) versions | Scenarios on SA, SA-C, SA-B; RQ2, RQ4, RQ5 | Most FRs; NFR-25, NFR-26 |
| Pilot apps P1 HandBrake and P2 KeePass 2 (#21, D1) | SC-06, SC-07, SC-23; RQ1 (#64) | NFR-27, FR-01, FR-03 |
| Clean offline Windows VM and an internal Docker host; network cut off; firewall logging outbound attempts (#84, #85) | SC-35, SC-36 | NFR-29, NFR-30, NFR-36 |
| Team laptop with 16 GB RAM and no GPU (D2); department GPU if granted (#131) | RQ3 runs and latency | NFR-12, NFR-13, NFR-37 |

GitHub Actions is development infrastructure outside the closed network; it is not part of the product at run time (NFR-29 is verified on the offline VM).

### 4.3 Verification of each requirement

The Verification column of every FR and NFR row (§3.2–§3.8) gives its method and the issue or scenario that will produce the evidence. It is not repeated here. The §5.1 matrix shows it per use case.

How evidence is recorded for each method:
- **T:** the test's path or pytest node id in the pull request that closes the issue.
- **D:** an issue comment from the weekly session or the gate.
- **I:** the approving review of the pull request.
- **A:** the report in `eval/` with its numbers and intervals.

Every Must requirement names an issue that builds or measures it. At G2 (#70) and G3 (#88), §5.1 gets an evidence column with the status of every requirement.

Methods used on 2026-10-29 (a requirement may use several): FR — 34 T, 12 D, 1 I, 2 A; NFR — 25 T, 11 D, 13 I, 7 A.

### 4.4 Acceptance

The gates are the acceptance points of the semester-1 system:

| Gate | Week | Opens when | Requirements shown |
|---|---|---|---|
| G0 walking skeleton (#28) | 3 | On one sample-app screen the Spy picks an element, it is saved in Neo4j and the agent replays Click and Type by its logical name; a 7–8B model returns valid JSON for a Turkish prompt | FR-01, FR-02, FR-06, FR-10, FR-18 (first slice) |
| G1 design baseline (#56) | 7 | RS and SDD submitted; graph schema, step schema and API contracts frozen with contract tests in CI | NFR-34, NFR-41, NFR-42 |
| G2 MVP core (#70) | 9 | ≥ 10 reference scenarios run end to end from editor-built steps; RQ1 measured; HTML report for each run | NFR-26, NFR-27, FR-12, FR-21 |
| G3 feature freeze (#88) | 12 | First H1 and H2 results; installer runs on a clean offline VM | FR-29 (RQ4), NFR-37, NFR-12, NFR-29, NFR-30, NFR-36 |
| G4 end of semester (#96) | 14 | Demo done; report and evaluation set submitted | All Must requirements |

**Acceptance of the semester-1 system:**
- Every Must requirement has its evidence (§4.3).
- Every Should requirement is either verified or cut in the plan's order (§1.3.6), and the cut is recorded in its issue.
- Every success criterion in §1.2 is reported with its measured value and interval, also when it is not met.

**Acceptance of this RS:**
1. Galip and Ömerfaruk review the draft (#35, done on PR #143).
2. All three team members approve the final version in a pull request (#41).
3. The advisor reviews it at the Tuesday meeting.
4. Version 1.0 is submitted as a PDF by 23 Nov 2026 and stored in `docs/rs/` (#41).

After G1, a requirement change that touches a frozen contract also needs an ADR (NFR-34).

## 5 Traceability

### 5.1 Traceability matrix

Use case → scenarios → requirements → verification:
- **Scenarios:** from the UC column of §3.1.
- **FRs and NFRs:** those whose Source column names the use case.
- **Verification:** the issues that will hold the evidence.

| UC | Scenarios | FRs | NFRs | Verification and evidence |
|---|---|---|---|---|
| UC-01 | SC-01, SC-02 | FR-37, FR-38 | — | T: client settings (#32), applications API integration tests (#128) · D: first-run screen (#32) |
| UC-02 | SC-04, SC-05, SC-06, SC-07, SC-08 | FR-01, FR-02, FR-03, FR-05 | NFR-01, NFR-14 | T: Windows tests (#22, #23), agent supervision (#17) · D: Spy at the weekly Windows session (#24) |
| UC-03 | SC-10, SC-11 | FR-06, FR-07 | NFR-14 | T and D: #25 |
| UC-04 | SC-12, SC-13 | FR-08, FR-09 | NFR-14 | T and D: #30 |
| UC-05 | SC-09, SC-32 | FR-04 | NFR-02, NFR-39 | T: snapshot export (#12), snapshot import (#15) |
| UC-06 | SC-14, SC-15, SC-20 | FR-11, FR-12, FR-13, FR-14 | NFR-14 | T: schema tests (#13), tests API (#39) · I: schema review (#13) · D: editor (#38) |
| UC-07 | SC-14, SC-16, SC-21 | FR-15 | NFR-14 | T: playback tests (#40) |
| UC-08 | SC-26, SC-27, SC-28, SC-36 | FR-25, FR-26, FR-27, FR-28 | NFR-11, NFR-12, NFR-37 | T: retrieval (#58), generation and validator with a stub model (#71) · A: RQ3 (#77) · D: NL panel (#78), SC-28 |
| UC-09 | SC-08, SC-17, SC-18, SC-19, SC-20, SC-21, SC-22, SC-23, SC-28, SC-29, SC-36 | FR-05, FR-10, FR-16, FR-17, FR-18, FR-19, FR-20 | NFR-04, NFR-05, NFR-06, NFR-14, NFR-45 | T: playback (#26, #40), screenshots (#54), live status and outbox (#44, #51) · D: SC-17 at the weekly session |
| UC-10 | SC-24, SC-36 | FR-19, FR-21, FR-22 | NFR-09, NFR-14, NFR-40 | T: report (#59), screenshot storage (#51) · D: run history (#68) |
| UC-11 | SC-19, SC-21, SC-22, SC-25 | FR-35, FR-36 | — | T: triage and decision log (#63) |
| UC-12 | SC-29, SC-30, SC-31, SC-36 | FR-29, FR-30, FR-31, FR-32 | NFR-10, NFR-14 | T: candidates (#42), scorer (#49), playback side (#73), proposals API (#74) · D: approval screen (#75) · A: RQ4 (#76), RQ5 (#86) |
| UC-13 | SC-32 | FR-33, FR-34 | NFR-39 | T: query against the ground truth of #46 (#81) · D: view (#81) |
| UC-14 | SC-33, SC-34 | FR-14, FR-23, FR-24 | — | T: CLI runner (#61), JUnit XML (#66), CI job (#67) |
| UC-15 | SC-03 | FR-39, FR-40 | NFR-32 | T: accounts (#60), healing decisions (#74) |
| UC-16 | SC-35, SC-36 | — | NFR-36, NFR-44 | D: installer on a clean VM (#84), air-gapped test (#85) · T: offline AI service (#82) |

### 5.2 Requirements that trace to no use case

These NFRs come from a constraint, a research question or a project decision rather than from one use case:

| Source | NFRs |
|---|---|
| CON-01 closed network | NFR-29, NFR-30, NFR-46 |
| CON-02 Windows desktop first | NFR-19, NFR-21 |
| CON-03 Turkish | NFR-16, NFR-17 |
| CON-04 no licence cost | NFR-08, NFR-23 |
| CON-05 models only at authoring time | NFR-22 |
| CON-07 fixed architecture | NFR-24, NFR-31 |
| Q5, response times and capacity | NFR-07, NFR-08 |
| RQ1, RQ2 (success criteria) | NFR-25, NFR-26, NFR-27 |
| D2, team hardware | NFR-13 |
| Brief, plan and architecture | NFR-18, NFR-33, NFR-34, NFR-42 |
| ADR graph schema v0 | NFR-38, NFR-41 |
| Conventions and working agreement | NFR-35, NFR-43 |
| A single issue | NFR-03 (#54), NFR-15 (#25, #32, #39, #40), NFR-20 (#22), NFR-28 (#51) |

### 5.3 Coverage checks

Checked on 2026-10-27 with a one-off script (not committed) over this file and Appendix C, again on 2026-10-29 after the review changes of version 0.6, and on 2026-11-19 for version 1.0. **0 errors.** It checked that:
- every `FR`, `NFR`, `UC`, `SC` and `TBD` ID referenced in either file is defined exactly once: FR and NFR rows in §3.2–§3.8, UC headings in Appendix B, SC headings in Appendix C, TBD rows in Appendix E;
- the §3.1 summaries match those definitions in ID, title, use cases and priority, and the use-case titles match the workshop notes;
- the FR and NFR rows moved from `docs/rs/scenarios.md` (#34) are unchanged, except the Verification cell of NFR-07 and NFR-08 (on 2026-10-27; the 0.6 changes are listed in the document history);
- each use case's lists in Appendix B and §5.1 match the FR and NFR Source columns and the scenarios' UC tags, and every NFR without a use case is in §5.2.

| Check | Target | Result |
|---|---|---|
| Reference scenarios | ≥ 30 | 36 (SC-01–SC-36): 21 main, 11 negative, 4 edge; each has Given, When and Then |
| Functional requirements | ≥ 25 | 40 (FR-01–FR-40): 35 Must, 5 Should |
| Non-functional requirements | — | 46 (NFR-01–NFR-46): 44 Must, 1 Could, 1 Won't (S1) |
| Every FR → at least one SC | all | 40 of 40; every SC an FR lists exists |
| Every SC → evidence for at least one requirement | all | 36 of 36; SC-35 only for NFR-36 |
| Every UC → at least one SC | all | 16 of 16 |
| Every UC → at least one FR | all | 15 of 16; UC-16 (installation, closed network) is a quality requirement, covered by NFR-29, NFR-30, NFR-36 and NFR-44 |
| Every Must requirement → a planned issue or test | all | All; the load test of NFR-07 and NFR-08 is #152 |

## Appendices

### Appendix A — Glossary and acronyms

| Term | Meaning |
|---|---|
| A, D, I, T | Verification methods: analysis, demonstration, inspection, test (§4.1) |
| ADR | Architecture decision record, in `memory-bank/decisions/` |
| AUT | Application under test |
| Bolt | Neo4j's binary network protocol |
| C1–C4 | The project's contributions (§1.2) |
| Change impact | The tests affected by the elements that changed between two application versions |
| Checkpoint | A Verify step comparing an element property with an expected value |
| CI | Continuous integration |
| CLI runner | The `ayna run` command that plays a suite with a headless agent |
| Closed network | A network with no connection to the internet or any outside service |
| D1–D7 | The plan's decision points |
| Descriptor | The multi-property description of an element (AutomationId, Name, ControlType, ClassName, parent path, nearest label, bounds…) |
| Element | One node of a UI Automation snapshot of a specific application version |
| FR, NFR | Functional, non-functional requirement |
| G0–G4 | Gates: milestone checks that must pass before the next phase starts |
| H1–H3 | The project's hypotheses (§3.9) |
| Healing proposal | Ranked replacement candidates for a repository object that no longer resolves, with per-property score contributions; applied only after approval |
| Held-out split | The 30 NL/step pairs frozen before any prompt tuning, used only for RQ3 |
| JSON-RPC | Remote procedure calls encoded in JSON, version 2.0 [42] |
| JSONL | JSON Lines: one JSON object per line |
| JUnit XML | The XML test-result format read by CI systems |
| LLM | Large language model |
| Logical name | A repository object's stable name, `screen.element` in lowerCamelCase, e.g. `login.userNameInput` |
| MoSCoW | Must, Should, Could, Won't: the priority scale (§1.5) |
| NL | Natural language |
| Object Spy | Client screen that inspects elements on screen and adds them to the repository |
| p95 | 95th percentile |
| RAG | Retrieval-augmented generation [31] |
| RepoObject, repository object | Entry in the object repository: a logical name with primary and fallback properties, resolved to an element per application version |
| RQ1–RQ5 | The research questions (§3.9) |
| RS, SDD | Requirements Specification, Software Design Document |
| Rule, rule book | A deterministic rule created from an approved decision, so that the same situation never needs a model again |
| SC, UC | Reference scenario, use case |
| Smart wait | Waiting until the element exists, is visible and is enabled, instead of a fixed sleep |
| Snapshot | A captured window subtree of one application version, stored as Window and Element nodes |
| Step, keyword | One action in a test: Click, Type, Select, Verify or Wait |
| SUIT | HAVELSAN's programme to which AYNA applied |
| SUS | System Usability Scale [39] |
| TBD | To be decided (Appendix E) |
| Triage | Classifying a failed step: element not found, unexpected window, assertion failed, timeout, search incomplete |
| UIA | Microsoft UI Automation, the accessibility tree AYNA reads through pywinauto's `uia` backend [30] |

### Appendix B — Use-case catalogue

Condensed from the requirements workshop notes ([`docs/requirements-workshop.md`](../requirements-workshop.md), #19), a draft awaiting the advisor (Q2). Each use case lists its actor, priority (§3.1), sources, main flow, alternative and error flows with the scenarios that exercise them, and the requirements it leads to.

#### UC-01 · Connect to the server and register an application version
**Actor** ROLE-2 · **Priority** Must · **Traces to** graph model; #32, #128
- **Goal:** work against a named application and build.
- **Precondition:** an AYNA server runs on the closed network.
- **Main flow:**
  1. On first run the engineer enters the server URL.
  2. The engineer chooses or creates the application and adds a version for the build under test.
  3. The client remembers the server and the choice on this machine.
- **Alternatives:**
  - 1a. No AYNA server answers: the client names the URL and stays on the first-run screen (SC-02).
  - 2a. A duplicate version is refused (SC-01).
- **Requirements:** FR-37, FR-38 · **Scenarios:** SC-01, SC-02

#### UC-02 · Inspect an element with the Object Spy
**Actor** ROLE-1 · **Priority** Must · **Traces to** Core 1; RQ1; ADR client/server; #11, #22, #24
- **Goal:** see how AYNA recognises a control.
- **Precondition:** the AUT runs on the test machine; the client and its agent are connected.
- **Main flow:**
  1. The author opens the Spy and chooses a window; the element tree and the property panel appear.
  2. The author points at a control and presses the pick hotkey.
  3. The control is outlined on screen and selected in the tree, and the panel shows its descriptor.
  4. Selecting another node in the tree outlines that element.
- **Alternatives:**
  - 3a. UI Automation gives neither an AutomationId nor a Name: the win32 properties are added, marked as such (SC-07).
  - 3b. At 150 % display scaling the result is the same (SC-05).
  - 1a. The agent has crashed: the client restarts it up to 3 times, then shows "failed" (SC-08).
- **Requirements:** FR-01, FR-02, FR-03, FR-05 · **Scenarios:** SC-04–SC-08

#### UC-03 · Add an element to the object repository
**Actor** ROLE-1 · **Priority** Must · **Traces to** Core 2; ADR Neo4j; #25
- **Goal:** give a control a stable name that tests can use.
- **Precondition:** an element is picked in the Spy (UC-02) and an application version is selected.
- **Main flow:**
  1. The author chooses "Add to repository".
  2. The author enters a logical name `screen.element`.
  3. The author edits the primary and fallback properties and saves.
  4. The object is linked to the element for this version and appears in the repository view and the editor's object picker.
- **Alternatives:**
  - 2a. A name that is not of the form `screen.element` is refused, and the message shows the form (SC-11).
  - 3a. A name that already exists in the application is refused, and the message names the existing object (SC-11).
- **Requirements:** FR-06, FR-07 · **Scenarios:** SC-10, SC-11

#### UC-04 · Maintain the object repository
**Actor** ROLE-2 · **Priority** Must · **Traces to** Core 2; #30
- **Goal:** keep logical names and properties correct as the UI changes.
- **Main flow:**
  1. The engineer opens the repository view and searches.
  2. The engineer renames an object or edits its properties.
  3. The view shows how many tests use each object; tests show the new name without being edited (SC-12).
- **Alternatives:**
  - 2a. Deleting an object that tests use is refused, and the message names the tests; an unused object is deleted (SC-13).
- **Requirements:** FR-08, FR-09 · **Scenarios:** SC-12, SC-13

#### UC-05 · Capture a snapshot of an application version
**Actor** ROLE-2 · **Priority** Must · **Traces to** Core 1; C2, C3; #12, #15
- **Goal:** store a build's whole window tree for healing and impact analysis.
- **Precondition:** the AUT runs at the version under test, and that version is registered (UC-01).
- **Main flow:**
  1. The engineer chooses a window.
  2. The agent exports its whole subtree as one snapshot.
  3. The server imports it under the version.
- **Alternatives:**
  - 3a. Importing the same snapshot again leaves the graph unchanged (SC-09).
- **Requirements:** FR-04 · **Scenarios:** SC-09, SC-32

#### UC-06 · Build a test in the codeless editor
**Actor** ROLE-1 · **Priority** Must · **Traces to** Core 3, 5; #13, #38, #39
- **Goal:** create a test without writing code.
- **Precondition:** the repository has objects for the screens the test uses.
- **Main flow:**
  1. The author creates a test.
  2. The author adds steps, choosing a keyword (Click, Type, Select, Verify, Wait) and picking each target from the repository.
  3. The author enters values and, if needed, a timeout.
  4. The author drags steps to reorder them and saves.
  5. The test can be exported to a JSON file and imported again.
- **Alternatives:**
  - 4a. An invalid step is highlighted with its reason and the test is not saved; the server rejects the same step sent to its API with HTTP 400 (SC-15).
- **Requirements:** FR-11, FR-12, FR-13, FR-14 · **Scenarios:** SC-14, SC-15, SC-20

#### UC-07 · Add a property checkpoint
**Actor** ROLE-1 · **Priority** Must · **Traces to** Core 4; #13, #40
- **Goal:** check that the screen shows the expected result.
- **Main flow:**
  1. The author adds a Verify step and picks its target.
  2. The author chooses a property (name, value, enabled, visible, checked, selected), an operator (equals, notEquals, contains) and the expected value.
  3. During a run the step passes or fails on that comparison.
- **Alternatives:**
  - 3a. The comparison fails: the result shows the expected and the actual value, and the category is "assertion failed" (SC-16, SC-21).
- **Requirements:** FR-15 · **Scenarios:** SC-14, SC-16, SC-21

#### UC-08 · Write steps from a Turkish description
**Actor** ROLE-1 · **Priority** Should (cut 2; FR-25, FR-26 stay Must) · **Traces to** C1; RQ3, H2; ADR LLM authoring-only; #37, #58, #71, #78
- **Goal:** get draft steps from plain Turkish.
- **Precondition:** the AI service runs, and the repository has objects for the current screen.
- **Main flow:**
  1. The author types a description in the NL panel.
  2. The server retrieves the current screen's subgraph and the closest repository objects.
  3. The local model returns steps in the step schema.
  4. The validator drops steps with an unknown target or keyword.
  5. The panel shows the remaining steps with their reasons.
  6. The author edits and accepts them, all or one by one, and they join the test as ordinary steps.
- **Alternatives:**
  - 4a. No valid step remains: the panel says so, with the reasons (SC-27).
  - 1a. The AI service is down: the panel is disabled with a message, and everything else works (SC-28).
- **Requirements:** FR-25, FR-26, FR-27, FR-28 · **Scenarios:** SC-26, SC-27, SC-28, SC-36

#### UC-09 · Run a test and watch it live
**Actor** ROLE-1, ROLE-2 · **Priority** Must · **Traces to** Core 4; RQ2; #26, #40, #44, #51, #54
- **Goal:** replay a test on the current build.
- **Precondition:** the test is saved, the AUT is in its start state and the agent is connected.
- **Main flow:**
  1. The user presses Run, and the client sends the steps to the local agent.
  2. Before each step the agent waits until the element exists, is visible and is enabled, up to the timeout.
  3. The agent performs the step and takes a screenshot.
  4. The step's status appears live in this client and in every other client that has the test open.
  5. The run and its step results are stored on the server.
- **Alternatives:**
  - 2a. The element never becomes ready: the step fails as "timeout" and the remaining steps are not run (SC-19).
  - 2b. No element matches: the step ends as "repair proposed" (UC-12, SC-29).
  - 2c. The search runs out of its time budget before it covers the window: the step fails as "search incomplete", and no healing starts (FR-35).
  - 3a. A checkpoint fails (SC-21).
  - 3b. An unexpected window appears (SC-22).
  - 5a. The server cannot be reached: the results wait in the client's outbox and are stored when the server is back (NFR-45).
- **Requirements:** FR-05, FR-10, FR-16, FR-17, FR-18, FR-19, FR-20 · **Scenarios:** SC-08, SC-17–SC-23, SC-28, SC-29, SC-36

#### UC-10 · Read the run report and run history
**Actor** ROLE-2 · **Priority** Must · **Traces to** Core 5; #59, #68
- **Goal:** see what passed and what failed.
- **Main flow:**
  1. The engineer opens the run list and filters it by test and status.
  2. The engineer opens a run; the HTML report shows a summary, a step table with status, duration and error, and a screenshot per step.
  3. The report downloads as one file that opens offline.
- **Requirements:** FR-19, FR-21, FR-22 · **Scenarios:** SC-24, SC-36

#### UC-11 · See the failure category of a failed step
**Actor** ROLE-2 · **Priority** Should (cut 3; FR-36 stays Must) · **Traces to** ADR decision layer in semester 2; #63
- **Goal:** know what kind of failure happened.
- **Main flow:**
  1. Rules put each failed step in one category: element not found, unexpected window, assertion failed, timeout or search incomplete.
  2. The category is shown with the step.
  3. The decision is logged, and the log exports as JSONL for semester 2.
- **Decided (TBD-5, closed):** "element not found" when nothing matches the primary or fallback properties by the end of the wait (healing starts); "timeout" when an element matches but does not become visible and enabled in time; "search incomplete" when the search ran out of its budget (neither starts healing).
- **Requirements:** FR-35, FR-36 · **Scenarios:** SC-19, SC-21, SC-22, SC-25

#### UC-12 · Approve or reject a healing proposal
**Actor** ROLE-3 · **Priority** Must · **Traces to** C2; RQ4/H1, RQ5/H3; ADR approval-gated healing; #49, #73, #74, #75
- **Goal:** repair a broken locator without hiding a real bug.
- **Precondition:** a step ended as "repair proposed" (UC-09, 2b), and the run stopped there (TBD-6).
- **Main flow:**
  1. The reviewer opens the proposal from the run report.
  2. The proposal shows the failing step and the top 3 candidates, each with per-property contribution bars.
  3. The selected candidate is outlined on screen.
  4. The reviewer approves one: the repository object resolves to it for that version, and a Rule is stored with the reviewer and the time.
  5. The next run passes without any step being edited.
- **Alternatives:**
  - 4a. The reviewer rejects all: the step stays failed as "element not found", the repository is unchanged and the decision is logged (SC-31).
- **Requirements:** FR-29, FR-30, FR-31, FR-32 · **Scenarios:** SC-29, SC-30, SC-31, SC-36

#### UC-13 · See which tests a new version affects
**Actor** ROLE-2 · **Priority** Should (cut 1; FR-33 stays Must) · **Traces to** C3; #42, #81
- **Goal:** know before a run which tests a UI change touches.
- **Precondition:** snapshots of both versions exist (UC-05).
- **Main flow:**
  1. The engineer chooses the old and the new version.
  2. The server lists the changed repository objects, the tests that use them and the pending healing proposals.
  3. Each test links to the editor.
- **Alternatives:**
  - 1a. The same version on both sides lists no change (SC-32).
- **Requirements:** FR-33, FR-34 · **Scenarios:** SC-32

#### UC-14 · Run a suite headless in CI
**Actor** ROLE-5 (set up by ROLE-2) · **Priority** Should (cut 4) · **Traces to** Core 5; #61, #66, #67
- **Goal:** run the regression suite on every build.
- **Precondition:** the CI job runs on a Windows runner and has started the AUT.
- **Main flow:**
  1. The pipeline runs `ayna run --server URL --suite NAME --junit out.xml`, with the CI service account's API token in `AYNA_SERVER_TOKEN`.
  2. The headless agent plays the steps.
  3. JUnit XML is written, and the results are posted to the server.
  4. The command exits with 0: every test passed and every result reached the server.
- **Alternatives:**
  - 1a. `--from-file suite.json` runs without a server (SC-34).
  - 4a. A test fails or proposes a repair: the exit code is 1 and the CI job fails (SC-34).
  - 4b. Results could not be delivered, or the token was refused: the runner keeps the undelivered results in a file next to the JUnit XML and exits with 2, even if every test passed.
- **Requirements:** FR-14, FR-23, FR-24 · **Scenarios:** SC-33, SC-34

#### UC-15 · Manage user accounts
**Actor** ROLE-4 · **Priority** Must · **Traces to** #60
- **Goal:** control who can edit, run and approve.
- **Main flow:**
  1. The admin creates accounts with the role admin or tester.
  2. Users log in.
  3. The server stores the user id with every edit, run and approval.
- **Alternatives:**
  - 1a. A tester who opens user management is refused, in the client and by the API (SC-03).
- **Open:** a separate approver permission (Q1); whether local accounts are enough (Q8).
- **Requirements:** FR-39, FR-40 · **Scenarios:** SC-03

#### UC-16 · Install and run AYNA on a closed network
**Actor** ROLE-4 · **Priority** Must · **Traces to** CON-01; ADR client/server; #82, #84, #85
- **Goal:** run AYNA with no internet access.
- **Main flow:**
  1. The administrator loads the offline backend bundle on an internal host and starts the server, Neo4j and the AI service (model weights bundled) with one `docker compose up`.
  2. The administrator installs the client and its agent with one installer on each test machine.
  3. The administrator points the clients at the server.
  4. The whole chain works with the network off and makes no outbound connections.
- **Alternatives:**
  - 4a. After uninstalling, no AYNA process is left running (SC-35).
- **Requirements:** no FR; NFR-29, NFR-30, NFR-36, NFR-44 · **Scenarios:** SC-35, SC-36

### Appendix C — Reference scenarios

The 36 reference scenarios, in Given / When / Then form, are in [`docs/rs/scenarios.md`](scenarios.md) (#34): how to read them (C.1), the applications under test and the sample-app behaviour they assume (C.2), and the scenarios grouped by area (C.3). That file is included in full as Appendix C of the submitted PDF (#41), so the RS stands alone; its summary table is §3.1.

### Appendix D — Mapping to ISO/IEC/IEEE 29148:2018 §9.6

| 29148 SRS item | Here |
|---|---|
| Purpose · Scope | 1.1 · 1.2 |
| Product perspective | 1.3.1 (summary), 3.5 (interface requirements) |
| System, user, hardware, software, communications interfaces | 3.5 |
| Memory constraints | 3.3 (memory of the local model, NFR-13); no other limit applies |
| Operations · Site adaptation | 3.8.6 (offline install, settings through environment variables, backup) |
| Product functions · User characteristics · Limitations | 1.3.2 · 1.3.3 · 1.3.4 |
| Assumptions and dependencies · Apportioning of requirements | 1.3.5 · 1.3.6 |
| Functions | 3.2 (with use cases and scenarios in 3.1) |
| Usability · Performance · Logical database | 3.4 · 3.3 · 3.6 |
| Design constraints · Standards compliance | 3.7 |
| Software system attributes | 3.8 |
| Verification | 4 |
| Supporting information | 3.9, 5, Appendices |

Added for the course: 3.1 use cases and scenarios, 5 traceability matrix.

### Appendix E — Open questions (TBD)

Every `TBD-n` in the document, with its owner and the issue that closes it. In this final version (#41), each item is closed or explicitly deferred with a reason. TBD-1 to TBD-6 come from #34; TBD-7 onwards from #35.

#### E.1 Items, closed or deferred

| ID | Item | Where it is used | Owner | Closes in |
|---|---|---|---|---|
| TBD-1 | **Closed 2026-10-31** (D1, #21; ADR pilot apps and sample-app technology): P1 is HandBrake (WPF), P2 is KeePass 2 (WinForms); KeePassXC (Qt Widgets) may join as a third pilot once the first two run end to end. Notepad++ stays the win32 fallback fixture (#23) | C.2; SC-06, SC-07, SC-23; NFR-27; §4.2 | hasan | #21 |
| TBD-2 | **Closed 2026-11-03** (team decision, #185): Turkish and English, chosen by the user (ADR client-ui-language) | NFR-17; §1.3.3 | galip (advisor, Q4) | #185 |
| TBD-3 | **Deferred** to the Windows installer and the air-gapped test (#84, #85, Week 12), which fix the image of the clean VM: supported Windows versions of the test machines. So far the system runs on Hasan's Windows 11 machine and the CI runner's Windows Server image. Note for the decision: Windows 10 22H2 has been out of mainstream support since 14 Oct 2025, and closed-network sites often run LTSC editions (D5) | NFR-19; §1.3.5, §3.5.3 | hasan, omer | #85 |
| TBD-4 | **Deferred** to the advisor's answer to Q5 (E.2), because the meeting (#19) has not been held. Numbers marked "(proposed, to confirm)": NFR-04 (500 ms per step; playback exists since #40, so the playback tests can time it), NFR-13 (16 GB RAM, no GPU), NFR-18 (SUS ≥ 68), NFR-19 (Windows versions, with TBD-3). Team-confirmed, advisor Q5 pending: NFR-02 (sample-app windows only), NFR-05 (hasan, #143); NFR-06–NFR-09 (omer, #140; NFR-07 and NFR-08 also met by the load test #152). NFR-32 is team-confirmed (#140); its open point is Q8 | §3.3–§3.8 | hasan: NFR-04 · galip: NFR-13, NFR-18 | Q5 at the advisor meeting (#19) |
| TBD-5 | **Closed 2026-10-29** (hasan, #143 review). Boundary between "element not found" and "timeout": "element not found" when no element matches the primary or fallback properties by the end of the wait (healing starts); "timeout" when an element matches but does not become visible and enabled in time (no healing). Added: a fifth category, "search incomplete", when the search or the snapshot runs out of its budget before covering the window; it never starts healing, because candidates from an incomplete tree would give a confident but unfounded proposal | FR-29, FR-35; SC-19, SC-25, SC-29; UC-09, UC-11 | hasan | Built in #40, #63; the budget in #12 |
| TBD-6 | **Closed 2026-10-29** (hasan, #143 and #151 reviews). After a "repair proposed" step the agent performs no further step of that test, its remaining steps are marked "not run", the run is failed, and in a suite the next test runs. One run gives at most one proposal | FR-30; SC-29, SC-31; UC-12 | hasan | Built in #73 |
| TBD-7 | **Deferred** to a team decision before the evaluation set is published (#90, Week 13): the project's own licence, for the code and for the open evaluation set (C4). The repository has been public since 2026-11-17 with no licence file, which by default reserves all rights; nothing in semester 1 needs more than that, but publishing the evaluation set does | §1.3.5 | team (galip raises it) | #90 |
| TBD-8 | **Deferred** to the next plan revision: the plan's "Team and roles" and WP1 rows still name Hasan as RS lead, while ADR windows-work-to-hasan moved the RS chain (#27, #34, #35, #41) to Galip. This document follows the ADR; only the plan document (Claude Docs) is behind | Document history; §4.4 | galip | Next plan revision |
| TBD-9 | **Closed 2026-10-29** (omer, #143 review): the load test for NFR-07 and NFR-08 is #152. Run on 2026-11-10: both met, numbers kept (`server/loadtest/results/2026-11-10-apple-m3.md`) | NFR-07, NFR-08 | omer | #152 |
| TBD-10 | **Closed 2026-10-29** (omer, #143 review; option 5a of ADR healing proposal transport). The CLI runner authenticates with a revocable API token of a CI service account, passed in `AYNA_SERVER_TOKEN` as a Bearer token; no human password lives on the CI machine | FR-23, FR-39; NFR-32; UC-14; ROLE-5; §3.5.4 | omer, hasan | #60, #61 |
| TBD-11 | **Deferred** to the semester report (#93), the first document that cites all sources together: one reference numbering for RS, SDD and report. Until then the rule is that the RS's §2.1 list ([1]–[43]) is the project numbering, the SDD cites it, and a source that only `docs/literature.md` or #20 uses gets the next free number when a document first cites it | §2.1 | galip, omer | #93 |

#### E.2 Questions waiting for the advisor

The requirements workshop (#19) put eight questions to the advisor; its §7 records the answers. Until they come, the RS rests on the team's proposal.

| Q | Question | What in the RS depends on it | Status |
|---|---|---|---|
| Q1 | Are ROLE-1 to ROLE-5 right, and are the account roles admin and tester enough, or does approving healing need its own permission? | §1.3.3; UC-12, UC-15; FR-39 | Open |
| Q2 | Are UC-01 to UC-16 complete, and is the cut-order priority acceptable? | §3.1, Appendix B; every Source column | Open |
| Q3 | Is the out-of-scope list right, especially the recorder and data-driven tests in semester 2? | §1.2 (OOS-08, OOS-10) | Open |
| Q4 | Client UI in Turkish, English or both? May the RS be in English? | NFR-17 (TBD-2); the whole document | UI language decided by the team (both, TBD-2 closed, #185); the RS language is still open |
| Q5 | Which response times and capacity should the RS commit to? | §3.3 (TBD-4), NFR-07, NFR-08 | Open |
| Q6 | Is there a course RS template, or is the 29148 structure acceptable? | The structure of this document; Appendix D | Open |
| Q7 | Any HAVELSAN mentor input on the target technology; should the RS name the pilot apps? | TBD-1; §1.3.5 (D5) | Open |
| Q8 | Are local user-name and password accounts enough on a closed network? | FR-39, NFR-32 | Open |
