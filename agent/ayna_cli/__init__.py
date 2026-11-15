"""`ayna run` — plays a suite with a headless agent, for CI (#61, FR-23, UC-14).

The same playback the Electron client drives, with no Electron: `UiaDesktop` reads the window,
`playback.runner` plays the steps, and this package is only the three things around it —
**where the suite comes from** (a file or the server), **where the results go** (the server,
when one is given) and **what the process exits with**.

FR-23 fixes the exit codes, and the third is the one that is easy to get wrong:

- **0** — every test passed *and* every result was delivered;
- **1** — a test failed or proposed a repair;
- **2** — an operational failure (results not delivered, token refused, server unreachable),
  **even if every test passed**. A green suite whose results never reached the server is a 2:
  a CI job that called that success would be lying about the record.

Nothing here needs Windows except the playback it calls, so the suite reading, the exit-code
rules and the server client are all tested with fakes on any OS.
"""

from ayna_cli.exits import ALL_GOOD, OPERATIONAL_FAILURE, TEST_FAILED

__all__ = ["ALL_GOOD", "OPERATIONAL_FAILURE", "TEST_FAILED"]
