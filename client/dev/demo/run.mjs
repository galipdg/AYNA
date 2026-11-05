// `npm run demo [-- --server <url> --no-build --no-docker]`: everything for showing the client
// from one command. Starts the backend with Docker, adds the sample data through the API, then
// opens the client with the fake agent, already pointing at that server and application.
// Docker keeps running after the app closes, so the next start is quick.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'
import { defaultSnapshot, fakeAgentEnv } from '../mock/fake-agent-env.mjs'
import { seed } from './seed.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const client = resolve(here, '..', '..')
const root = resolve(client, '..')
const HEALTH_TIMEOUT_MS = 180_000
// npm is npm.cmd on Windows, which only starts through a shell; the arguments are fixed.
const npmShell = process.platform === 'win32'

const { values } = parseArgs({
  options: {
    server: { type: 'string', default: 'http://127.0.0.1:8080' },
    'no-build': { type: 'boolean', default: false },
    'no-docker': { type: 'boolean', default: false },
  },
})
const server = values.server.replace(/\/+$/, '')

function fail(message) {
  console.error(`demo: ${message}`)
  process.exit(1)
}

/** Like Docker Compose: the shell's value wins over the `.env` file. */
function setting(name) {
  if (process.env[name]) return process.env[name]
  const file = join(root, '.env')
  if (!existsSync(file)) return undefined
  const line = readFileSync(file, 'utf8')
    .split(/\r?\n/)
    .find((entry) => entry.startsWith(`${name}=`))
  return line?.slice(name.length + 1).trim()
}

function startBackend() {
  const docker = spawnSync('docker', ['info'], { stdio: 'ignore' })
  if (docker.error) fail('Docker is not installed, or `docker` is not on PATH.')
  if (docker.status !== 0) fail('Docker is not running. Start Docker Desktop and try again.')

  console.log('demo: starting the server and Neo4j with Docker…')
  const args = ['compose', 'up', '-d', ...(values['no-build'] ? [] : ['--build'])]
  const compose = spawnSync('docker', args, { cwd: root, stdio: 'inherit' })
  if (compose.status !== 0) {
    fail('`docker compose up` failed. If port 8080 is taken, stop what is using it.')
  }
}

async function waitForServer() {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${server}/api/health`, { signal: AbortSignal.timeout(2000) })
      if (response.ok && (await response.json()).db === 'UP') return
    } catch {
      // Not up yet.
    }
    await new Promise((done) => setTimeout(done, 1000))
  }
  fail(`no healthy server at ${server} after 3 minutes. See \`docker compose logs server\`.`)
}

async function logIn() {
  const username = setting('AYNA_ADMIN_USERNAME')
  const password = setting('AYNA_ADMIN_PASSWORD')
  if (!username || !password) {
    fail('set AYNA_ADMIN_USERNAME and AYNA_ADMIN_PASSWORD in the .env file (see .env.example).')
  }
  const response = await fetch(`${server}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (response.status === 401) {
    fail(
      `the server refused ${username}. The first admin is created only once, so this database ` +
        'may have another password. Use that one in .env.',
    )
  }
  if (!response.ok) fail(`login answered ${response.status}.`)
  return { username, token: (await response.json()).token }
}

/** A folder of its own, so the demo never touches the settings of a normal `npm run dev`. */
async function prepareUserData(applicationId) {
  const folder = join(tmpdir(), 'ayna-demo-client')
  await mkdir(folder, { recursive: true })
  const settings = { serverUrl: server, applicationId, language: 'tr' }
  await writeFile(join(folder, 'settings.json'), `${JSON.stringify(settings, null, 2)}\n`)
  return folder
}

function installPackages() {
  if (existsSync(join(client, 'node_modules', '.bin', 'electron-vite'))) return
  console.log('demo: installing the client packages…')
  const install = spawnSync('npm', ['ci'], { cwd: client, stdio: 'inherit', shell: npmShell })
  if (install.status !== 0) fail('`npm ci` failed.')
}

function openClient(userData) {
  const args = ['run', 'dev', '--', '--', `--user-data-dir=${userData}`]
  const dev = spawn('npm', args, {
    cwd: client,
    stdio: 'inherit',
    shell: npmShell,
    env: {
      ...process.env,
      ...fakeAgentEnv({ windows: join(here, 'windows.json'), snapshot: defaultSnapshot }),
    },
  })
  // Ctrl+C reaches every process in the terminal's group; wait for the app to close.
  process.on('SIGINT', () => {})
  dev.on('exit', (code) => {
    console.log('demo: closed. The server keeps running; `docker compose stop` stops it.')
    process.exit(code ?? 0)
  })
}

installPackages()
if (!values['no-docker']) startBackend()
await waitForServer()
const { username, token } = await logIn()
const app = await seed(server, token).catch((error) => fail(`sample data: ${error.message}`))
const userData = await prepareUserData(app.id)
console.log(`demo: ready. Log in as ${username} (password in .env), application "${app.name}".`)
openClient(userData)
