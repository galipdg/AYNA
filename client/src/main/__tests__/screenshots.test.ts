import assert from 'node:assert/strict'
import { mkdir, mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, it } from 'node:test'
import {
  AGENT_SCREENSHOT_ROOT,
  isAgentRunDir,
  ownRunDir,
  removeOwnRunDir,
  screenshotKeeper,
} from '../screenshots.ts'

const exists = (path: string) =>
  readFile(path).then(
    () => true,
    () => false,
  )

describe('step screenshots (#261)', () => {
  let dir: string
  let agentRun: string
  let own: string
  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'ayna-shots-'))
    agentRun = join(dir, AGENT_SCREENSHOT_ROOT, 'run-r1')
    own = join(dir, 'own')
    await mkdir(agentRun, { recursive: true })
  })
  afterEach(() => rm(dir, { recursive: true, force: true }))

  it("knows the agent's run folders and nothing else", () => {
    assert.equal(
      isAgentRunDir(join('C:', 'Temp', AGENT_SCREENSHOT_ROOT, 'run-20261115-140311-004812')),
      true,
    )
    assert.equal(isAgentRunDir(join('C:', 'Temp', AGENT_SCREENSHOT_ROOT, 'run-r1')), true)
    assert.equal(isAgentRunDir(join('C:', 'Temp', AGENT_SCREENSHOT_ROOT)), false)
    assert.equal(isAgentRunDir(join('C:', 'Users', 'you', 'Documents')), false)
    assert.equal(isAgentRunDir(join('C:', 'Temp', 'other', 'run-r1')), false)
  })

  it('keeps each step under its own name, so the agent reusing its file loses nothing', async () => {
    const keeper = screenshotKeeper(own, () => {})
    const agentPng = join(agentRun, 'step-0000.png')
    await writeFile(agentPng, 'first')
    const first = await keeper.keep('r1', 0, agentPng)
    await writeFile(agentPng, 'second')
    const second = await keeper.keep('r1', 1, agentPng)
    assert.equal(first, join(ownRunDir(own, 'r1'), 'step-0000.png'))
    assert.equal(await readFile(first!, 'utf8'), 'first')
    assert.equal(await readFile(second!, 'utf8'), 'second')
    assert.equal(await exists(agentPng), false, "the agent's file is taken away")
  })

  it('a missing image is no error: nothing kept', async () => {
    const lines: string[] = []
    const keeper = screenshotKeeper(own, (line) => lines.push(line))
    assert.equal(await keeper.keep('r1', 3, join(agentRun, 'step-0000.png')), null)
    assert.equal(lines.length, 1)
  })

  it('never touches a path outside the agent folder', async () => {
    const elsewhere = join(dir, 'Documents', 'secret.png')
    await mkdir(join(dir, 'Documents'))
    await writeFile(elsewhere, 'x')
    const keeper = screenshotKeeper(own, () => {})
    assert.equal(await keeper.keep('r1', 0, elsewhere), null)
    await keeper.release('r1')
    assert.equal(await exists(elsewhere), true)
  })

  it("release removes the run's agent folder; the client's copies stay until the outbox is done", async () => {
    const keeper = screenshotKeeper(own, () => {})
    await writeFile(join(agentRun, 'step-0000.png'), 'x')
    const kept = await keeper.keep('r1', 0, join(agentRun, 'step-0000.png'))
    await writeFile(join(agentRun, 'leftover.png'), 'y')
    await keeper.release('r1')
    assert.deepEqual(await readdir(join(dir, AGENT_SCREENSHOT_ROOT)), [])
    assert.equal(await exists(kept!), true)
    await removeOwnRunDir(own, 'r1')
    assert.equal(await exists(kept!), false)
    await removeOwnRunDir(own, 'r1') // twice is fine
  })
})
