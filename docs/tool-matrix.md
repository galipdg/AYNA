# Tool comparison matrix

How seven Windows desktop UI test tools cover the features AYNA targets ([brief](../memory-bank/project/brief.md)). Input for the literature review (#10) and the Requirements Specification. Issue: #18.

- **Sources.** Every cell links to its source in the footnotes: vendor documentation, the project's own repository/package page, or (marked *3rd party*) another site where the vendor publishes nothing. Nothing here is "tested by us" yet; hands-on checks would need the weekly Windows session and the commercial licences.
- **Accessed** 2026-10-26. Vendor docs are versioned; the footnote names the doc version where the page has one. Commercial features change often, so re-check before quoting a cell in the RS.
- **Robot Framework** is a generic keyword engine; its desktop column assumes [robotframework-flaui](https://github.com/GDATASoftwareAG/robotframework-flaui), the maintained Windows GUI library built on FlaUI.
- **AYNA (target)** shows what we plan, not what exists; its sources are our own decisions.

## Matrix

| # | Feature | TestComplete | Ranorex Studio | UFT One | FlaUI | pywinauto | WinAppDriver | Robot Framework | AYNA (target) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Windows UI technologies | Win32, .NET WinForms, WPF and more [^tc1] | Win32, WinForms, WPF, UIA plugins [^rx1] | Standard Windows, .NET WinForms, WPF add-ins [^uf1] | Win32, WinForms, WPF, Store apps (UIA2/UIA3) [^fl1] | Win32 backend + UIA backend (WinForms, WPF, Store, Qt5) [^pw1] | UWP, WinForms, WPF, Win32 [^wa1] | Win32, WinForms, WPF, Store apps via FlaUI [^rf1] | UIA tree with win32 fallback [^ay1] |
| 2 | Recorder | Yes [^tc2] | Yes [^rx2] | Yes [^uf2] | No [^fl1] | No; "record-replay" listed as planned [^pw2] | UI Recorder, pre-release v1.1 (2018) [^wa2] | No (not in core or library) [^rf2] | Semester 2 [^ay1] |
| 3 | Object Spy / inspector | Object Spy [^tc3] | Ranorex Spy, Track / Instant Tracking [^rx3] | Object Spy / Object Identification Center [^uf3] | Separate tool: FlaUInspect [^fl3] | None built in; Inspect.exe, Spy++, py_inspect prototype [^pw1] | UI Recorder shows tree + XPath [^wa2] | External inspectors (FlaUInspect, Inspect) [^rf3] | Spy overlay in the client [^ay1] |
| 4 | Object repository (logical names) | Name Mapping repository with aliases [^tc4] | Repository items [^rx4] | Local and shared object repositories [^uf4] | No; locators live in code [^fl1] | No; `WindowSpecification` in code [^pw3] | No; locators in WebDriver client code [^wa1] | No central store; XPath in variables/resource files [^rf1] | Graph repository in Neo4j [^ay2] |
| 5 | Multi-property locators / fallback | Mapping criteria (basic, conditional, extended search); OCR fallback with add-on [^tc4] [^tc9] | RanoreXPath; RobustPath in Robust mode [^rx9] | Description properties → visual relation → Smart Identification → ordinal [^uf5] | Combinable property conditions, no fallback [^fl5] | Several criteria per spec, no fallback [^pw3] | One strategy per lookup (id, name, class, XPath) [^wa1] | XPath only [^rf1] | Primary + fallback properties per object [^ay1] |
| 6 | Codeless / keyword tests | Keyword tests [^tc6] | Action tables (basic + smart actions) [^rx6] | Keyword View (VBScript underneath) [^uf4] | No; C# code [^fl1] | No; Python code [^pw1] | No; Selenium/Appium client code [^wa1] | Keyword-driven text files [^rf6] | Codeless step editor, JSON step schema [^ay1] |
| 7 | Smart wait / synchronisation | Auto-wait timeout (default 10 s), `WaitProperty` [^tc7] | `Wait for` action + repository search timeout [^rx7] | Object synchronisation timeout, sync points [^uf7] | `Retry` helpers in code [^fl7] | `wait('exists visible enabled ready active')`, `Timings` [^pw7] | Client-side WebDriver waits only [^wa1] | `Wait Until Element Exist / Is Enabled` [^rf7] | exists + visible + enabled, configurable timeout [^ay1] |
| 8 | Property checkpoints | Property checkpoints (+ table, region, file ...) [^tc8] | Validation actions (`AttributeEqual` ...) [^rx7] | Standard checkpoints [^uf8] | Assertions in test code [^fl1] | Assertions in code (`is_enabled`, `verify_actionable`) [^pw8] | Assertions in client code [^wa1] | `Element Should Be ...`, `Get Property From Element` [^rf7] | Property checkpoints [^ay1] |
| 9 | Self-healing | Heals at runtime for that run only; saved to Name Mapping if the user accepts the fix; add-on licence [^tc9] | Robust mode, default since 10.1.1; healed steps logged as warnings [^rx9] | Smart Identification fallback at runtime [^uf5] | No [^fl1] | No [^pw1] | No [^wa1] | No [^rf1] | Proposals with per-property scores, applied only after approval [^ay3] |
| 10 | AI / natural-language authoring | AI test-data generation; no documented NL→test feature [^tc10] | None shipped; on the 2025 roadmap [^rx10] | UFT Aviator: plain-language features on a customer-supplied LLM, separate licence [^uf10] | No [^fl1] | No [^pw1] | No [^wa1] | Community RF-MCP server (not core) [^rf10] | Turkish NL → steps, local model, authoring time only [^ay4] |
| 11 | Report with screenshots | Test log with Visualizer screenshots [^tc11] | Report, screenshot per validation [^rx11] | Run results, screenshot per step or on error, movie [^uf11] | Screen/video capture API, no report [^fl11] | `capture_as_image()`, no report [^pw8] | None; left to the test framework [^wa1] | `log.html` / `report.html`, screenshot on failure [^rf11] [^rf7] | HTML report, screenshot per step [^ay1] |
| 12 | CLI runner / CI (JUnit) | Command line, exit codes, `/ExportSummary` JUnit XML; Jenkins [^tc12] | Command line, `/reporttype:JUnit`; Jenkins [^rx12] | CI utilities CLI; Jenkins plugin [^uf12] | Any .NET test runner [^fl1] | Any Python runner (e.g. pytest) [^pw1] | Server on `127.0.0.1:4723`; runner is the client's [^wa1] | `robot` CLI, `--xunit` [^rf11] | CLI runner writing JUnit XML [^ay1] |
| 13 | Closed-network use | Offline licence only on request, or on-prem licence server; self-healing OCR calls a SmartBear web service [^tc13] [^tc9] | On-prem License Manager; offline activation with a licence file carried from an online machine [^rx13] | Seat licence or on-prem AutoPass server; AI detection runs locally, models installable offline [^uf13] | Yes; library, no licence check [^fl1] | Yes; library, no licence check [^pw1] | Yes; local service (needs Developer Mode) [^wa1] | Yes; no licence check [^rf1] | Full stack runs with network off [^ay1] |
| 14 | Licence and cost | Commercial, quote-based plans [^tc14] | Commercial, quote only; floating Enterprise + Runtime seats [^rx14] | Commercial, seat or concurrent [^uf14] | MIT, free [^fl1] | BSD-3-Clause, free [^pw1] | Free; repo MIT [^wa1] | Apache-2.0 + MIT library, free [^rf1] | Licence-free, hosted in-house [^ay5] |
| 15 | Maintenance (as of 2026-10) | Active (15.8x docs) [^tc12] | Active (10.x) [^rx9] | Active; renamed OpenText Functional Testing (26.x) [^uf10] | v5.0.0 (2025-02); commits in 2026-08 [^fl1] | 0.6.9 (2025-01); commits in 2026-10 [^pw1] | Last stable v1.2.1 (2020-11); ~1.1k open issues [^wa15] | RF 7.5 (2026-09), library 6.0.0 (2026-10) [^rf1] | Built in this project, Oct 2026 – Jun 2027 [^ay1] |

## What it tells us

- Only the three commercial tools have the full set (recorder, spy, repository, keyword tests, reports), and all three are licensed per seat or concurrent user, the cost problem in the [brief](../memory-bank/project/brief.md).
- None of the open-source tools has a repository, a codeless editor or self-healing; they are libraries you call from code. FlaUI and pywinauto are candidates for AYNA's recognition layer, not alternatives to the product.
- In all three commercial tools healing happens during the run, so a healed step can pass against the wrong object (rows 5, 9). TestComplete asks the user to accept a fix only to make it permanent, and its OCR-based healing needs an external web service, which rules it out on a closed network. None of their docs describes per-property scores for a match. That is the gap behind C2: no healing mid-run, explainable proposals, applied only after approval.
- Natural-language authoring exists only in UFT One (Aviator), on an LLM the customer supplies, with a separate licence; nothing targets Turkish. That is the gap behind C1.
- WinAppDriver, the only Microsoft option, has had no stable release since 2020.

## Sources

TestComplete (SmartBear docs, 15.7x–15.8x):

[^tc1]: [Supported Development Tools](https://support.smartbear.com/testcomplete/docs/general-info/supported-technologies/development-tools.html) · [Testing WPF Applications](https://support.smartbear.com/testcomplete/docs/app-testing/desktop/wpf/about.html)
[^tc2]: [Recording Automated Tests](https://support.smartbear.com/testcomplete/docs/testing-with/creating/recording/index.html)
[^tc3]: [Object Spy](https://support.smartbear.com/testcomplete/docs/testing-with/exploring-apps/object-spy.html)
[^tc4]: [Name Mapping](https://support.smartbear.com/testcomplete/docs/testing-with/object-identification/name-mapping/about.html)
[^tc6]: [Keyword Tests](https://support.smartbear.com/testcomplete/docs/keyword-testing/index.html)
[^tc7]: [WaitProperty Method](https://support.smartbear.com/testcomplete/docs/reference/test-objects/members/common-for-all/waitproperty-method.html) · [Waiting for a process or window (auto-wait timeout)](https://support.smartbear.com/testcomplete/docs/ver-15-0/app-objects/common-tasks/waiting-process-or-window-activation.html)
[^tc8]: [About Checkpoints](https://support.smartbear.com/testcomplete/docs/testing-with/checkpoints/about.html)
[^tc9]: [Self-Healing Tests](https://support.smartbear.com/testcomplete/docs/testing-with/running/self-healing-tests.html) · [Intelligent Quality add-on](https://smartbear.com/product/testcomplete/features/intelligent-quality/)
[^tc10]: [SmartBear news release on HaloAI, 2024-06](https://smartbear.com/news/news-releases/expanding-haloai-footprint-smartbear-boosts-code/)
[^tc11]: [About Test Visualizer](https://support.smartbear.com/testcomplete/docs/testing-with/visualizer/index.html)
[^tc12]: [TestComplete Command Line](https://support.smartbear.com/testcomplete/docs/working-with/automating/command-line-and-exit-codes/command-line.html) · [Integration With Jenkins](https://support.smartbear.com/testcomplete/docs/working-with/integration/jenkins/index.html)
[^tc13]: [Offline Fixed User licence in private networks](https://support.smartbear.com/testcomplete/docs/licensing/id-based/private-networks/fixed-user.html) · [Floating licence in private networks](https://support.smartbear.com/testcomplete/docs/licensing/id-based/private-networks/floating.html)
[^tc14]: [TestComplete pricing (no list prices published)](https://smartbear.com/product/testcomplete/pricing/)

Ranorex Studio (Ranorex Help Center):

[^rx1]: [Supported technologies](https://www.ranorex.com/supported-technologies/)
[^rx2]: [Record your first test](https://support.ranorex.com/hc/en-us/articles/38006049041681-4-Record-Your-First-Test)
[^rx3]: [Instant Tracking](https://support.ranorex.com/hc/en-us/articles/38036333083793-Instant-Tracking) · [Track Button](https://support.ranorex.com/hc/en-us/articles/38036179623057-Track-Button)
[^rx4]: [Manage repository items](https://support.ranorex.com/hc/en-us/articles/38080234142993-Manage-repository-items)
[^rx6]: [Basic and Smart Actions](https://support.ranorex.com/hc/en-us/articles/38080091129617-Basic-and-Smart-Actions)
[^rx7]: [Action Properties (Wait for, Validate)](https://support.ranorex.com/hc/en-us/articles/38079925833873-Action-Properties)
[^rx9]: [Self-Healing](https://support.ranorex.com/hc/en-us/articles/38028419260433)
[^rx10]: [Ranorex blog, 2025 software testing quality report](https://www.ranorex.com/blog/software-testing-quality-report/)
[^rx11]: [Validate.Options (reportScreenshot)](https://api-manual.ranorex.com/en-US/api/Ranorex.Validate.Options.html)
[^rx12]: [Integration with CI/CD pipelines](https://api-manual.ranorex.com/en-US/guides/integration-with-cicd-pipelines.html) · [Create and run a Jenkins freestyle project](https://support.ranorex.com/hc/en-us/articles/38108619476241-Create-and-Set-Up-a-Jenkins-Project)
[^rx13]: [Install a Perpetual Floating License](https://support.ranorex.com/hc/en-us/articles/38008938331409)
[^rx14]: [Ranorex pricing (quote only)](https://www.ranorex.com/pricing/)

UFT One / OpenText Functional Testing (ADM Help Center):

[^uf1]: [Object Model Reference, 23.4](https://admhelp.microfocus.com/uft/en/23.4/UFT_Help/Content/Landing_Pages/OMR_Overview_Landing_Page.htm) · [WinObject (Standard Windows)](https://admhelp.microfocus.com/uft/en/2021-2023/UFT_Help/Subsystems/OMRHelp/Content/StdWin/STDPACKAGELib~WinObject.html)
[^uf2]: [Record a GUI test or component, 23.4–24.2](https://admhelp.microfocus.com/uft/en/23.4-24.2/UFT_Help/Content/User_Guide/Record_Test.htm)
[^uf3]: [Use the Object Identification Center, 23.4–24.2](https://admhelp.microfocus.com/uft/en/23.4-24.2/UFT_Help/Content/User_Guide/OIC.htm)
[^uf4]: [Add test objects to an object repository (Keyword View), 23.4–24.2](https://admhelp.microfocus.com/uft/en/23.4-24.2/UFT_Help/Content/User_Guide/Move_Objs_in_OR.htm)
[^uf5]: [Object identification process workflow, 2021–2023](https://admhelp.microfocus.com/uft/en/2021-2023/UFT_Help/Content/User_Guide/ObjID_Workflow.htm) · [Smart identification, 2021–2023](https://admhelp.microfocus.com/uft/en/2021-2023/UFT_Help/Content/User_Guide/Smart_Ident_Concept_TEST.htm)
[^uf7]: [Solve synchronization problems, 2021–2023](https://admhelp.microfocus.com/uft/en/2021-2023/UFT_Help/Content/User_Guide/Solve_Sync_Probs.htm)
[^uf8]: [Configure checkpoint details, 2021](https://admhelp.microfocus.com/uft/en/2021/UFT_Help/Content/User_Guide/Checkpoint_Properties_Dialog_Box.htm)
[^uf10]: [UFT Aviator, 26.1–26.3](https://admhelp.microfocus.com/uft/en/26.1-26.3/UFT_Help/Content/User_Guide/aviator.htm)
[^uf11]: [Screen Capture pane, 23.4–24.2](https://admhelp.microfocus.com/uft/en/23.4-24.2/UFT_Help/Content/User_Guide/Screen_recorder_options.htm)
[^uf12]: [UFT One and continuous integration, 23.4](https://admhelp.microfocus.com/uft/en/23.4/UFT_Help/Content/User_Guide/ci-tools.htm) · [UFT One and Jenkins, 23.4](https://admhelp.microfocus.com/uft/en/23.4/UFT_Help/Content/User_Guide/Jenkins.htm)
[^uf13]: [UFT One licensing, 23.4–24.2](https://admhelp.microfocus.com/uft/en/23.4-24.2/UFT_Help/Content/User_Guide/z_Ch_Apndx_UFTLicenses.htm) · [AI-based testing, 23.4–24.2](https://admhelp.microfocus.com/uft/en/23.4-24.2/UFT_Help/Content/User_Guide/AI-based-testing.htm)
[^uf14]: [Seat vs. concurrent licenses, 23.4–24.2](https://admhelp.microfocus.com/uft/en/23.4-24.2/UFT_Help/Content/User_Guide/seatvsconcurlice.htm)

FlaUI:

[^fl1]: [FlaUI repository and README](https://github.com/FlaUI/FlaUI) (licence, supported technologies, releases)
[^fl3]: [FlaUInspect](https://github.com/FlaUI/FlaUInspect)
[^fl5]: [ConditionFactory source](https://github.com/FlaUI/FlaUI/tree/main/src/FlaUI.Core/Conditions)
[^fl7]: [Retry.cs](https://github.com/FlaUI/FlaUI/blob/main/src/FlaUI.Core/Tools/Retry.cs)
[^fl11]: [Capture.cs](https://github.com/FlaUI/FlaUI/blob/main/src/FlaUI.Core/Capturing/Capture.cs) · [VideoRecorder.cs](https://github.com/FlaUI/FlaUI/blob/main/src/FlaUI.Core/Capturing/VideoRecorder.cs)

pywinauto:

[^pw1]: [pywinauto repository](https://github.com/pywinauto/pywinauto) (licence, releases) · [Getting Started Guide](https://pywinauto.readthedocs.io/en/latest/getting_started.html)
[^pw2]: [README, roadmap](https://github.com/pywinauto/pywinauto#readme)
[^pw3]: [Waiting for long operations (WindowSpecification)](https://pywinauto.readthedocs.io/en/latest/wait_long_operations.html)
[^pw7]: [Waiting for long operations](https://pywinauto.readthedocs.io/en/latest/wait_long_operations.html) · [timings.py](https://github.com/pywinauto/pywinauto/blob/master/pywinauto/timings.py)
[^pw8]: [pywinauto.base_wrapper](https://pywinauto.readthedocs.io/en/latest/code/pywinauto.base_wrapper.html)

WinAppDriver:

[^wa1]: [WinAppDriver repository and README](https://github.com/microsoft/WinAppDriver)
[^wa2]: [UI Recorder v1.1 release](https://github.com/microsoft/WinAppDriver/releases/tag/UIR-v1.1)
[^wa15]: [Releases](https://github.com/microsoft/WinAppDriver/releases) · [Microsoft Q&A: "Is WinAppDriver dead or not?"](https://learn.microsoft.com/en-au/answers/questions/1455246/is-the-tool-winappdriver-dead-or-not)

Robot Framework:

[^rf1]: [robotframework-flaui repository and README](https://github.com/GDATASoftwareAG/robotframework-flaui) · [Robot Framework repository](https://github.com/robotframework/robotframework)
[^rf2]: [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
[^rf3]: [robotframework-flaui on PyPI (inspection tools)](https://pypi.org/project/robotframework-flaui/1.3.2/)
[^rf6]: [User Guide: creating test cases](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-cases)
[^rf7]: [robotframework-flaui keywords 6.0.0](https://gdatasoftwareag.github.io/robotframework-flaui/keywords/6.0.0.html)
[^rf10]: [Robot Framework forum: Open Space October 2025 (RF-MCP)](https://forum.robotframework.org/t/open-space-october-2025/9347)
[^rf11]: [User Guide: output files (log, report, xUnit)](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#output-files)

AYNA:

[^ay1]: [Project brief](../memory-bank/project/brief.md)
[^ay2]: [ADR: Neo4j as the single database](../memory-bank/decisions/2026-10-20-neo4j-single-database.md) · [Graph model](graph-model.md)
[^ay3]: [ADR: Self-healing proposes, never applies mid-run](../memory-bank/decisions/2026-10-20-approval-gated-self-healing.md)
[^ay4]: [ADR: Language models only at authoring time](../memory-bank/decisions/2026-10-20-llm-authoring-only.md)
[^ay5]: [AGENTS.md §1 (project summary)](../AGENTS.md)
