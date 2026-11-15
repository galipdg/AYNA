# Test data

- **`junit-10.xsd`** — the Apache Ant / JUnitReport XML schema, used by
  `tests/test_cli_junit.py` to validate what `ayna run --junit` writes (#66, criterion 1).
  Copyright © 2011 Windy Road Technology Pty. Limited, distributed under the Apache License
  2.0 (the notice is in the file's own `xs:annotation`). Vendored rather than fetched, because
  nothing in this project may reach the network — including its tests.
- **`trial-app-tree.json`** — the trial app's real UIA tree (#11), used by the playback tests.
