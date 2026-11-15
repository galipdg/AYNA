# #63 Rule-based failure triage + decision log

- Issue: https://github.com/galipdg/AYNA/issues/63
- Owner: hasan · Branch: `hasan/63-failure-triage`
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach

Two deliverables that look like one:

1. **Triage** — every failed step carries a `category` (FR-35). The contract for it is already
   on `main`: ADR `2026-11-15-failure-category` (omer, #240) put `category` in
   `schemas/agent-rpc.schema.json` 1.1 with five values, and the server and the report already
   read it. **Nothing fills it.** That is this issue.
2. **A decision log** — one JSONL line per failed step, with enough context to label later
   (criterion 2), feeding RQ5 and #86.

The triage rule lives in **one pure function** (`playback/triage.py`) rather than at each of the
twenty-odd `done(FAILED, …)` sites. A rule spread over twenty sites is a rule nobody can read,
and this one has to be read: it decides what the measurements mean.

### The mapping

| What happened | Category | Why |
|---|---|---|
| `NotFound` — nothing matched by the deadline | `elementNotFound` | TBD-5 |
| `Ambiguous` — more than one matched | `elementNotFound` | The ADR says so in as many words: no *unique* element matched, and it is deliberately not a sixth category |
| `NotReady` — it matched but never became visible and enabled | `timeout` | TBD-5's own wording |
| A snapshot or search that ran out of budget | `searchIncomplete` | TBD-5 |
| A `Verify` checkpoint that did not hold | `assertionFailed` | TBD-5 |
| A row checkpoint (`cell`, `rowExists`, `rowCount`) that did not hold | `assertionFailed` | It is a checkpoint; the row shape does not change what failed |
| The step's window was not the one in front | `unexpectedWindow` | TBD-5. **Playback cannot raise this today** — it is given a handle and never looks for a window — so the name is defined in `triage.py` and nothing produces it. The client sets it itself in #44 |

### The decision the ADR left to me

> "whether those two cases get a category of their own, or one of the five, is Hasan's call in
> #63. Until then, absent means 'not classified'."

The cases are wider than the two it names. **None of them is about the application:**

- a keyword this agent does not implement;
- a step document the agent refuses (no target, no value, a bad `timeoutMs`, a malformed
  checkpoint or row address);
- `Unsupported` — a property set playback cannot match on;
- `ActionFailed`, `SelectFailed`, `RowFailed`-by-refusal — the control is there and ready and
  the provider refused the action;
- `Unreadable` — a property the provider would not give up.

**My call: they stay out of the five, and `category` is absent for them.** Putting them in one
of the five would be the worst outcome available, because this field is not decoration — RQ2
and RQ5 are computed from it. A `timeout` that was really "this agent has no `SelectRow` yet"
is not a measurement of AYNA's recognition, it is a measurement of AYNA's unfinished state, and
once the two are mixed in one enum no later analysis can separate them.

**But absence is not good enough either**, and criterion 1 says *every* failed step gets a
category. So the **decision log carries a `reason` for every failed step**, finer than the five
and never absent, and the contract's `category` stays the coarse, cross-component field it was
designed as. The log is where labelling happens (criterion 2), so that is the right place for
the finer truth.

I am **proposing a sixth contract value** rather than taking one: see Open issues. I did not
want to bump a shared schema by myself while #248 already holds 1.2 and is in review.

## Decisions (small, local to this task)
- 2026-11-15 — one pure `triage.py`, not a `category=` at every `done(FAILED, …)` — the rule
  decides what RQ2 and RQ5 mean and has to be readable in one place.
- 2026-11-15 — the five stay as they are; everything the agent itself refused is `category`-less
  in the contract and carries a `reason` in the log.

## Status
- [x] Branch, task note, ADR and contract read
- [x] `playback/triage.py`: `category_for` (the contract's five, or `None`) and `reason_for`
      (finer, never `None`), with 29 tests
- [x] `category` filled at every failure site in `runner.py`. `done()` takes the **exception**
      and triages itself, so the rule stays in one module instead of twenty `except` branches;
      the two failures with no exception to pass name their reason instead.
- [x] `playback/decisions.py`: the JSONL log, 22 tests
- [x] `docs/agent-rpc.md`: `category` in the `runSteps` result, what absent means and why, the
      two boundaries worth stating, and a failed step in the example (the ADR asked me for this)
- [x] **689 agent tests pass**, ruff clean
- [ ] Commit, PR
- Next step: commit and open the PR, saying on it that implementing the ADR is my approval of it.

## What `RowFailed` and `SelectFailed` had to learn

Both collapsed two different findings into one exception: "the row/item is not there" and "it
is there and the application refused to select it". The first is recognition evidence and the
second is not, so each now carries a `kind` (`notFound` / `refused`) and triage reads it. That
is the kind of distinction that cannot be recovered later: once both are `elementNotFound` in a
stored result, no analysis can split them again.

## Open issues
- **A sixth value, proposed not taken.** The agent refuses steps for reasons that are nothing to
  do with the application, and FR-35 wants every failed step categorised. A sixth value —
  `notAttempted` is my suggestion — would say "this failure is not evidence about the
  application", which is strictly more useful than an absent field, because absent also means
  "a 1.0 agent wrote this". It is a minor version on two schemas plus the server's enum, so it
  needs omer, galip and an ADR. Raised on #63 and on the PR; until then, absent.
- **`unexpectedWindow` is unreachable from playback today.** `runSteps` takes a handle, so the
  agent never looks for a window and cannot find the wrong one in front. The client sets this
  category itself in #44 (`runner.ts`), which I approved on PR #247 for that reason. When the
  agent gains window finding (#61 gave the CLI its own; `docs/agent-rpc.md` promises the agent
  will), the category moves here and the client's copy should go.
- **The ADR is still Proposed and needs my approval and galip's.** Implementing it is my
  approval in substance; I will say so explicitly on the PR.

## Handoff

- **`triage.py` is the one place that decides, and it must stay that way.** `done()` in the
  runner takes the *exception* and triages itself, so a new failure path gets a category by
  passing `error=exc` and nothing else. Resist adding `category=` at a call site: the two that
  have one (an assertion that did not hold, a step the agent refuses) have no exception to pass
  and say so in a comment.
- **The hard rule, in one line:** a failure the **agent** caused never wears one of the five.
  `test_a_malformed_checkpoint_is_not_an_assertion_failure` is the guard; `CheckpointError`
  means "the checkpoint itself is wrong, whatever the application is doing", and filing that
  under `assertionFailed` would put a broken test in the application's column.
- **`test_the_five_are_exactly_the_contracts_five`** reads `schemas/agent-rpc.schema.json` and
  fails if the enum and the module drift apart — which is what will happen the day somebody
  adds the sixth value without telling playback.
- **The log never fails the run.** A full disk in the measurement harness must not cost the run
  it was measuring; `test_a_log_that_cannot_be_written_does_not_fail_the_run` holds that.
- **Nothing calls `run_steps(decisions=…)` yet.** The parameter is there and tested; wiring it
  up belongs to whoever owns a run — `UiaDesktop.run_steps` for the RPC path and the CLI runner
  (#61, PR #250) for CI, where the ≥50 examples (criterion 3) will actually come from. Kept out
  of this PR so the triage can be reviewed on its own.

## Outcome (fill when the issue closes)
