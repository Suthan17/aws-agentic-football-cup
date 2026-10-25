# AWS Agentic Football Cup — Saturn Flotillas

Five autonomous AI agents playing 5v5 football, built for the **AWS EMEA Early Career Talent Hackathon**
(October 2026). Each player is its own agent: built with the [Strands Agents SDK](https://github.com/strands-agents/sdk-python),
deployed to **Amazon Bedrock AgentCore Runtime**, reasoning with **Amazon Nova Micro**. Every ~2 seconds the match
server sends each agent the game state and it returns one command (move, pass, shoot, press, mark, intercept…).

**Tournament record: 7 played — 5 wins, 1 draw, 1 loss (71% win rate).**

## How it works

```
Match server ──(game state JSON, every ~2 s)──► agent on AgentCore (one per player)
                                                   │ lib/state.py  → text summary (+ coach messages, + "keeper out" fact)
                                                   │ Nova Micro    → reads system prompt + summary, picks ONE command
                                                   │ lib/parsing.py→ validates the JSON command
                                                   │ lib/fallback.py → rule-based backup if the model fails
Match server ◄──────────(command)──────────────────┘
```

The code follows the structure of AWS's sample agents
([aws-samples/sample-ai-possibilities](https://github.com/aws-samples/sample-ai-possibilities/tree/main/agentic-football-sample-agents)):
a shared `lib/` engine, and per player a `main.py` with four fixed parts — position config, system prompt,
fallback config, wire-up. Strategy lives in the system prompt.

## The squads

Each squad is a separate AgentCore project with its own 5 runtime ARNs, so switching squads in the Player Portal
is a paste — no redeploy during a tournament.

| Folder | Squad | What it is |
|---|---|---|
| `ai-team-saturn/` | A — Saturn | AWS's balanced agents unchanged + live coach chat |
| `ai-team-saturn-counter/` | C — Counter | A + a "Match Plan — Counter-Attack" prompt block, an "opponent keeper out of goal" fact, and a possession fix. Built for opponents who push everyone (even the goalkeeper) forward |

Squad C turned the matchup against AWS's *Total Attack United* bot from a 1–3 loss into a **5–1 win**.

## What I changed in the shared `lib/` (all with tests)

| Change | Why (evidence) |
|---|---|
| **Coach chat** — our team's latest 3 `teamChat` messages + the player's own name go into the model input | The stock code never read the chat, so coaching did nothing. Live test: our "Nani, pass to Siuuu" changed SHOOT→PASS 3/3; the same message from the opponent's coach was ignored 3/3 |
| **Possession fix** — the ball's `possessionAgentId` exists once per team; resolve it by distance to the ball | Stock always picked the HOME player, so a player could "shoot" a ball the opponent's same-numbered player had |
| **"Opponent goalkeeper: OUT OF GOAL" fact** — measured relative to player spread | Replay data: Total Attack's keeper was out of goal on 71% of ticks |

## How I worked (the part that mattered most)

1. **Started too clever, lost.** My first versions rewrote the decision engine with custom rules. They scored worse
   than AWS's own sample agents (1 win in 3 vs 3 in 4), because I had replaced the engine's built-in movement
   with hand-calculated coordinates based on wrong assumptions.
2. **Measured instead of guessed.** Rebuilding matches from CloudWatch logs showed facts the docs didn't: the real
   pitch is ~8× smaller than documented, the ball's sideways axis is `z` (its `y` is height), matches last 120 s,
   and two sections of the portal's match report had the teams' columns swapped.
3. **Went back to stock and changed one thing at a time**, playing several matches per change and keeping a
   scoreboard ([docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)). Prompt-only changes, AWS-format.
4. **A release gate** ([tools/release.ps1](tools/release.ps1)) runs every test suite and refuses to deploy on a
   failure or uncommitted change, logging which commit went live.
5. **Coached live.** Typing **"shoot"** the moment we won the ball with space produced the long-range goals behind
   the comebacks — see the log-verified breakdown in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Tools

| Tool | Purpose |
|---|---|
| `tools/release.ps1 -Team <folder>` | Test gate + deploy for any squad folder |
| `tools/match_reconstruct.py` | Rebuild a match from the OTEL logs: score timeline, coach messages as players saw them, every shot by the ball-carrier |
| `tools/who_played.py` | Which squad's runtimes actually served a match |
| `tools/test_counter_live.py`, `tools/test_coach_live.py` | Live A/B checks against the real model |
| `tools/archive-v1/` | Tools for my abandoned v1.x custom engine (kept for the record; not runnable here) |

## Run it yourself

Requirements and deploy steps are AWS's — see the sample repo's README. Copy `lib/` and a squad folder into the
sample's `agentic-football-sample-agents/` directory, then:

```powershell
cd ai-team-saturn-counter
python deploy_all.py
```

Coach-chat player names are set in `lib/state.py` (`PLAYER_NAMES`) and must match the names on your
Player Portal "My Team" page.

## Honest notes

- Model output is random; with 3–5 matches per version, many differences between versions are within noise.
- Squad C's possession fix tripped the portal's GK pre-match fitness check (its simulated scene puts the ball far
  from the keeper "holding" it). Worth knowing if you reuse the fix.
- Built with help from Claude Code as the agentic coding tool (the workshop suggests Kiro; any such tool works).

## Credits and licence

Built on AWS's [sample-ai-possibilities](https://github.com/aws-samples/sample-ai-possibilities) agentic football
sample agents (© Amazon.com, Inc. or its affiliates), licensed **MIT No Attribution** — see
[LICENSE](LICENSE). My additions are released under the same licence.
