# AYNA client flows

Draft for the #183 team review. How a user moves between the screens of [wireframes.md](wireframes.md) for the main tasks. Screen names in **bold** are wireframe sections; UC numbers are the RS use cases.

## Map of places

```mermaid
flowchart LR
  subgraph before[Before login: no shell]
    S[Server settings] --> L[Log in] --> A[Choose application]
  end
  A --> SHELL
  subgraph SHELL[Shell: top bar + navigation]
    direction TB
    SPY[Object Spy]
    REPO[Repository]
    TESTS[Tests: list + editor + NL panel + live run]
    RUNS[Runs: history + run details + report]
    REP[Repairs]
    CHG[Changes]
    USR[Users and API tokens - admin]
    SET[Settings]
  end
  SPY -- "Add to repository" --> REPO
  REPO -- "Used by n tests" --> TESTS
  TESTS -- "Run" --> TESTS
  TESTS -- "Open run" --> RUNS
  RUNS -- "Review repair" --> REP
  REP -- "Run again" --> TESTS
  CHG -- "affected test" --> TESTS
  CHG -- "pending repair" --> REP
```

## F1 · First run (UC-01)

```mermaid
flowchart TD
  start([Client starts]) --> saved{Server saved?}
  saved -- no --> settings[Server settings]
  settings -- "Connect: AYNA answers" --> login[Log in]
  settings -- "no answer" --> err1[Error under the field names the URL] --> settings
  login -- ok --> apps{Application saved?}
  apps -- no --> picker[Choose application]
  picker -- "choose or add" --> versions{Application has a version?}
  versions -- no --> addver["Top bar: 'Add the version you are testing'"]
  versions -- yes --> spy[Object Spy, latest version chosen]
  addver --> spy
```

- The first application choice is a centred card; later the user changes application from the top bar.
- If there is no version yet, the shell still opens; the top bar's version menu shows **Add version** with a highlighted hint, and actions that need a version (Add to repository, Run) are disabled with a tooltip that points to it.

## F2 · Daily start

```mermaid
flowchart TD
  start([Client starts]) --> check[Check saved server] -- ok --> session{Session valid?}
  check -- fails --> settings[Server settings with the error]
  session -- no --> login[Log in] --> last
  session -- yes --> last[Shell at the last place, same application and version]
```

## F3 · Build the repository (UC-02, UC-03)

```mermaid
flowchart TD
  spy[Object Spy] --> win[Choose a window in the left panel]
  win --> cap[AYNA captures it; the tree fills the middle panel]
  cap --> pick{How to find the element}
  pick -- "click in the tree or search" --> el[Element chosen: outlined on screen, properties on the right]
  pick -- "hover it and press the pick hotkey" --> el
  el --> add["Add to repository (right panel)"]
  add --> name[Type the element name; AYNA suggests one]
  name --> save[Save]
  save -- ok --> done["✓ Saved login.okButton · link: Show in repository"]
  save -- "name already used" --> err[Error names the existing element] --> name
  done --> el
```

- The panels do not move while the user picks one element after another; the form closes after saving and the next element can be picked at once.
- **Show in repository** opens Repository with that element chosen.

## F4 · Write and run a test (UC-06, UC-07, UC-08, UC-09)

```mermaid
flowchart TD
  tests[Tests] --> new[New test: name it]
  new --> how{Add steps}
  how -- "by hand" --> step["Add step: action, element (from the repository), value"]
  how -- "Describe in Turkish" --> nl[NL panel: write, Suggest steps]
  nl --> review[Review suggested steps and reasons; edit]
  review -- "Add selected" --> steps[Steps in the editor]
  step --> steps
  steps --> check{Every step valid?}
  check -- no --> mark[Invalid step marked with the reason] --> steps
  check -- yes --> save[Save] --> run[Run]
  run --> live[Run bar on top; each step row shows its status live]
  live --> result{Result}
  result -- passed --> ok[✓ Passed · Run details]
  result -- failed --> fail[✕ Failed at step n · category · Run details]
  result -- "needs review" --> rev[! Needs review at step n · Review repair]
```

- The NL panel is disabled with a message when the AI service is not reachable (FR-27, FR-28); everything else works.
- A second client with the same test open sees the same run bar and statuses (FR-20, NFR-06).

## F5 · Review a repair (UC-12)

```mermaid
flowchart TD
  from1[Run result: Review repair] --> rep
  from2[Repairs list] --> rep
  rep[Repair suggestion: failing step + what was expected] --> cand[Choose one of 3 suggested elements]
  cand --> why[See why it matches: bars per property]
  cand --> show[Show on screen: outline on the running application]
  cand --> decide{Decide}
  decide -- "Use this element" --> confirm[Confirm dialog names the element and the version] --> updated[✓ Repository updated · Run again]
  decide -- "None of these" --> rejected[Step stays failed; repository unchanged]
  updated --> rerun[Tests: run again]
```

## F6 · A new build arrives (UC-01, UC-05, UC-13)

```mermaid
flowchart TD
  top[Top bar: Version menu] --> addv[Add version 1.3]
  addv --> spy[Object Spy: capture the changed windows]
  spy --> chg[Changes: compare 1.3 with 1.2]
  chg --> list[Changed elements → tests that use them → pending repairs]
  list --> open[Open an affected test] --> run[Run it]
```

## F7 · Interruptions (any screen)

| What happens | What the user sees | Where it returns |
|---|---|---|
| Session ended (401) | Login dialog over the current screen: "Your session has ended. Log in again." | Same screen, same unsaved input |
| Server unreachable | Page message under the header with **Try again**; the top bar shows the server as unreachable; the Spy keeps working (it needs only the agent) | Same screen |
| Agent stopped or failed | Top bar pill turns red; Spy and Run show a page message with **Start again** | Same screen |
| AI service down | NL panel disabled with a message; nothing else changes | |
| Application or version deleted on the server | Page message; the top bar opens its menu to choose again | |
| Not an admin | Users is not in the navigation; a link to it shows "Only admins manage users." | |

## F8 · Administration (UC-15)

```mermaid
flowchart TD
  nav[Navigation: Users - admins only] --> list[Users table]
  list --> addu[Add user panel: name, role, password]
  list --> pick[Choose a user] --> details[Role, Set password, Remove]
  details --> tok[API tokens - service accounts] --> create[Create token] --> secret[Token shown once with Copy hint]
```
