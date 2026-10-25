# Technology stack

- Date: 2026-10-20
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
The team knows Python, JavaScript/React and Java/Spring Boot. Windows UI Automation is best reached from Python (pywinauto).

## Decision
Python for the automation agent and AI service, JavaScript (Electron + React) for the client, Java (Spring Boot) for the server, Neo4j as the database. No other languages in product code.

## Consequences
Three runtimes to package and test; contracts between them (schemas/, REST, JSON-RPC) must be explicit and frozen early (G1).
