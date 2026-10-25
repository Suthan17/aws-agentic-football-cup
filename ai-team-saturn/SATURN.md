# Saturn Flotillas — our own team (built the AWS way)

Created exactly as the sample README's "Creating Your Own Agent" section describes: a copy of
`ai-team-strands-balanced`, deployed as its own AgentCore project (`TeamSaturn`), so it gets its own
5 runtimes and ARNs. The original balanced squad stays deployed and untouched — switching squads in
the Player Portal is just pasting the other set of ARNs (instant A/B, instant rollback).

## What differs from ai-team-strands-balanced
| Area | Change |
|---|---|
| `agentcore/agentcore.json` | project name `TeamSaturn` (new stack `AgentCore-TeamSaturn-default`) |
| shared `lib/state.py` | coach chat: our team's latest 3 `teamChat` messages + the player's portal name in the state summary |
| `ai-*/src/main.py` | unchanged from balanced (same prompts, model, fallback) |

Future strategy changes follow the AWS format: edit only an agent's `SYSTEM_PROMPT`
(identity → optional capability block → `## Your Role` → commands → field → response).

## Deploy
```powershell
powershell -File C:\dev\tools\release.ps1 -Team ai-team-saturn
```
The release gate runs every test first and refuses to deploy on any failure or uncommitted change.

Player names used by coach chat (must match the portal's My Team page): IKER, PIYOL, BUSQETS, NANI, SIUUU.

> **Note for this repository:** `lib/` here is the squad C version. Squad A ran during the event with `lib/` *without* the possession fix and the keeper-out fact (coach chat only).
