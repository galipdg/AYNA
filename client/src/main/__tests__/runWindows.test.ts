import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { AgentNotConnectedError } from '../agent.ts'
import { findWindow, windowTitleOf, type Clock } from '../runWindows.ts'

const win = (handle: number, title: string) => ({
  handle,
  title,
  className: 'QWidget',
  processId: 1,
  processName: 'trial.exe',
  bounds: [0, 0, 100, 100],
})

/** An agent whose `listWindows` answers the next list each time; the last one repeats. */
function agentListing(...lists: ReturnType<typeof win>[][]) {
  let calls = 0
  return {
    get calls() {
      return calls
    },
    async call(method: string) {
      assert.equal(method, 'listWindows')
      const windows = lists[Math.min(calls, lists.length - 1)]
      calls++
      return { windows }
    },
  }
}

/** A clock that moves only when slept on. */
function fakeClock() {
  const slept: number[] = []
  let now = 0
  const clock: Clock = {
    now: () => now,
    sleep: async (ms) => {
      slept.push(ms)
      now += ms
    },
  }
  return { clock, slept }
}

const LOGIN = 'AYNA Trial - Login'

describe('finding a step window', () => {
  it('takes the one window with the title', async () => {
    const agent = agentListing([win(1, `${LOGIN} (2)`), win(7, LOGIN), win(9, 'Notepad')])
    const { clock } = fakeClock()
    assert.deepEqual(await findWindow(agent, LOGIN, 1000, clock), { handle: 7 })
  })

  it('waits for a window that opens late', async () => {
    const agent = agentListing([], [], [win(3, LOGIN)])
    const { clock, slept } = fakeClock()
    assert.deepEqual(await findWindow(agent, LOGIN, 10_000, clock), { handle: 3 })
    assert.deepEqual(slept, [250, 250])
  })

  it("gives up after the step's time", async () => {
    const agent = agentListing([win(1, 'Notepad')])
    const { clock } = fakeClock()
    assert.deepEqual(await findWindow(agent, LOGIN, 1000, clock), { none: true })
    assert.equal(agent.calls, 5) // at 0, 250, 500, 750 and 1000 ms
  })

  it('returns every window when two match', async () => {
    const agent = agentListing([win(1, LOGIN), win(2, LOGIN)])
    const { clock } = fakeClock()
    const found = await findWindow(agent, LOGIN, 1000, clock)
    assert.ok('many' in found)
    assert.equal(found.many.length, 2)
    assert.equal(agent.calls, 1)
  })

  it('stops polling when stopped', async () => {
    const agent = agentListing([])
    const { clock } = fakeClock()
    assert.deepEqual(await findWindow(agent, LOGIN, 10_000, clock, () => true), { none: true })
    assert.equal(agent.calls, 1)
  })

  it('fails at once when the agent is gone', async () => {
    const agent = {
      async call(): Promise<unknown> {
        throw new AgentNotConnectedError()
      },
    }
    const { clock, slept } = fakeClock()
    const found = await findWindow(agent, LOGIN, 10_000, clock)
    assert.ok('failed' in found)
    assert.deepEqual(slept, [])
  })

  it('windowTitleOf prefers primary, then fallback, then the capture', () => {
    const t = (title?: string) => (title === undefined ? {} : { windowTitle: title })
    assert.equal(windowTitleOf({ primary: t('A'), fallback: t('B') }, t('C')), 'A')
    assert.equal(windowTitleOf({ primary: t(), fallback: t('B') }, t('C')), 'B')
    assert.equal(windowTitleOf({ primary: t(), fallback: t() }, t('C')), 'C')
    assert.equal(windowTitleOf({ primary: t(''), fallback: t() }, t('')), null)
    assert.equal(windowTitleOf({ primary: {}, fallback: {} }), null)
  })
})
