import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, it } from 'node:test'
import type { WriteAnswer } from '../runs.ts'
import { Outbox, type OutboxEntry, type OutboxSender } from '../outbox.ts'
import type { Clock } from '../runWindows.ts'

const SERVER = 'http://server'

const result = (runId: string, stepIndex: number, serverUrl = SERVER): OutboxEntry => ({
  kind: 'result',
  serverUrl,
  runId,
  stepIndex,
  body: { runId, stepIndex, status: 'passed' },
})
const shot = (runId: string, stepIndex: number): OutboxEntry => ({
  kind: 'screenshot',
  serverUrl: SERVER,
  runId,
  stepIndex,
  path: `/own/${runId}/step-${stepIndex}.png`,
})
const finish = (runId: string): OutboxEntry => ({
  kind: 'finish',
  serverUrl: SERVER,
  runId,
  status: 'passed',
})

/** A sender that answers from `answers` in turn (then `stored`), recording what it was sent. */
function sender(answers: (WriteAnswer | 'hang')[] = [], serverUrl: string | null = SERVER) {
  const sent: OutboxEntry[] = []
  const s: OutboxSender & { sent: OutboxEntry[] } = {
    sent,
    serverUrl: () => serverUrl,
    put: (entry) => {
      sent.push(entry)
      const answer = answers.shift() ?? 'stored'
      return answer === 'hang' ? new Promise<WriteAnswer>(() => {}) : Promise.resolve(answer)
    },
  }
  return s
}

function fakeClock() {
  const slept: number[] = []
  const clock: Clock = { now: () => 0, sleep: async (ms) => void slept.push(ms) }
  return { clock, slept }
}

const quiet = () => {}

describe('the run outbox', () => {
  let dir: string
  let file: string
  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'ayna-outbox-'))
    file = join(dir, 'run-outbox.json')
  })
  afterEach(() => rm(dir, { recursive: true, force: true }))

  const onDisk = async () => JSON.parse(await readFile(file, 'utf8'))

  it('delivers in order and empties the file', async () => {
    const s = sender()
    const outbox = await Outbox.open(file, s, fakeClock().clock, quiet)
    await outbox.add(result('A', 0))
    await outbox.add(result('A', 1))
    await outbox.add(finish('A'))
    await outbox.idle()
    assert.deepEqual(
      s.sent.map((e) => (e.kind === 'result' ? e.stepIndex : 'finish')),
      [0, 1, 'finish'],
    )
    await outbox.close()
    assert.deepEqual((await onDisk()).entries, [])
  })

  it('writes an entry to disk before add returns', async () => {
    const outbox = await Outbox.open(file, sender(['hang']), fakeClock().clock, quiet)
    await outbox.add(result('A', 0))
    assert.equal((await onDisk()).entries.length, 1)
    await outbox.close()
  })

  it('retries with growing waits', async () => {
    const s = sender(['retry', 'retry', 'stored', 'retry'])
    const { clock, slept } = fakeClock()
    const outbox = await Outbox.open(file, s, clock, quiet)
    await outbox.add(result('A', 0))
    await outbox.idle()
    assert.deepEqual(slept, [1000, 2000])
    await outbox.add(result('A', 1))
    await outbox.idle()
    assert.deepEqual(slept, [1000, 2000, 1000], 'the wait starts over after a success')
    await outbox.close()
  })

  it('never waits longer than 30 s', async () => {
    const s = sender(Array(8).fill('retry'))
    const { clock, slept } = fakeClock()
    const outbox = await Outbox.open(file, s, clock, quiet)
    await outbox.add(result('A', 0))
    await outbox.idle()
    assert.deepEqual(slept, [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000])
    await outbox.close()
  })

  it('keeps entries on 401 until resumed', async () => {
    const s = sender(['unauthorized'])
    const outbox = await Outbox.open(file, s, fakeClock().clock, quiet)
    await outbox.add(result('A', 0))
    await outbox.idle()
    await outbox.add(result('A', 1))
    await outbox.idle()
    assert.equal(s.sent.length, 1)
    outbox.resume()
    await outbox.idle()
    assert.deepEqual(
      s.sent.map((e) => (e.kind === 'result' ? e.stepIndex : 'finish')),
      [0, 0, 1],
    )
    await outbox.close()
  })

  it('sets a run aside on 404', async () => {
    const s = sender(['gone'])
    const outbox = await Outbox.open(file, s, fakeClock().clock, quiet)
    const setAside: string[] = []
    outbox.onSetAside((runId) => setAside.push(runId))
    await outbox.add(result('A', 0))
    await outbox.idle()
    await outbox.add(result('A', 1))
    await outbox.add(finish('A'))
    await outbox.add(result('B', 0))
    await outbox.idle()
    assert.deepEqual(setAside, ['A'])
    assert.deepEqual(
      s.sent.map((e) => `${e.runId}${e.kind === 'result' ? e.stepIndex : 'f'}`),
      ['A0', 'B0'],
      "a set-aside run's later entries are not sent",
    )
    await outbox.close()
    const disk = await onDisk()
    assert.equal(disk.entries.length, 0)
    assert.deepEqual(
      disk.setAside.map((e: OutboxEntry & { answer: string }) => [e.runId, e.answer]),
      [
        ['A', 'gone'],
        ['A', 'gone'],
        ['A', 'gone'],
      ],
    )
  })

  it('survives a restart', async () => {
    const first = await Outbox.open(file, sender(['hang']), fakeClock().clock, quiet)
    await first.add(result('A', 0))
    await first.add(result('A', 1))
    await first.close()
    const s = sender()
    const second = await Outbox.open(file, s, fakeClock().clock, quiet)
    await second.idle()
    assert.deepEqual(
      s.sent.map((e) => (e.kind === 'result' ? e.stepIndex : 'finish')),
      [0, 1],
    )
    await second.close()
  })

  it("skips another server's entries and lists unfinished runs", async () => {
    const first = await Outbox.open(file, sender(['hang']), fakeClock().clock, quiet)
    await first.opened(SERVER, 'A')
    await first.opened('http://other', 'X')
    await first.opened(SERVER, 'B')
    await first.add(result('A', 0))
    await first.add(result('X', 0, 'http://other'))
    await first.add(result('B', 0))
    await first.add(finish('B'))
    assert.deepEqual(first.unfinishedRuns(SERVER), ['A'])
    assert.deepEqual(first.unfinishedRuns('http://other'), ['X'])
    await first.close()
    const s = sender()
    const second = await Outbox.open(file, s, fakeClock().clock, quiet)
    await second.idle()
    assert.deepEqual(
      s.sent.map((e) => e.runId),
      ['A', 'B', 'B'],
    )
    await second.close()
    assert.deepEqual(
      (await onDisk()).entries.map((e: OutboxEntry) => e.runId),
      ['X'],
    )
  })

  it('starts empty from an unreadable file and keeps it aside', async () => {
    await writeFile(file, '{ not json', 'utf8')
    const lines: string[] = []
    const outbox = await Outbox.open(file, sender(), fakeClock().clock, (line) => lines.push(line))
    assert.deepEqual(outbox.unfinishedRuns(SERVER), [])
    assert.equal(await readFile(`${file}.bad`, 'utf8'), '{ not json')
    assert.equal(lines.length, 1)
    await outbox.close()
  })

  it('remembers an opened run whose results were all delivered, across a restart', async () => {
    const first = await Outbox.open(file, sender(), fakeClock().clock, quiet)
    await first.opened(SERVER, 'A')
    await first.add(result('A', 0))
    await first.idle()
    await first.close()
    assert.deepEqual((await onDisk()).entries, [])
    const second = await Outbox.open(file, sender(), fakeClock().clock, quiet)
    assert.deepEqual(second.unfinishedRuns(SERVER), ['A'])
    await second.add(finish('A'))
    assert.deepEqual(second.unfinishedRuns(SERVER), [])
    await second.close()
  })

  it('reads an outbox file written before runs were marked open', async () => {
    await writeFile(file, JSON.stringify({ entries: [result('A', 0)], setAside: [] }), 'utf8')
    const outbox = await Outbox.open(file, sender(['hang']), fakeClock().clock, quiet)
    assert.deepEqual(outbox.unfinishedRuns(SERVER), [])
    await outbox.close()
  })
})

describe('the run outbox with screenshots (#261)', () => {
  let dir: string
  let file: string
  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'ayna-outbox-'))
    file = join(dir, 'run-outbox.json')
  })
  afterEach(() => rm(dir, { recursive: true, force: true }))

  /** `sender` that also records each entry it is told is done with. */
  function releasing(answers: (WriteAnswer | 'hang')[] = []) {
    const done: string[] = []
    const s: OutboxSender & { sent: OutboxEntry[] } = {
      ...sender(answers),
      released: async (entry) => {
        done.push(
          entry.kind === 'finish' ? `finish:${entry.runId}` : `${entry.kind}:${entry.stepIndex}`,
        )
      },
    }
    return { s, done }
  }

  it('sends a screenshot after its result and releases each entry once delivered', async () => {
    const { s, done } = releasing()
    const outbox = await Outbox.open(file, s, fakeClock().clock, quiet)
    await outbox.add(result('A', 0))
    await outbox.add(shot('A', 0))
    await outbox.add(finish('A'))
    await outbox.idle()
    assert.deepEqual(
      s.sent.map((e) => e.kind),
      ['result', 'screenshot', 'finish'],
    )
    assert.deepEqual(done, ['result:0', 'screenshot:0', 'finish:A'])
    await outbox.close()
  })

  it('drops only the image the server refuses; the run goes on', async () => {
    const lines: string[] = []
    const { s, done } = releasing(['stored', 'conflict'])
    const outbox = await Outbox.open(file, s, fakeClock().clock, (line) => lines.push(line))
    await outbox.add(result('A', 0))
    await outbox.add(shot('A', 0))
    await outbox.add(result('A', 1))
    await outbox.add(finish('A'))
    await outbox.idle()
    assert.deepEqual(
      s.sent.map((e) => e.kind),
      ['result', 'screenshot', 'result', 'finish'],
    )
    assert.deepEqual(done, ['result:0', 'screenshot:0', 'result:1', 'finish:A'])
    await outbox.close()
    assert.deepEqual(JSON.parse(await readFile(file, 'utf8')).setAside, [])
    assert.match(lines.join('\n'), /refused the screenshot of step 0 of run A/)
  })

  it('releases every entry of a run the server set aside, the finish included', async () => {
    const { s, done } = releasing(['hang'])
    const outbox = await Outbox.open(file, s, fakeClock().clock, quiet)
    await outbox.add(result('A', 0)) // hangs, so the rest stays queued
    await outbox.close()
    const { s: s2, done: done2 } = releasing(['gone'])
    const again = await Outbox.open(file, s2, fakeClock().clock, quiet)
    await again.idle() // the queued result comes back 404: run A is set aside
    await again.add(shot('A', 0))
    await again.idle()
    await again.add(finish('A'))
    await again.idle()
    assert.deepEqual(done, [])
    assert.deepEqual(done2, ['result:0', 'screenshot:0', 'finish:A'])
    await again.close()
  })

  it('a failing cleanup never stops the queue', async () => {
    const s: OutboxSender & { sent: OutboxEntry[] } = {
      ...sender(),
      released: async () => {
        throw new Error('EBUSY')
      },
    }
    const outbox = await Outbox.open(file, s, fakeClock().clock, quiet)
    await outbox.add(shot('A', 0))
    await outbox.add(finish('A'))
    await outbox.idle()
    assert.equal(s.sent.length, 2)
    await outbox.close()
  })
})
