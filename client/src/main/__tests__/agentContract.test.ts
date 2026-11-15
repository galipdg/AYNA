// The client's side of the agent JSON-RPC contract (`schemas/agent-rpc.schema.json`, #52):
// every request it sends matches the contract, and every result the contract allows is read.
// The agent's side is tested against the same file in `agent/tests/`.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import Ajv2020 from 'ajv/dist/2020.js'
import { parseListening, rpcRequest } from '../agent.ts'
import { perStepPlayer } from '../stepPlayer.ts'
import { listWindows, parseSnapshot, parseWindows, snapshot } from '../spy.ts'

const schemas = join(import.meta.dirname, '..', '..', '..', '..', 'schemas')
const read = (path: string): unknown => JSON.parse(readFileSync(join(schemas, path), 'utf8'))
const contract = read('agent-rpc.schema.json') as {
  $id: string
  $defs: { version: { const: string } }
}

const ajv = new Ajv2020({ allErrors: true, strict: false })
ajv.addSchema(contract as object)

/** A validator for one definition of the contract, e.g. `request` or `pingResult`. */
function matches(definition: string) {
  const validate = ajv.compile({ $ref: `${contract.$id}#/$defs/${definition}` })
  return (value: unknown): void => {
    assert.ok(
      validate(value),
      `${definition}: ${ajv.errorsText(validate.errors)} in ${JSON.stringify(value)}`,
    )
  }
}

/** Records the calls the Spy makes and frames them as `AgentManager.call` does. */
function recordingAgent(answer: unknown) {
  const sent: unknown[] = []
  return {
    sent,
    agent: {
      call: async (method: string, params?: Record<string, unknown>) => {
        sent.push(rpcRequest(sent.length + 1, method, params))
        return answer
      },
    },
  }
}

const window = {
  handle: 395942,
  title: 'AYNA Trial',
  className: 'LoginWindow',
  processId: 7316,
  processName: 'python.exe',
  bounds: [320, 180, 960, 660],
}

describe('agent JSON-RPC contract, client side', () => {
  it('is version 1.2', () => {
    assert.equal(contract.$defs.version.const, '1.2')
  })

  it('sends requests the contract allows', async () => {
    const request = matches('request')
    request(rpcRequest(1, 'ping'))

    const windows = recordingAgent({ windows: [] })
    await listWindows(windows.agent)
    const shot = recordingAgent(read('examples/snapshot/trial-login.json'))
    await snapshot(shot.agent, 657704)

    for (const sent of [...windows.sent, ...shot.sent]) request(sent)
    assert.deepEqual(shot.sent[0], {
      jsonrpc: '2.0',
      id: 1,
      method: 'snapshot',
      params: { handle: 657704 },
    })
  })

  it('sends a one-step runSteps the contract allows (#44)', async () => {
    const recorded = recordingAgent({ results: [{ stepIndex: 0, status: 'passed', durationMs: 31 }] })
    await perStepPlayer(recorded.agent).play({
      step: { id: 's1', keyword: 'Type', target: 'login.userNameInput', value: 'admin', timeoutMs: 2000 },
      stepIndex: 3,
      stepId: 's1',
      version: '0.2',
      handle: 657704,
      target: { properties: { automationId: 'usernameInput' }, fallback: { name: 'User name' } },
      runId: '7a3c2f4e-1b2d-4c5e-8f9a-0b1c2d3e4f5a',
      appVersionId: '9b8a7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d',
    })
    matches('request')(recorded.sent[0])
  })

  it('reads every window the contract allows, also with values Windows could not read', () => {
    const result = {
      windows: [
        window,
        { ...window, handle: 2, title: null, className: null, processId: null, processName: null },
        { ...window, handle: 3, bounds: [-1920, -8, -10, 1040] },
      ],
    }
    matches('listWindowsResult')(result)
    const parsed = parseWindows(result)
    assert.deepEqual(
      parsed?.map((w) => [w.handle, w.title, w.processId]),
      [
        [395942, 'AYNA Trial', 7316],
        [2, '', null],
        [3, 'AYNA Trial', 7316],
      ],
    )
  })

  it('reads the snapshot result', () => {
    const result = read('examples/snapshot/trial-login.json')
    matches('snapshotResult')(result)
    assert.ok(parseSnapshot(result))
  })

  it('reads the agent answers the contract documents', () => {
    matches('pingResult')({ agentVersion: '0.0.0', rpcVersion: '1.0' })
    matches('success')({ jsonrpc: '2.0', id: 3, result: { windows: [] } })
    matches('failure')({
      jsonrpc: '2.0',
      id: 4,
      error: { code: -32000, message: 'Window not found: 12' },
    })
    matches('failure')({
      jsonrpc: '2.0',
      id: null,
      error: { code: -32700, message: 'Parse error' },
    })
    // #22: one shape for every outcome, every field nullable (docs/agent-rpc.md).
    matches('elementFromPointResult')({
      handle: 657704,
      bounds: [614, 300, 814, 326],
      snapshotId: '5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b',
      elementId: 'e8',
      element: { automationId: 'QApplication.loginWindow.usernameInput', controlType: 'Edit' },
    })
    matches('elementFromPointResult')({
      handle: null,
      bounds: null,
      snapshotId: null,
      elementId: null,
      element: null,
    })
    matches('request')({
      jsonrpc: '2.0',
      id: 9,
      method: 'elementFromPoint',
      params: { x: -8, y: 40 },
    })
    matches('runStepsResult')({
      results: [
        {
          stepIndex: 0,
          status: 'passed',
          durationMs: 31,
          matched: 'primary',
          performedWith: 'SetValue',
        },
        {
          stepIndex: 1,
          status: 'failed',
          durationMs: 10000,
          stepId: 'b6f0',
          message: 'Element not found',
          category: 'elementNotFound',
        },
        { stepIndex: 2, status: 'notRun', durationMs: 0 },
      ],
    })
    const line = { event: 'listening', port: 53124 }
    matches('listening')(line)
    assert.equal(parseListening(JSON.stringify(line)), 53124)
  })

  it('keeps working with a later 1.x agent, which only adds', () => {
    matches('pingResult')({ agentVersion: '0.3.0', rpcVersion: '1.4' })
    const later = { windows: [{ ...window, monitor: 2 }] }
    assert.deepEqual(
      parseWindows(later)?.map((w) => w.handle),
      [395942],
    )
  })
})
