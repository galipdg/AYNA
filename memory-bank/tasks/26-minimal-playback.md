# #26 Minimal playback: Click and Type by logical name

- Issue: https://github.com/galipdg/AYNA/issues/26
- Owner: hasan · Branch: `hasan/26-minimal-playback`
- Started: 2026-11-07 · Last update: 2026-11-07

## Why now

It is the **only unmet G0 criterion that is mine** (#28, gate on 9 Nov): "Agent replays Click and
Type by logical name". D1 is closed (#169 merged), Spy→Neo4j is omer's #186/#187, the Turkish-prompt
JSON is galip's #7. Both dependencies are on `main`: #16 (agent RPC, PR #135) and #13 (step schema
v0, PR #134).

## Approach

#26 is the **minimal slice of #40**, not a down payment on a different design. `docs/agent-rpc.md`
already drafts the method under "Proposed (#149)… The run request (**defined by #40**)" with
`targets` marked "name for **#40 to settle**", so the request shape is mine to fix, and #26 fixes
the part it needs in a way #40 and #73 extend without breaking.

**New code, all in my area** (`agent/ayna_agent/playback/`, per `agent/AGENTS.md`):

- `resolve.py` — return **every** element whose descriptor matches a property set, so that
  "more than one" is an answer. Pure: it takes descriptors and a parallel list of live elements
  and never touches either, which is why every rule in it is tested off Windows.
- `recognition/uia.py` gets `read_tree(handle, timeout_ms)` and keeps the live element per node.
  I first planned a second walk inside `playback/`, and that was the wrong instinct: it would
  have duplicated the property reading, the budget and the abandoned-thread handling, and worse,
  resolution would then compare against values derived by a *second* rule. `read_tree` is the
  existing walk without `snap.build`, so a target is matched against exactly the derivation
  (`model.describe_tree`) that produced the values the repository stored. `snapshot()` and
  `read_tree()` now share `_walk_window`.
- `actions.py` — Click and Type through UIA patterns only, never coordinates (`agent/AGENTS.md`).
- `runner.py` — walk the step document, resolve each target, act, produce one result per step.

**Not in #26** (they are #40, #63, #73): the other keywords, checkpoints, screenshots, healing,
`run.stepResult` notifications, the decision log, window discovery without a handle.

## Decisions (small, local to this task)

- 2026-11-07 — **`runSteps` params are `{handle, steps, targets}`** and the results come back as the
  method's **result**, not as notifications — reason: notifications are the v0.2 draft that #40 and
  #73 implement together with healing; a synchronous result is testable now and a superset later
  (the notification path adds messages, it does not change the request). `runId` and
  `appVersionId` from galip's draft are accepted and ignored in #26, so omer's client can already
  send the full shape.
- 2026-11-07 — **`handle` names the window to play against.** Galip's draft has no `handle` because
  by #40 a target's `windowTitle` is enough to find the window. For #26 an explicit handle is the
  honest minimum: the Spy already hands one out, it is exactly what `snapshot` takes, and window
  discovery is a separate problem with its own failure modes (FR-35's "unexpected window"). #40
  makes `handle` optional.
- 2026-11-07 — **`targets[name]` carries `properties` *and* `fallback`.** Galip's draft has only the
  recorded `properties`, because healing only needs those. But a repository object stores primary
  **and** fallback property sets (#25), and FR-06/FR-29 say the fallback is what is tried when the
  primary set stops matching, so playback cannot do its job without it. This is an addition to the
  draft and omer builds the request, so it goes to both of them.
- 2026-11-07 — **Ambiguity is a failure, never a guess.** More than one element matching the primary
  set ends the step as "element not found" with the count in the message; playback never picks the
  first match. Reason: UI Automation does not guarantee child order across runs, so picking one
  would make the same test act on different elements on different days and would show up in RQ2
  (#69) as AYNA's own flaky rate, indistinguishable from the application's. Decided in the #187
  review; it is the rule for #40 too.
- 2026-11-07 — **The fallback set is tried only when the primary set matches zero elements**, never
  when it matches several: a fallback replaces a primary set, it cannot narrow one.
- 2026-11-07 — **Smart wait, no fixed sleep** (`agent/AGENTS.md`): re-resolve every 250 ms until the
  target resolves to exactly one element or `timeoutMs` runs out. 250 ms is the interval the step
  schema v0.2 ADR records for row checks, kept the same here so there is one number. `timeoutMs: 0`
  means check once (RS NFR-05).

## Status

- [x] Branch, task note, issue moved to In progress on the Project
- [x] `resolve.py` + 24 unit tests against the real #11 trial-app tree
- [x] `actions.py` (Click, Type) + 15 unit tests with an injected pattern lookup
- [x] `runner.py` + 36 unit tests (order, stop-on-failure, waiting, per-step failures)
- [x] `recognition/uia.py`: `read_tree()` and the live element per node (see Decisions)
- [x] **`@pytest.mark.windows`: the 3-step login on the real trial app, 10/10** — plus the
      empty-value, fallback and ambiguity cases on the real app
- [x] `rpc.py` wiring (`5cfaf94`) + 37 tests in `tests/test_rpc_run_steps.py`, and the
      `docs/agent-rpc.md` section (`5ee6b26`) — both in **galip's** file/content, each in its
      own commit so he can take, move or redirect it
- [ ] PR open, galip's approval on the two commits above, omer told about `targets[].fallback`
- Next step: open the PR with `Closes #26`, request both reviews, and say in the body what each
  of them should check.

**Measured 2026-11-07 on this machine** (Windows 11 Pro 26300, 120 DPI, Python 3.13.0,
pywinauto 0.6.9, PySide6 6.12.0): agent suite **397 passed** in 10.4 s, ruff and format clean.
The five trial-app tests take 7.2 s together, the ten login runs included.

**Both acceptance criteria are met and measured**, not argued:
`test_the_three_step_login_passes_ten_times_out_of_ten` (10/10 on the real app, each run
resetting the status label first so it proves its own login) and
`test_no_coordinate_can_be_stored_in_a_test`.

## Manual checks

- **None needed.** Both acceptance criteria are automated:
  `test_the_three_step_login_passes_ten_times_out_of_ten` and
  `test_no_coordinate_can_be_stored_in_a_test`. The first is `@pytest.mark.windows` and also
  needs an interpreter that can import PySide6, which the agent environment does not have — so
  **it skips in CI** and the result above is from this machine. See "Open issues".

## Open issues

- **`rpc.py` and `docs/agent-rpc.md` are galip's.** Registering `runSteps` is two lines in his
  `Dispatcher` map and one method on his `Desktop` Protocol, and his #16 inbox note already says a
  backend swap in `rpc.main()` is "fine for you to change, or tell me". The contract section is his
  content in my folder. Plan: write the wiring, keep it in its own commit, and ask for his approval
  on the PR rather than merging it silently.
- The `targets[].fallback` addition changes what omer's client must send. Goes to his inbox and to
  the PR.

## Findings worth keeping

- **A passed Click does not mean the application has finished reacting.** The first draft of the
  10/10 test read the status label straight after `Invoke()` returned and saw it empty — on the
  *first* run only, because runs 2–10 were reading the message the previous run had left. All 30
  steps had passed. `Invoke()` returns when the provider accepts the call; Qt updates the label
  on its own event loop afterwards. **For #40 this is the design point for checkpoints:** a
  Verify has to wait for the *assertion* to come true, not only for its element to exist, or
  every check becomes a race that passes on the second run. The test now resets the label before
  each run and polls for the expected text.
- **A Qt line edit's UIA `Name` is its label, not its content.** `usernameInput` reports
  `name="Username"`, which is why a test that read `name` to check typing would pass while
  typing nothing. The typed text is in `ValuePattern.CurrentValue`. This is the same
  Name-versus-Value split the step schema v0.2 cell-text rule is about, now on an Edit.
- `usernameLabel` and `usernameInput` **both** have `name="Username"` in the trial app, so
  `{name: "Username"}` is genuinely ambiguous there. That made the ambiguity rule testable
  against a real application rather than a constructed case.

## Handoff

- The branch carries one line that also lives on `hasan/review-round-1107` (PR #198): adding
  `nearest_label_source` to `model.NEVER_MATCH`. `resolve.MATCHABLE` is derived from that list
  and has to agree with the server's, and #198 was not merged yet. The text is identical on both
  branches, so the merge is clean whichever lands first.

## Outcome (fill when the issue closes)

Not closed.
