# AYNA client UI design

Status: **draft for team review** (#183). Nothing here is built yet. The shell and shared styles are built only after the team has reviewed these pages; decisions from the review go into `memory-bank/tasks/183-ui-design.md`.

Owner: omer. The RS lists the screens (§3.5.1) and the SDD will link here for layouts.

| File | What it holds |
|---|---|
| [style-guide.md](style-guide.md) | Layout grid, colours, type, components, wording rules, the plain-language glossary |
| [flows.md](flows.md) | How a user moves between screens for the main tasks |
| [wireframes.md](wireframes.md) | One wireframe per screen of RS §3.5.1, with what each part does |

## Why

In the #25 manual checks the team found the client hard to use and hard to explain: screens are forms stacked under each other, there is no navigation, and labels use internal terms (primary/fallback, snapshot, descriptor). AYNA's users are mostly not programmers (RS §1.3.3, NFR-14), and AYNA should be easier and nicer to use than TestComplete.

## Design principles

1. **One window, one place for each thing.** A fixed shell: top bar for *context* (application, version, user, language, agent), left navigation for *places* (Spy, Repository, Tests, Runs, …), and the work area for the current task. Nothing scrolls off to the bottom of a long page.
2. **Context is chosen once.** The application and its version are chosen in the top bar and apply to every screen. Forms never ask for them again.
3. **Plain words first, details on demand.** Every screen speaks in the user's terms ("Find by", "Repair suggestion", "Check"). Internal terms (AutomationId, snapshot, fallback, score) appear only under **Advanced** or in a tooltip.
4. **Side by side, not one under another.** Work areas are split into panels: *list → details*, or *source → item → properties*. Choosing an item never moves the panels.
5. **Every state is designed.** Each screen has a loading, empty, error and success state, and a state for "not available yet" (a later issue) or "not possible now" (agent stopped, AI service down, not an admin).
6. **Errors say what, where and what next.** They name the URL, element, step or field they concern (NFR-15), appear next to their subject, and keep what the user typed.
7. **Closed network.** CSS only, system fonts, no icon font or image from the network, no new dependency. Icons are a handful of inline SVGs in the client.

## Questions for the team review

Answer in the PR or at the review; the answers go into the task note.

1. **Navigation items.** The issue names Object Spy, Repository, Tests and Runs. The wireframes add **Repairs** (healing approval, with a count badge, so a reviewer has a queue and not only a link from the report) and **Changes** (change impact) as the last two, shown as unavailable until #75 and #81. Keep, or reach them only from Runs and Repository?
2. **Where the NL panel lives.** Proposed: a panel on the right side of the test editor that the user opens with "Describe in Turkish" (#78). Alternative: its own screen.
3. **Live run status.** Proposed: inside the test editor (each step row gets its status, a run bar on top), not a separate screen, so the user sees the steps they just wrote. Run history keeps finished runs.
4. **Theme.** Proposed: follow the operating system's light or dark setting, with no switch in semester 1. Enough?
5. **Window size.** Designed for 1280 × 720 (a laptop at 150 % scaling) and up; minimum 1024 × 640. Enough for the pilot machines?
6. **Words.** Check the glossary in [style-guide.md](style-guide.md#plain-language-glossary). Especially "Repair suggestion" for healing proposal and "Element name" for logical name. The Turkish column is a first draft for #185 (galip, hasan: please correct).
