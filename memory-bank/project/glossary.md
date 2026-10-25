# Glossary

| Term | Meaning |
|---|---|
| AUT | Application under test |
| UIA | Microsoft UI Automation, the accessibility tree AYNA reads through pywinauto's `uia` backend |
| Element | One node of a UIA snapshot of a specific app version |
| Descriptor | The multi-property description of an element (AutomationId, Name, ControlType, ClassName, parent path, nearest label, bounds…) |
| Snapshot | A captured window subtree of one app version, stored as Window/Element nodes |
| RepoObject | Entry in the object repository: a stable logical name with primary + fallback properties, resolved to an Element per app version |
| Object Spy | Client screen that inspects elements on screen and adds them to the repository |
| Step / keyword | One action in a test: Click, Type, Select, Verify, Wait (see `schemas/step.schema.json`) |
| Checkpoint | A Verify step comparing an element property with an expected value |
| Smart wait | Waiting until the element exists, is visible and enabled, instead of a fixed sleep |
| Healing proposal | Ranked replacement candidates for a RepoObject that no longer resolves, with per-property score contributions; applied only after approval |
| Rule / rule book | A deterministic rule created from an approved decision, so the same situation never needs a model again |
| Triage | Classifying a failed step: element not found, unexpected window, assertion failed, timeout |
| Change impact | The tests affected by the elements that changed between two app versions |
| Gate (G0–G4) | Milestone check that must pass before the next phase starts |
| RS / SDD | Requirements Specification / Software Design Document (course deliverables) |
| Held-out split | The 30 NL/step pairs frozen before any prompt tuning, used only for RQ3 |
