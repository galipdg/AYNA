# Project brief

Last reviewed: 2026-10-25 · Full plan: "AYNA – 14-Week Project Plan" (Claude Docs). Tasks: GitHub Issues.

## Problem

Long-lived desktop software (simulation, command-and-control, training systems) needs UI regression tests on every release. Commercial tools (TestComplete, Ranorex, UFT One) are licensed per user — ASELSAN's test unit had two TestComplete licences shared by the whole unit — and they are hard to use on closed networks (TestComplete's self-healing needs SmartBear's OCR web service). Open-source options (FlaUI, pywinauto) need code and have no recorder, repository or reports.

## What we build

The core of a TestComplete-style platform for **Windows desktop apps**, hosted in-house, running on a closed network, usable by non-programmers:

1. Object recognition + Object Spy (UI Automation tree, multi-property descriptors, win32 fallback).
2. Graph object repository in Neo4j: stable logical names, primary + fallback properties.
3. One versioned JSON step schema: keywords Click, Type, Select, Verify, Wait.
4. Smart-wait playback (exists + visible + enabled, configurable timeout) with property checkpoints.
5. Codeless editor, HTML report with a screenshot per step, CLI runner writing JUnit XML.
6. Recorder — semester 2.

## Contributions (research side)

- **C1** Turkish natural language → steps with a local open-weight model, grounded in the repository; used only while writing a test, never during playback.
- **C2** Explainable, approval-gated self-healing: weighted similarity with per-property contributions; never applied mid-run.
- **C3** Change-impact analysis: which tests a UI change affects, from the graph.
- **C4** Open evaluation set (NL/step pairs, controlled UI-change and bug-injected app versions).
- Semester 2: calibrated decision layer (rule book first, local decision model, human below threshold).

## Research questions

RQ1 recognition rate · RQ2 replay consistency (flaky rate) · RQ3 Turkish NL accuracy (H2: repository context helps) · RQ4 weighted vs single-property healing (H1) · RQ5 approval-gated vs auto-applied healing on bug-injected versions (H3, full test in semester 2). Paired tests: McNemar (α = 0.05); proportions with Wilson CIs.

## Success criteria

| Criterion | End of semester 1 (19 Jan 2027) | End of project (June 2027) |
|---|---|---|
| Recognition of standard controls | ≥ 90% | ≥ 90% |
| Replay without manual fixes | ≥ 10 reference scenarios | ≥ 85% of recorded scenarios |
| Flaky rate (10 runs) | < 10% | < 5% |
| Turkish NL → steps | ≥ 60% step accuracy on held-out split | ≥ 70% scenarios need no fix |
| Self-healing, controlled changes | H1 tested offline | ≥ 80% correct matches |
| Closed network | Full stack runs with network off | Same, HAVELSAN-like environment |

## Calendar

Semester 1: 20 Oct 2026 – 25 Jan 2027, weeks start Tuesday (advisor meeting). RS due 23 Nov, SDD due 7 Dec. Gates: G0 walking skeleton (wk 3) · G1 design baseline (wk 7) · G2 MVP core (wk 9) · G3 feature freeze (wk 12) · G4 demo (wk 14).

## Out of scope (semester 1)

Web/mobile drivers, visual/OCR checkpoints (unless RQ1 shows > 10% unrecognised), code injection into the app, script-based tests, RPA, data-driven tests and the recorder (semester 2).
