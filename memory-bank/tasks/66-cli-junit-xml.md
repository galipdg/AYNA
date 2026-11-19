# #66 CLI writes JUnit XML

- Issue: https://github.com/galipdg/AYNA/issues/66
- Owner: hasan · Branch: `hasan/66-junit-xml`
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach

`ayna run --junit out.xml`. The CLI (#61, PR #250) already keeps reporting behind its own seam,
so this adds `ayna_cli/junit.py` and one option.

### Validating against the real schema changed the design

Criterion 1 is "XML validates against the JUnit schema", so I fetched one (`agent/tests/data/
junit-10.xsd` — the Apache Ant / JUnitReport schema, Apache-2.0, vendored with its notice) and
validate in a test with `xmlschema` as a **dev-only** dependency. The product never imports it.

That was not a formality. **The shape the project has been producing since #249 does not
validate**, in four separate ways, and nothing would have told us:

| What `run_suite.py` wrote | Why the schema refuses it |
|---|---|
| `<testsuites>` root with a nested `<testsuite>` | a nested suite additionally requires `package` and `id` |
| no `<properties>` | required, first in the sequence, even when empty |
| `<system-out>` inside `<testcase>` | both `system-out` and `system-err` belong to the **suite**, and both are required |
| no `timestamp`, no `hostname` | both required on `testsuite` |

So #66 emits a single root `<testsuite>` with the sequence the schema demands —
`<properties>`, `<testcase>`*, `<system-out>`, `<system-err>` — and all seven required
attributes.

### Two decisions worth stating

- **The timestamp carries no timezone**, against this project's convention everywhere else.
  The schema's own type says "Timezone may not be specified" and restricts the pattern to
  `YYYY-MM-DDThh:mm:ss`. Rather than lose the information, the offset-carrying stamp goes in
  `<properties>` as `startedAt`, so a reader has both.
- **A delivery failure goes in `<system-err>`.** A run whose tests all passed but whose results
  never reached the server exits **2** (FR-23), and a reporter showing all-green beside a red
  job is the confusing outcome. The XML reports *tests*, so the outcomes stay honest, and the
  reason the job failed anyway is written where a reader looks for it.

## Status
- [x] Branch, task note, schema fetched and read
- [x] `ayna_cli/junit.py` + `--junit OUT.XML`
- [x] 26 tests, of which **8 validate a whole document against the real XSD** — every shape the
      module can produce: all passed, a failure, an error, every kind at once, undelivered
      only, a run-level error, no tests at all, and no scenario ids
- [x] **Run for real** against the live sample app on `--bug bug1`: exit 1, and the file it
      wrote **validates against the schema**
- [x] 782 agent tests pass under CI's own invocation (`.venv/Scripts/pytest.exe`), ruff clean
- [x] Commit, **PR #254** open as *Part of #66*
- [ ] **CI has not run**: every job on this branch failed to start with "recent account
      payments have failed or your spending limit needs to be increased". Account-level and
      repo-wide -- my 18:13Z run on #64 passed and the 18:35Z run here never started. Only the
      repository owner can clear it; said so on the PR and in galip's inbox.
- Next step: nothing of mine. Re-run the checks once billing is clear, and ask omer which way
  he wants criterion 2 (a reporter action, or the XML into the job summary).

## The claim about the old format, checked rather than asserted

I validated a JUnit file the **stand-in actually produced** (kept from my #249 review) against
the same schema. It does not validate; the first complaint is `'name' attribute not allowed for
element`, because `<testsuites>` takes no `name`. So the four problems in the table above are
real and were shipping.

## Open issues
- **Criterion 2 ("GitHub Actions test reporter displays it") is partly omer's.** `.github/` is
  his, and #249 deliberately added no third-party reporter action ("that would be a new
  dependency"). Without one, GitHub shows an artifact rather than a test report. Options are
  his call: a reporter action, or parsing the XML into the job summary, which is what
  `ci_suite.py` already does with the text output. Raised on the issue and on #252.
- **#252 is on the way out of the text parsing.** It reads the CLI's `pass  NAME` / `FAIL  NAME`
  lines and says so; once this merges, it can read the XML and drop the `_say` import. Said so
  in my #252 review.

## Handoff
Nothing yet beyond this note.

## Outcome (fill when the issue closes)
