# agent/

Python automation agent and headless CLI runner. The agent reads Windows UI Automation trees through pywinauto, serves the Object Spy, plays back test steps and proposes self-healing candidates. It talks to the Electron client over a localhost JSON-RPC connection.

- `ayna_agent/` — recognition, healing, playback and the RPC server
- `ayna_cli/` — headless runner that writes JUnit XML

Owners: galip (recognition, heal, RPC) · hasan (playback, CLI). Build, test and agent rules: [AGENTS.md](AGENTS.md).
