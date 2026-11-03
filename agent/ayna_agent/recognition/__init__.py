"""Reading the UI: element descriptors, window snapshots and the Spy backend (hasan).

`snapshot` is free of UI Automation and runs on any OS: it turns raw nodes into the snapshot
document of `schemas/snapshot.schema.json` (#12). The UIA reading that produces those nodes
lives next to it and only runs on Windows.
"""
