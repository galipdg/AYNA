# AYNA — Requirements Specification (RS)

| | |
|---|---|
| Project | AYNA — Akıllı, Yerli, Nesne Tabanlı Arayüz Testi: codeless UI test automation for Windows desktop applications on a closed network |
| Course | COM 4061 Research Project I, Ankara University |
| Advisor | Prof. Dr. Gazi Erkan Bostancı |
| Team | Galip Enes Doğan · Ömerfaruk Sarıbal · Hasan Berk Yanıkkaya |
| Programme | HAVELSAN SUIT application |
| Document | Software Requirements Specification in the style of ISO/IEC/IEEE 29148:2018 §9.6 [40] |
| Version | 0.1 — outline |
| Date | 2026-10-27 |
| Status | Outline for team approval (#27). Draft: #35 (week 4). Final PDF: #41, due 23 Nov 2026 |

**How to read this outline.** Every section carries one line: _What_ goes there, the issue that **Fills** it, what it is written **From**, and, where a teammate owns the subject, whose **Input** it needs. #35 replaces these lines with prose and tables. Sections 1.5, 4.1 and Appendix D are written in full now because #34 and #35 depend on them.

## Document history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-10-27 | Galip | Outline (#27) |
| 0.5 | planned, week 4 | Galip | Full draft (#35), reviewed by Galip and Ömerfaruk |
| 1.0 | planned, 23 Nov 2026 | Galip | Submitted version (#41) |

Approval: each version is approved in a pull request by the three team members; the advisor reviews the draft at the Tuesday meeting.

## 1 Introduction

### 1.1 Purpose
_What:_ why this RS exists and who reads it (advisor, course jury, HAVELSAN mentor, team). — **Fill:** #35 · **From:** [brief](../../memory-bank/project/brief.md)

### 1.2 Scope
_What:_ product name, what AYNA does and does not do in semester 1, its goals and the semester-1 / end-of-project success criteria table. — **Fill:** #35 · **From:** brief ("What we build", "Success criteria", "Out of scope"), out-of-scope list agreed in `docs/requirements-workshop.md` (#19)

### 1.3 Product overview

#### 1.3.1 Product perspective
_What:_ AYNA in its environment — context diagram (test machine: client, agent, application under test; closed network: server, Neo4j, AI service; CI runner) and how it relates to TestComplete and the open-source tools. — **Fill:** #35 · **From:** [architecture](../../memory-bank/project/architecture.md), ADRs, [tool matrix](../tool-matrix.md) (#18), `docs/literature.md` (#10, #20) · **Input:** omer

#### 1.3.2 Product functions
_What:_ one short paragraph per major function (recognition and Object Spy, repository, steps and editor, playback, reports and CLI, NL assistant C1, self-healing C2, change impact C3, triage), each pointing to its §3.2 subsection. — **Fill:** #35 · **From:** brief, plan "What we will do"

#### 1.3.3 User characteristics
_What:_ the user roles, their technical skill (non-programmer testers), language (Turkish) and what each role may do. — **Fill:** #35 · **From:** roles in `docs/requirements-workshop.md` (#19), accounts and roles (#60)

#### 1.3.4 Limitations
_What:_ constraints that bound every design choice — closed network, Windows desktop only in semester 1, Turkish UI and NL, fixed stack, Neo4j as the single database, LLM only at authoring time, no mid-run repair, team capacity. — **Fill:** #35 · **From:** constraints in `docs/requirements-workshop.md` (#19), [ADR index](../../memory-bank/decisions/README.md)

#### 1.3.5 Assumptions and dependencies
_What:_ what must hold for the requirements to be achievable — the AUT exposes UIA properties, team hardware runs a quantised 7–8B model (D2), Windows versions of test machines, pilot apps (D1, #21), HAVELSAN mentor input (D5), the project's own licence (open, Appendix E). — **Fill:** #35 · **From:** plan "Decision points" and "Risks and mitigations"

#### 1.3.6 Apportioning of requirements
_What:_ which requirements belong to semester 1, semester 2 or later (maps to the Priority attribute, §1.5) and the plan's fixed cut order. — **Fill:** #35 · **From:** plan "If we fall behind" and "Semester 2 outline", issues #99–#108

### 1.4 Definitions, acronyms and abbreviations
_What:_ pointer to Appendix A. — **Fill:** #35

### 1.5 Document conventions

**Identifiers.** Numbers are zero-padded to two digits (`FR-07`; three digits after 99), never reused and never renumbered. A dropped requirement stays in its table marked _Deleted_ with the reason. IDs are flat; the section a requirement sits in gives its area, so moving it between areas does not change its ID.

| Prefix | Meaning | Defined in | Filled by |
|---|---|---|---|
| `UC-xx` | Use case | `docs/requirements-workshop.md`, condensed into Appendix B | #19, #35 |
| `SC-xx` | Reference scenario (given / when / then) | `docs/rs/scenarios.md`, included as Appendix C | #34 |
| `FR-xx` | Functional requirement | §3.2 | #34 |
| `NFR-xx` | Non-functional requirement: performance, usability, interface, data, design constraint, quality attribute | §3.3–§3.8 | #34, #35 |

IDs that already exist in the plan keep their meaning and are cited as they are: C1–C4 (contributions), RQ1–RQ5, H1–H3, G0–G4 (gates), D1–D7 (decision points). Issue numbers (`#nn`) are links, never requirement IDs.

**Statement form** (29148 §5.2 [40]): _"The ‹system | client | agent | server | AI service› shall ‹capability› [‹condition›] [‹measurable criterion›]."_ One requirement per statement. _shall_ = binding, _should_ = desired, _may_ = optional. No unmeasured adjectives ("fast", "user-friendly", "robust"): give a number, or write `TBD-n` and list it in Appendix E.

**Attributes.** Every FR and NFR row has these columns; FR rows add **Scenarios** (the `SC-xx` that exercise it — the FR → SC trace #34 requires).

| Attribute | Values |
|---|---|
| Priority | MoSCoW, tied to the plan: **Must** = semester-1 core the plan never cuts (Spy, repository, editor, smart-wait playback, report, self-healing experiment, offline NL measurement) and closed-network operation · **Should** = semester 1, on the plan's cut list (change-impact view, NL chat panel, rule-based triage, CLI + JUnit XML) · **Could** = semester 1 only if time allows (e.g. visual fallback, D3) · **Won't (S1)** = semester 2 or later (recorder, data-driven tests, decision layer) |
| Source | Where the requirement comes from: `UC-xx`, workshop (#19), brief / plan section, ADR, HAVELSAN letter of intent, literature `[n]`, tool matrix |
| Verification | T, D, I or A (§4.1), plus where the evidence will be |

Optional: **Rationale**, only when the reason is not obvious from the source.

FR table shape (used in every §3.2 subsection; NFR tables drop the Scenarios column):

| ID | Requirement | Priority | Source | Verification | Scenarios |
|---|---|---|---|---|---|
| FR-xx | The agent shall … | Must | UC-xx | T | SC-xx, SC-yy |

## 2 References

### 2.1 External references
_What:_ the sources the RS cites. Numbers follow the plan's reference list ("AYNA – 14-Week Project Plan", [1]–[39]) so the RS, SDD and report cite each source with the same number; the RS lists only what it cites, keeps the plan's numbers, and adds new sources from [40]. Likely citations: [2]–[8], [9], [10], [14], [30], [32], [33], [38]. — **Fill:** #35 · **From:** plan "References"

[40] ISO/IEC/IEEE 29148:2018, _Systems and software engineering — Life cycle processes — Requirements engineering_.

### 2.2 Project documents
_What:_ the repository documents this RS builds on. — **Fill:** #35 refreshes the status column.

| Document | Path | Issue | Status on 2026-10-27 |
|---|---|---|---|
| Project brief | [`memory-bank/project/brief.md`](../../memory-bank/project/brief.md) | — | merged |
| Architecture | [`memory-bank/project/architecture.md`](../../memory-bank/project/architecture.md) | — | merged |
| Decisions (ADRs) | [`memory-bank/decisions/README.md`](../../memory-bank/decisions/README.md) | — | merged |
| Glossary | [`memory-bank/project/glossary.md`](../../memory-bank/project/glossary.md) | — | merged |
| Requirements workshop notes | `docs/requirements-workshop.md` | #19 | in progress |
| Reference scenarios | `docs/rs/scenarios.md` | #34 | planned |
| Tool comparison matrix | [`docs/tool-matrix.md`](../tool-matrix.md) | #18 | merged |
| Literature review | `docs/literature.md` | #10, #20 | PR #126 |
| Graph model | [`docs/graph-model.md`](../graph-model.md) | #14 | merged |
| Step schema | `schemas/step.schema.json` | #13 | PR #134 |
| Element and snapshot schemas | `schemas/element.schema.json`, `schemas/snapshot.schema.json` | #11, #12 | planned |
| Agent JSON-RPC contract | `docs/agent-rpc.md` | #16 | PR #135 |
| REST API (generated) | `docs/api/openapi.yaml` | #31, #52 | planned |
| Software Design Document | `docs/sdd/` | #45, #53 | planned |

## 3 Requirements

### 3.1 Use cases and reference scenarios
_What:_ two summary tables — use cases (`UC-xx`, name, primary actor, priority) and reference scenarios (`SC-xx`, title, application under test, `UC-xx`). Full texts live in Appendix B and Appendix C. — **Fill:** #35 (UC summary), #34 (SC) · **From:** `docs/requirements-workshop.md` (#19), `docs/rs/scenarios.md`, sample app (#33) and pilot apps (#21)

### 3.2 Functional requirements
_What:_ at least 25 `FR-xx`, grouped by area below, in the §1.5 table shape; every FR traces to at least one `SC-xx`. — **Fill:** #34

#### 3.2.1 Object recognition and Object Spy
_What:_ element under cursor, multi-property descriptor, window snapshot, win32 fallback, highlight overlay and pick hotkey. — **From:** #11, #12, #22, #23, #24 · **Input:** hasan (agent), omer (Spy view)

#### 3.2.2 Object repository
_What:_ adding elements, stable logical names (`screen.element`), primary and fallback properties, resolution per app version, snapshot import. — **From:** #15, #25, #30 · **Input:** omer

#### 3.2.3 Test authoring: steps and codeless editor
_What:_ the five keywords (Click, Type, Select, Verify, Wait) in one step schema; create, reorder and edit steps; object picker; tests API. — **From:** #13, #38, #39 · **Input:** omer

#### 3.2.4 Playback, smart waits and checkpoints
_What:_ playing steps by logical name, readiness waits (exists, visible, enabled) with a configurable timeout, property checkpoints, step result per step. — **From:** #26, #40 · **Input:** hasan

#### 3.2.5 Runs, reports and CLI runner
_What:_ run from the editor with live status, run history, screenshot per step, HTML report, headless CLI runner writing JUnit XML, CI job. — **From:** #44, #51, #54, #59, #61, #66, #67, #68 · **Input:** omer, hasan (CLI)

#### 3.2.6 Turkish NL assistant (C1)
_What:_ Turkish description → suggested steps grounded in the repository, validated against the schema and repository, approved by the user; never used during playback. — **From:** #37, #58, #71, #78

#### 3.2.7 Self-healing proposals and approval (C2)
_What:_ candidate generation and weighted scoring with per-property contributions, "repair proposed" step status, approval screen, repository changes only after approval. — **From:** #42, #43, #49, #73, #74, #75 · **Input:** hasan (playback side), omer (API and screen)

#### 3.2.8 Change-impact analysis (C3)
_What:_ objects changed between two app versions, the tests that use them, pending healing proposals. — **From:** #81 · **Input:** omer

#### 3.2.9 Failure triage and decision log
_What:_ rule-based classification of failed steps (element not found, unexpected window, assertion failed, timeout) and the logged decision examples for semester 2. — **From:** #63

#### 3.2.10 Projects, applications, users and settings
_What:_ projects, applications and versions, server connection settings, local accounts and roles. — **From:** #32, #60, #128 · **Input:** omer

### 3.3 Performance requirements
_What:_ `NFR-xx` with numbers — response times (Spy pick, server API, step overhead beyond the wait, report generation, NL suggestion latency on team hardware), default step timeout, capacity (concurrent clients, repository size), memory needed by the local model. — **Fill:** #34 · **Input:** hasan (playback timings), omer (API, UI)

### 3.4 Usability requirements
_What:_ usable by non-programmers without code, Turkish UI labels, steps readable as sentences, errors that say what to do; SUS study planned for semester 2 [39]. — **Fill:** #34, #35 · **From:** brief, #104 · **Input:** omer

### 3.5 Interface requirements
_What:_ requirement-level description of each interface (what is exchanged, direction, binding); message formats stay in the contract documents and the SDD.

#### 3.5.1 User interfaces
_What:_ the client screens (Spy, repository, editor, NL chat, run status and history, report, healing approval, change impact) and rules common to all (language, hotkeys, highlight overlay, DPI scaling). — **Fill:** #35 · **From:** #24, #30, #38, #44, #67, #75, #78, #81 · **Input:** omer

#### 3.5.2 Hardware interfaces
_What:_ Windows test machine and display (scaling and multiple monitors), no special hardware; GPU optional for the AI service (D2, #131). — **Fill:** #35 · **Input:** hasan

#### 3.5.3 Software interfaces
_What:_ the AUT through Microsoft UI Automation and win32 via pywinauto [8][30]; supported Windows versions; Neo4j Community Edition over Bolt [38]; Ollama or llama.cpp [32][33]; JUnit XML consumers and the GitHub Actions Windows runner. — **Fill:** #35 · **Input:** hasan (UIA), omer (Neo4j, CI)

#### 3.5.4 Communication interfaces
_What:_ client ↔ server REST, plus WebSocket for live run status (`docs/api/openapi.yaml`, #31, #52); client ↔ agent JSON-RPC over a localhost-only WebSocket (`docs/agent-rpc.md`, #16); server ↔ AI service HTTP, authoring time only; server ↔ Neo4j Bolt; all inside the closed network. — **Fill:** #35 · **From:** [architecture](../../memory-bank/project/architecture.md) "Contracts" · **Input:** omer

### 3.6 Logical database requirements
_What:_ what must be stored and the integrity rules — graph model ([`docs/graph-model.md`](../graph-model.md), #14), step schema (`schemas/step.schema.json`, #13), element and snapshot schemas (#11, #12), snapshots kept per app version, UUID ids, screenshots as files on the server disk with paths in the graph, retention and backup. — **Fill:** #35 · **Input:** omer

### 3.7 Design constraints
_What:_ standards and fixed decisions the design must follow — accepted ADRs (stack, Neo4j only, Windows first, LLM authoring-only, approval-gated healing, TypeScript client, graph migrations), contracts frozen at G1 (#52), standards complied with ([40], JSON Schema, JUnit XML). — **Fill:** #35 · **From:** [ADR index](../../memory-bank/decisions/README.md)

### 3.8 Software system attributes

#### 3.8.1 Reliability
_What:_ deterministic playback (no model at run time), flaky-rate target, smart waits instead of fixed sleeps. — **Fill:** #34 · **From:** brief success criteria (RQ2), #69 · **Input:** hasan

#### 3.8.2 Availability
_What:_ behaviour when a part is down — everything except NL generation works without the AI service; the client restarts a crashed agent. — **Fill:** #35 · **From:** #17, plan "Architecture"

#### 3.8.3 Security and closed-network operation
_What:_ no runtime call outside the closed network (no CDN, telemetry or auto-update), agent reachable only from localhost with a token, local accounts and roles, test data stays in-house. — **Fill:** #34 · **From:** brief, #16, #60, #85

#### 3.8.4 Maintainability
_What:_ tests refer to logical names, not coordinates; versioned contracts with contract tests; module tests in CI. — **Fill:** #35 · **From:** conventions, #52

#### 3.8.5 Portability
_What:_ supported Windows versions for test machines, backend via Docker Compose, driver interface left open for web and mobile drivers later. — **Fill:** #35 · **Input:** omer, hasan

#### 3.8.6 Installation and operation
_What:_ one Windows installer for client and agent, installable on an offline machine; backend started with one `docker compose up`; offline AI-service package; backup and restore of the graph and screenshot store. — **Fill:** #35 · **From:** #82, #84, #85 · **Input:** omer

### 3.9 Supporting information
_What:_ how RQ1–RQ5, H1–H3 and the success criteria map to requirement IDs, and which targets are measured in `eval/` rather than tested. — **Fill:** #35 · **From:** brief "Research questions" · **Input:** hasan (RQ1, RQ2, RQ5)

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
_What:_ where verification runs — CI (Linux and Windows runners), the weekly Windows session (`needs-windows-test`), sample app (#33) and pilot apps (#21), clean offline VM for the air-gapped test (#85). — **Fill:** #35 · **Input:** hasan

### 4.3 Verification of each requirement
_What:_ the method and the planned evidence for every FR and NFR (section 4 parallels section 3, as 29148 asks); kept in the §5 matrix rather than repeated here. — **Fill:** #35

### 4.4 Acceptance
_What:_ gate criteria G0–G4 and the semester-1 success criteria as the acceptance basis for the system; how the RS itself is accepted (advisor). — **Fill:** #35 · **From:** brief, [working agreement](../working-agreement.md)

## 5 Traceability

### 5.1 Traceability matrix
_What:_ one row per FR and NFR — `FR/NFR-xx | SC-xx | UC-xx | Verification | Test or evidence (pytest node id, eval script, issue comment) | Status`. — **Fill:** #34 (FR ↔ SC ↔ UC), #35 (tests); refreshed at G2 (#70)

### 5.2 Coverage checks
_What:_ counts and gaps — ≥ 30 SC, ≥ 25 FR, every FR → at least one SC, every UC → at least one FR, every Must requirement → a test or a planned issue. — **Fill:** #34, #35

## Appendices

### Appendix A — Glossary and acronyms
_What:_ the project [glossary](../../memory-bank/project/glossary.md) plus RS terms (FR, NFR, UC, SC, MoSCoW, T/D/I/A). — **Fill:** #35

### Appendix B — Use-case catalogue
_What:_ the full use-case descriptions, condensed from the workshop notes. — **Fill:** #35 · **From:** `docs/requirements-workshop.md` (#19)

### Appendix C — Reference scenarios
_What:_ `docs/rs/scenarios.md`, included in full in the submitted PDF so the RS stands alone. — **Fill:** #34, #41

### Appendix D — Mapping to ISO/IEC/IEEE 29148:2018 §9.6

| 29148 SRS item | Here |
|---|---|
| Purpose · Scope | 1.1 · 1.2 |
| Product perspective | 1.3.1 (summary), 3.5 (interface requirements) |
| System, user, hardware, software, communications interfaces | 3.5 |
| Memory constraints | 3.3 (memory of the local model); no other limit applies |
| Operations · Site adaptation | 3.8.6 (offline install, server settings #32) |
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
_What:_ every `TBD-n` in the document with its owner and the issue that closes it; must be empty, or each item explicitly deferred, by #41. Known now: the project's own licence; supported Windows versions; response-time values; final user roles (#19). — **Fill:** #34, #35
