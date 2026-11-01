// `npm run dev:mock [-- --port 8099 --windows file.json --no-uia]`: the client with a stub
// server and a fake agent, for checking screens without the real server, Neo4j or Windows.
// Starts the stub server, waits until it listens, then runs `npm run dev` with the fake
// agent first on PYTHONPATH. Ctrl+C or closing the app stops everything.
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'
import { delimiter, dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'

const here = dirname(fileURLToPath(import.meta.url))
const python = process.platform === 'win32' ? 'python' : 'python3'

const { values } = parseArgs({
  options: {
    port: { type: 'string', default: '8099' },
    windows: { type: 'string', default: resolve(here, 'windows.json') },
    'no-uia': { type: 'boolean', default: false },
  },
})

function fail(message) {
  console.error(`dev:mock: ${message}`)
  process.exit(1)
}

/** Resolves once the stub prints its listening line; fails if it exits first. */
function startStub() {
  // stdin stays open: the stub exits on EOF, so it never outlives this script.
  const stub = spawn(python, [resolve(here, 'stub_server.py'), values.port], {
    stdio: ['pipe', 'pipe', 'inherit'],
  })
  return new Promise((done) => {
    stub.on('error', (error) =>
      fail(`cannot start ${python} (${error.message}); is Python 3 on PATH?`),
    )
    stub.on('exit', (code) => fail(`the stub server exited with code ${code}`))
    createInterface({ input: stub.stdout }).once('line', () => done(stub))
  })
}

const stub = await startStub()
stub.removeAllListeners('exit')
const url = `http://127.0.0.1:${values.port}`
console.log(`dev:mock: stub server on ${url}; enter this address in the app`)

const dev = spawn('npm', ['run', 'dev'], {
  stdio: 'inherit',
  // npm is npm.cmd on Windows, which only starts through a shell; the arguments are fixed.
  shell: process.platform === 'win32',
  env: {
    ...process.env,
    AYNA_AGENT_PYTHON: python,
    PYTHONPATH: [here, process.env.PYTHONPATH].filter(Boolean).join(delimiter),
    AYNA_MOCK_WINDOWS: resolve(values.windows),
    AYNA_MOCK_UIA: values['no-uia'] ? 'off' : 'on',
  },
})

// Ctrl+C reaches every process in the terminal's group; wait for the app to close.
process.on('SIGINT', () => {})
dev.on('exit', (code) => {
  stub.kill()
  process.exit(code ?? 0)
})
