# Saturn Flotillas — Squad C: Counter-Attack (vs Total Attack United)

AWS-format copy of `ai-team-saturn`, deployed as its own AgentCore project (`TeamSaturnCounter`) with its own
5 ARNs. Pick this squad against opponents that push everyone forward; switch back by pasting the other ARNs.

## Differences from ai-team-saturn
| Area | Change | Evidence |
|---|---|---|
| shared `lib/state.py` | possession fix: same-numbered players resolved by x-distance to the ball | live: stock FWD2 "shot" without the ball 4/4 when the opponent's #4 had it |
| shared `lib/state.py` | summary line "Opponent goalkeeper: OUT OF GOAL / in goal" (relative to player spread) | real Total Attack replay: their keeper out of goal on 71% of ticks |
| `ai-*/src/main.py` | "## Match Plan — Counter-Attack" block before `## Your Role` (prompt-only) | live A/B, 3 calls each: Piyol PRESS->MARK vs their running keeper; Iker THROW->KICK when their net is empty |

Deploy: `powershell -File C:\dev\tools\release.ps1 -Team ai-team-saturn-counter`
