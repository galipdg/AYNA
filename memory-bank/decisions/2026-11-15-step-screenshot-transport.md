# A step's screenshot travels as a path, and agent JSON-RPC goes to 1.2

- Date: 2026-11-15
- Status: Accepted 2026-11-19 (#54, PR #248). Hasan proposed; Ömerfaruk approved the schema change in his #248 review (2026-11-15); Galip approved on 2026-11-19 and raised `RPC_VERSION` to 1.2 in the same change (branch `galip/inbox-2026-11-19`).
- Deciders: Hasan (playback, agent screenshot), Ömerfaruk (client, server upload, report), Galip (agent RPC)
- Issue: #54 (FR-19, NFR-03). Depends on #40 (closed) and #52 (closed).
- Extends: ADR *Contracts v1* (`2026-11-08`), ADR *Run screenshots, idle timeout and retention* (`2026-11-08`, #51). Does not change the server side of #51.

## Context

- FR-19: after each step the agent captures a PNG of the AUT's window, cropped to that window,
  and returns it with the step result. NFR-03 gives the whole capture 300 ms per step.
- #51 already settled the **server** side: `PUT /api/runs/{runId}/results/{stepIndex}/screenshot`
  with raw `image/png`, after the step's result was accepted, at most 8 MB. What it deliberately
  left open was how the bytes get from the agent to whoever uploads them;
  `docs/agent-rpc.md` says in as many words that "the image itself travels as #54 and #51 decide".
- Sizes are the whole argument. A 50-step run is about **15 MB** of PNG
  (`client/src/main/runs.ts`), and the agent → client link is the same WebSocket that carries
  live step status.
- The agent and the client always share a machine: the client spawns the agent as a child
  process (`docs/agent-rpc.md`, "Starting the agent"). The CLI runner (#61) hosts the agent
  in-process, so it shares a machine with it too.
- `schemas/agent-rpc.schema.json` is frozen at v1 and `stepResult` has
  `additionalProperties: false`, so a new field is not merely undocumented — it is **forbidden**.

## Options considered

**1. How the image reaches the client**
- a. *A path in the step result.* The agent writes the PNG and returns `screenshotPath`.
  \+ The notification stays a few hundred bytes. + The reader chooses when to pay for the bytes.
  \+ The upload is a file read, which is what `PUT …/screenshot` wants anyway.
  − Only works when the reader shares a filesystem with the agent (true today, and for #61).
  − Someone must delete the files.
- b. *Base64 in the step result.* + One message, nothing to clean up, no filesystem assumption.
  − About 20 MB of JSON for a 50-step run, a third more than the bytes themselves, through the
  socket that also carries live status. − Every repeat or retry of a result carries it again.
- c. *A second JSON-RPC method, `getScreenshot(stepIndex)`.* + Keeps the result small and needs no
  shared filesystem. − A new method on a frozen contract, and the agent must hold the images until
  someone asks, which is state with no owner.

**2. Who deletes the files**
- a. *Whoever owns the run* — the client, after its uploads; nothing in the agent.
  \+ The agent cannot know when the upload finished, so it cannot be the one to decide.
  \+ The client already removes report files for the same reason (`client/src/main/index.ts`).
  − A client that crashes mid-run leaves a directory behind.
- b. *The agent deletes after N minutes.* − It would delete images the client has not uploaded yet.

**3. The contract version**
- a. *Minor bump to 1.2, two optional fields.* + Exactly what ADR *Contracts v1* calls an addition:
  a reader that does not know them ignores them. − None.
- b. *Leave the schema alone and send the fields anyway.* − They are forbidden by
  `additionalProperties: false`; every real `runSteps` answer would be outside the contract.

## Decision

**1a, 2a, 3a.**

- The step result carries **`screenshotPath`** (absolute, on the agent's machine) and
  **`screenshotAt`** (ISO 8601 with offset, to the millisecond). The bytes never travel in the
  message.
- `schemas/agent-rpc.schema.json` `$defs/version` goes **1.1 → 1.2** and `stepResult` gains the two
  optional fields. `RPC_VERSION` in `rpc.py` is Galip's to raise to `1.2` when he is ready; the
  schema is allowed to lead (`test_rpc_version_is_within_the_schemas_version`).
- **Absent means there is no image, and that is normal, not an error.** A `notRun` step is never
  photographed, and a capture that fails is logged and skipped rather than failing the step —
  the commonest reason a step fails is that the window is not what the test expected, including
  gone, and the screenshot of that step is the one worth having. #59's report and the client's
  step list must treat a missing screenshot as ordinary.
- The agent writes one directory per run under the system temporary directory. **Cleanup belongs
  to whoever owns the run**, not to the agent.
- `screenshotAt` is to the millisecond, unlike the snapshot's `startedAt` (seconds): steps are
  faster than a second, and the question the approval screen asks is how much older the image is
  than the geometry.

## Consequences

- The client (#51's client half, #44) reads the file at `screenshotPath` and PUTs the bytes. It
  must also delete the run's files afterwards. Ömerfaruk has taken both.
- **A caller that sends one step per `runSteps` call gets one directory per step**, because the
  agent starts a new run directory per call and the agent sees `stepIndex: 0` every time. #44's
  client does exactly that, so the cleanup cannot assume a single folder per run until the agent
  keys the directory on `runId` — which the client already sends and the agent currently ignores.
  Tracked on #248; it needs one line in `rpc.py` (Galip's).
- A future caller that does **not** share a filesystem with the agent — a remote agent, which
  nothing in AYNA plans — would need option 1b or 1c. That would be a new minor version, not a
  change to this one.
- No Pillow: the capture uses `pywin32` (already present through pywinauto) and the PNG is written
  with `zlib` and `struct`, so the agent's dependency list is unchanged from the #52 freeze. This
  is an implementation choice rather than a contract one, recorded here because it is the reason
  the encoder is ours to maintain.

## Measurements behind NFR-03

On the project's Windows machine at 125 % scaling, end to end (capture, crop, encode):

| | |
|---|---|
| Sample app, 902x564 | 41 ms |
| A 1920x1020 window | 91–96 ms |
| Encoder alone, 1920x1080, app-shaped frame | 29 ms, 30 KiB |
| Encoder alone, 1920x1080, random noise | 226–295 ms, 6 MB |

NFR-03's 300 ms is met with room for the windows AYNA tests. The only case with no margin is
content that is genuinely incompressible (a photo, a video surface); it is recorded as a
measurement in `agent/tests/test_screenshot.py`, not defended as a promise.
