# Technology stack

- Date: 2026-10-20
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
The team knows Python, JavaScript/React and Java/Spring Boot. Windows UI Automation is best reached from Python (pywinauto).

## Decision
Python for the automation agent and AI service, JavaScript (Electron + React) for the client, Java (Spring Boot) for the server, Neo4j as the database. No other languages in product code.

## Amendment (2026-10-25)
The client is written in TypeScript instead of JavaScript (still Electron + React). Agreed by Galip, Ömerfaruk and Hasan in person while the client was still a skeleton (#5); the team chose to amend this ADR instead of writing a new one.

## Consequences
Three runtimes to package and test; contracts between them (schemas/, REST, JSON-RPC) must be explicit and frozen early (G1).
