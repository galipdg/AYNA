# Literature review

Annotated sources behind AYNA's design and research questions. Section 1 (#10) covers test fragility, locators and self-healing; section 2 (#20) covers language models in GUI testing and decision models. Each entry gives the finding and what it means for AYNA. Full citations use the numbering of the project plan ("AYNA – 14-Week Project Plan", References).

Last update: 2026-10-26

## Section 1 — Fragility, locators, self-healing (#10)

### Assignment

Each member annotates at least three sources (#10 acceptance criteria). The split follows code ownership: whoever builds the part a source informs annotates it. Swap freely; update this table when you do.

| Plan ref | Source | Theme | Annotated by | Status |
|---|---|---|---|---|
| [3] | Hammoudi et al., ICST 2016 | Record/replay fragility | omer | done |
| [4] | Leotta et al., WCRE 2013 | Record/replay fragility | omer | done |
| [23] | Healenium | Test repair / self-healing | omer | done |
| [7] | Similo (Nass et al., TOSEM 2023) | Robust locators | galip | todo |
| [10] | WATER (Choudhary et al., 2011) | Test repair / self-healing | galip | todo |
| [11] | Vista (Stocco et al., ESEC/FSE 2018) | Test repair / self-healing | galip | todo |
| [5] | ROBULA+ (Leotta et al., JSEP 2016) | Robust locators | hasan | todo |
| [6] | Contextual clues (Yandrapally et al., ISSTA 2014) | Robust locators | hasan | todo |
| [12] | Luo et al., FSE 2014 | Flaky tests | hasan | todo |
| [8] | Sikuli (Yeh et al., UIST 2009) | Visual GUI testing | hasan | todo |
| [9] | Alégroth et al., IST 2016 | Visual GUI testing | hasan | todo |

Entry format: **Citation** · **Finding** (what the source shows, with its numbers) · **What it means for AYNA** (design consequence, linked to a brief item, RQ or ADR) · **Source checked** (what was actually read).

### 1.1 Record/replay fragility

#### [3] Hammoudi, Rothermel, Tonella — Why do record/replay tests of web applications break?

- **Citation:** M. Hammoudi, G. Rothermel, P. Tonella, "Why do record/replay tests of web applications break?," IEEE ICST, 2016.
- **Finding:** Selenium IDE suites were replayed across 300 versions of 5 open-source web apps, giving 722 test breakages; 3 more apps (153 versions, 343 breakages) validated the taxonomy without changes. Breakages fall into five causes: locators, values and actions, page reloading, user session times, popup boxes. Locators caused over 73% of breakages, and attribute-based locators (id, name) alone over 50% of all breakages. The authors note this does not prove attribute locators are worse, since counts are not normalised by how often each strategy is used, and conclude that repairing locator breakages pays off most.
- **What it means for AYNA:**
  - Element identification is the main maintenance risk, so it is AYNA's core: multi-property descriptors with primary and fallback properties in the object repository (brief items 1–2) and explainable self-healing (C2).
  - Even "stable" attributes break. On the desktop the analogues are `AutomationId` and `Name`, so a descriptor must not rely on one property; this is the motivation for RQ4 / H1 (weighted vs single-property healing).
  - Two of the five causes (page reloading, popups) are timing and window-state problems, which smart-wait playback (brief item 4) and RQ2 address.
  - The five-cause taxonomy can label the breakages in our controlled UI-change versions (C4), so our numbers are comparable with this study.
  - Gap: web DOM and Selenium IDE only; no equivalent study exists for the Windows UI Automation tree.
- **Source checked:** paper summary (A. Colyer, *the morning paper*, 2016, linked from the plan); numbers above are quoted from it.

#### [4] Leotta, Clerissi, Ricca, Tonella — Capture-replay vs. programmable web testing

- **Citation:** M. Leotta, D. Clerissi, F. Ricca, P. Tonella, "Capture-replay vs. programmable web testing: An empirical assessment during test case evolution," WCRE, pp. 272–281, 2013. DOI 10.1109/WCRE.2013.6671302.
- **Finding:** On six open-source web apps, suites were built twice — capture-replay (Selenium IDE) and programmable (Selenium WebDriver) — and maintained across a new release. Programmable suites took 32–112% more time to develop but 16–51% less time to maintain; in most cases their cumulative cost fell below capture-replay after one to three releases.
- **What it means for AYNA:**
  - Recorded tests are cheap to create and expensive to keep; non-programmers lose that trade-off after a few releases. A codeless tool has to give recorded tests the maintainability of programmed ones without asking for code.
  - Our interpretation: the object repository plays the role a shared locator layer plays in programmable suites. Steps refer to logical names (brief item 2), so a UI change is fixed once in the repository, not in every test. C3 (change-impact analysis from the graph) then shows which tests a change touches.
  - Evaluation idea: measure repair effort per UI-change version (C4) with and without the repository and healing, in the spirit of this cost comparison.
  - Gap: web only; no codeless or self-healing condition was compared.
- **Source checked:** abstract only, as indexed by web search (2026-10-26). The full PDF (https://sepl.dibris.unige.it/publications/2013-leotta-WCRE.pdf) could not be retrieved: the server refused the connection. Per-application figures and the method are not verified; read the PDF before citing details in the RS.

### 1.2 Robust locators

#### [5] ROBULA+ — *to be annotated by hasan*

#### [6] Contextual clues — *to be annotated by hasan*

#### [7] Similo — *to be annotated by galip*

### 1.3 Visual GUI testing

#### [8] Sikuli — *to be annotated by hasan*

#### [9] Alégroth et al. — *to be annotated by hasan*

### 1.4 Test repair / self-healing

#### [10] WATER — *to be annotated by galip*

#### [11] Vista — *to be annotated by galip*

#### [23] Healenium (EPAM, open source)

- **Citation:** EPAM, *Healenium*, https://healenium.io, source at https://github.com/healenium (Apache-2.0). Industrial tool, not a peer-reviewed paper.
- **Finding:** Healenium wraps Selenium WebDriver (`SelfHealingDriver`); Appium is also supported. After each successful lookup it stores the locator as a baseline in a PostgreSQL-backed service (`hlm-backend`). When a lookup throws `NoSuchElementException`, it compares the stored element path with the current page (the docs name an "LSC", i.e. longest-common-subsequence, algorithm), ranks candidate locators, and — if the best score is above `score-cap` (e.g. 0.5) — performs the action with the highest-scoring locator and lets the test continue in the same run. It produces a report with the healed locator, a screenshot and a feedback button; an IntelliJ plugin (`hlm-idea`) writes healed locators back into test code. Healing can be switched off globally (`heal-enabled`) or per method (`@DisableHealing`).
- **What it means for AYNA:**
  - It is the closest open-source analogue of C2, and it differs exactly where AYNA's ADR does: Healenium heals mid-run, so a test can pass after the element changed because of a real bug. AYNA records a proposal and never applies it during playback (decision 2026-10-20 approval-gated self-healing; RQ5 / H3).
  - Worth copying: a baseline captured on every successful find, a configurable score threshold, and a report entry per healing with a screenshot. These map onto the healing proposals API (#74) and the approval screen (#75).
  - Where AYNA goes further: Healenium shows one opaque score; AYNA shows per-property contributions so a tester can judge a proposal (C2), and an approve/reject decision updates the repository, not test code, because tests refer to logical names.
  - Gap: web and mobile only (DOM / Appium page source); no Windows desktop support and no closed-network packaging story beyond self-hosted Docker.
- **Source checked:** healenium.io "How Healenium works", the `healenium` and `healenium-web` GitHub READMEs (2026-10-26).

### 1.5 Flaky tests

#### [12] Luo et al. — *to be annotated by hasan*

### Gaps table

Copied from the project plan (section "What has been done"). Keep the two in sync: if an annotation changes a finding or gap, update both. Rows 1–5 are covered in section 1; the LLM row in section 2 (#20); the tool rows in detail in [`tool-matrix.md`](tool-matrix.md) (#18).

| Area | Key work | Finding | Gap for us |
|---|---|---|---|
| Record/replay fragility | Hammoudi et al., ICST 2016 [3]; Leotta et al., WCRE 2013 [4] | Over 70% of 722 studied test breakages came from element locators; record/replay is cheap to create but costly to maintain | Element identification must survive UI changes |
| Robust locators | ROBULA+ [5]; contextual clues [6]; Similo [7] | Similo's weighted multi-attribute similarity cut wrong element matches from 27% to 11% on 48 websites | Studied on the web DOM, not on the desktop UI Automation tree |
| Visual GUI testing | Sikuli [8]; Alégroth et al. [9] | Screenshot matching is technology-independent | Sensitive to resolution, theme and layout changes |
| Test repair / self-healing | WATER [10]; Vista [11]; Healenium [23] | Broken web locators can be repaired automatically | Web-only; fixes are often applied silently, which can hide real bugs |
| Flaky tests | Luo et al., FSE 2014 [12] | Async waits and timing are leading causes of flaky results | Playback needs readiness-based waits, not fixed sleeps |
| LLMs in testing | Survey [14]; GPTDroid [15]; AUITestAgent [16] | AUITestAgent reached a 77% task completion rate from natural-language requirements on mobile apps | Mostly mobile/web and cloud models; not desktop, not closed-network, not tied to an object repository |
| Commercial tools | TestComplete [21], Ranorex [32], UFT One [31] | Recorder, object repository, keyword tests, reports | Per-user licences; TestComplete's basic plan starts at about $1,210 per user per year [22] |
| Open-source tools | FlaUI [18], pywinauto [33], WinAppDriver [19], Robot Framework [20] | Programmatic UI Automation access; keyword-driven testing | No recorder, repository or self-healing; WinAppDriver's latest stable release is v1.2.1 and it has not had a new stable release for years |

## Section 2 — Language models in GUI testing, decision models (#20)

*To be written under #20 (galip).*
