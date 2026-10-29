// A stand-in for `python -m ayna_agent.rpc` that follows `docs/agent-rpc.md`: token in
// the environment, one `listening` line on stdout, a WebSocket on 127.0.0.1 that needs
// `Authorization: Bearer <token>`, and `ping`. Exits on stdin EOF, as the real agent will.
// FAKE_AGENT_MODE picks a misbehaviour for the tests. No dependencies: the WebSocket
// framing is the minimum RFC 6455 needs for small text frames.

import { createHash } from 'node:crypto'
import { createServer } from 'node:http'
import type { AddressInfo, Socket } from 'node:net'

type Mode =
  | 'ok'
  | 'exit' // dies at start, like a missing Python package
  | 'silent' // never prints its port
  | 'garbage' // prints something else on stdout
  | 'stop-answering' // answers the first ping only
  | 'ignore-stdin' // does not exit on EOF
  | 'slow-exit' // needs a moment to exit after EOF

const mode = (process.env.FAKE_AGENT_MODE ?? 'ok') as Mode
const token = process.env.AYNA_AGENT_TOKEN ?? ''

if (token.length < 16) process.exit(2)
if (process.argv.some((arg) => arg.includes(token))) process.exit(5)
if (mode === 'exit') {
  process.stderr.write('ModuleNotFoundError: No module named ayna_agent\n')
  process.exit(3)
}
if (mode !== 'ignore-stdin') {
  process.stdin.on('end', () => setTimeout(() => process.exit(0), mode === 'slow-exit' ? 300 : 0))
  process.stdin.resume()
}

function frame(opcode: number, payload: Buffer): Buffer {
  const length = payload.length
  const header =
    length < 126
      ? Buffer.from([0x80 | opcode, length])
      : Buffer.from([0x80 | opcode, 126, length >> 8, length & 0xff])
  return Buffer.concat([header, payload])
}

function send(socket: Socket, message: unknown) {
  socket.write(frame(0x1, Buffer.from(JSON.stringify(message))))
}

let pings = 0

function handle(socket: Socket, text: string) {
  const request = JSON.parse(text) as { id: number; method: string; params?: { ms?: number } }
  if (request.method === 'ping') {
    pings += 1
    if (mode === 'stop-answering' && pings > 1) return
    send(socket, {
      jsonrpc: '2.0',
      id: request.id,
      result: { agentVersion: '0.0.0', rpcVersion: '0.1' },
    })
  } else if (request.method === 'block') {
    // Like a long UI Automation call: the single agent thread answers nothing meanwhile.
    const end = Date.now() + (request.params?.ms ?? 0)
    while (Date.now() < end);
    send(socket, { jsonrpc: '2.0', id: request.id, result: {} })
  } else {
    send(socket, {
      jsonrpc: '2.0',
      id: request.id,
      error: { code: -32601, message: 'Method not found' },
    })
  }
}

const server = createServer()
server.on('upgrade', (request, socket: Socket) => {
  socket.on('error', () => {})
  if (request.headers.authorization !== `Bearer ${token}`) {
    socket.end('HTTP/1.1 401 Unauthorized\r\n\r\n')
    return
  }
  const accept = createHash('sha1')
    .update(`${request.headers['sec-websocket-key']}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`)
    .digest('base64')
  socket.write(
    'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n' +
      `Sec-WebSocket-Accept: ${accept}\r\n\r\n`,
  )
  let buffer = Buffer.alloc(0)
  socket.on('data', (chunk: Buffer) => {
    buffer = Buffer.concat([buffer, chunk])
    for (;;) {
      if (buffer.length < 2) return
      const opcode = buffer[0] & 0x0f
      let length = buffer[1] & 0x7f
      let offset = 2
      if (length === 126) {
        if (buffer.length < 4) return
        length = buffer.readUInt16BE(2)
        offset = 4
      }
      const mask = buffer.subarray(offset, offset + 4) // client frames are always masked
      offset += 4
      if (buffer.length < offset + length) return
      const payload = Buffer.from(buffer.subarray(offset, offset + length))
      for (let i = 0; i < payload.length; i++) payload[i] ^= mask[i % 4]
      buffer = buffer.subarray(offset + length)
      if (opcode === 0x8) return void socket.end(frame(0x8, Buffer.alloc(0)))
      if (opcode === 0x9) socket.write(frame(0xa, payload))
      if (opcode === 0x1) handle(socket, payload.toString('utf8'))
    }
  })
})

server.listen(0, '127.0.0.1', () => {
  if (mode === 'silent') return
  if (mode === 'garbage') return void process.stdout.write('Hello from Python\n')
  const { port } = server.address() as AddressInfo
  process.stdout.write(`${JSON.stringify({ event: 'listening', port })}\n`)
})
