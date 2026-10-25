# Saturn Flotillas — Evidence log

## Match: v1.1 vs Fort Knox Athletic — 1-0 win (2026-10-22, after 13:20 UTC deploy)

### Verified from CloudWatch (our own agent logs)
| Player | Decisions | What it did |
|---|---|---|
| Iker GK | 65 rule / 0 LLM | MOVE_TO 47, INTERCEPT 11, GK_DISTRIBUTE 8 |
| Piyol DEF | 64 LLM | MARK 31, PRESS 16, PASS 12, MOVE 5 |
| Busqets MID | 65 LLM | MOVE 50, PASS 13, PRESS 2 |
| Nani FWD1 | 57 LLM + 4 rule | MOVE 58, PRESS 2, PASS 1 — 3 SHOOTs blocked by guard |
| Siuuu FWD2 | 59 LLM + 8 rule | MOVE 59, PASS 4, PRESS 4 — 9 SHOOTs blocked by guard |
Errors 0. No RESET (stock had 123). Coach chat received by all 5 (`sf hold`, `nani shoot`).

### Report columns are swapped (verified)
The portal's "How agents played" / "Agent performance" column labelled *Fort Knox* matches OUR logs:
Move 212 ≈ our 219, Mark 31 = our 31, GK Dist 8 = our 8, GK latency 91 ms = our rule-based keeper.
=> Coach's-corner advice in the report is based on the wrong team. Use our logs, not that section.

### Root causes found
1. **Possession bug (stock lib)**: `possessionAgentId` ("agentId_3") exists once per team; stock code took the
   first match = always the HOME player. As HOME we "had" the ball whenever the opponent's same-number player had it
   → SHOOT/PASS issued without the ball → blocked/wasted. Independently reported by team DCON (Baku 2026).
   Payload confirmed: ball keys = angularVelocity, isFree, position, possessionAgentId, rotation, velocity (no team).
   Fix v1.2: resolve by distance to the ball (+ explicit team field if the server ever sends one).
2. **Guard reasons not logged** → couldn't tell "too far" from "no ball". Fixed v1.2.
3. **HOLD mode shot cap 18** too strict (coach used `sf hold`). Raised to 24.

## External evidence used
- 72-hour pre-test write-up (Beijing UG): prompt-only rules ignored ~40%; 92-98% of shots were long hoofs;
  put must-happen rules in code; reset history per tick; cap tokens. Only the designated (closest) player presses.
- Team DCON (Baku 2026) repo: fully rule-based v8, ~97 ms; FWD shoots ≤24 (≤32 with open lane); MID ≤20/26;
  GK on ball-goal line; only closest player presses; possession normalisation was "the biggest fix".
- Strands blog: tight prompts, validate outputs, command diversity matters.

## Process (from v1.2)
- `C:\dev\tools\release.ps1` — runs all suites; refuses to deploy on any failure or uncommitted change; logs the commit deployed.
- Iker logs every raw payload → replay dataset for offline regression tests.
