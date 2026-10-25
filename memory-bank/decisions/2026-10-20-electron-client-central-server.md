# Electron client per test machine, one central server

- Date: 2026-10-20
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
The Object Spy must run on the same machine as the application under test (overlay highlight, global hotkey). Many engineers must share one repository without licence limits.

## Decision
Each test machine runs the Electron client, which starts and supervises a local Python agent (JSON-RPC over localhost WebSocket). Projects, tests and the repository live on one central Spring Boot server + Neo4j.

## Consequences
Packaging: electron-builder + PyInstaller agent. Two network boundaries (client↔server, client↔agent) with versioned contracts.
