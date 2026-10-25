# Saturn Flotillas — Experiment Scoreboard

Method (from the manual's Phase 3 loop: Observe → Hypothesize → Change → Deploy → Measure):
- Agent CODE stays 100% stock (AWS-tested). Only system PROMPTS change.
- ONE change per experiment. Same opponents. At least 3 matches before judging (LLMs are non-deterministic).
- Score per match: W=3, D=1, L=0. Keep a change only if it beats the current best on points AND goal difference.
- Judge with match scores + our CloudWatch logs. Ignore the report's "How agents played"/"Agent performance"
  columns — they are swapped (verified against our logs twice).

## Results

| Exp | Change (one thing) | Git commit | Opponent | Score | Notes |
|---|---|---|---|---|---|
| E0 | Stock balanced team | c8972b8 | Fort Knox | W 3-0 | 22 Oct |
| E0 | Stock balanced team | c8972b8 | Benchmark | W 1-0 | 22 Oct, 40% possession |
| E0 | Stock balanced team | c8972b8 | Total Attack | W 2-0 | 23 Oct, 47% poss, shots 8 (2 on target) vs 6 (0) |
| E0 | Stock balanced team | c8972b8 | Benchmark | L 0-2 | 23 Oct, 61% poss, shots 3 (0) vs 10 (2); both goals in minute 1 |

**E0 total: 4 played, W3 L1, 9 pts, GF 6 GA 2 (GD +4).**
Watch: DEF latency 2788 ms in the Total Attack match (limit 5000 ms) — stock DEF prompt is the slowest.
Weakness seen twice vs Benchmark: we have more possession but few shots on target, and concede early.

| E1 | Hybrid: AWS defensive GK+DEF, balanced MID, AWS aggressive FWDs | 3cc1a0c | Benchmark | W 5-2 | 58% poss, 7 shots (5 on target) |
| E1 | (same) | 3cc1a0c | Total Attack | L 1-2 | 64% poss, 7 shots (1) — both goals against in minute 1 |
| E1 | (same) | 3cc1a0c | Fort Knox | W 2-1 | 67% poss, 12 shots (2) — conceded minute 1 |

**E1 total: 3 played, W2 L1, 6 pts, GF 8 GA 5 (GD +3).**

### E0 vs E1 (per match)
| | Points/match | Goals for/match | Goals against/match | GD/match |
|---|---|---|---|---|
| E0 stock (4) | 2.25 | 1.50 | 0.50 | +1.00 |
| E1 hybrid (3) | 2.00 | 2.67 | 1.67 | +1.00 |
Verdict by our rule (must beat on points AND GD): **E1 not adopted.** It scores more but concedes 3x more — aggressive
forwards stop defending. Sample sizes are small (LLM noise), so neither is proven better.
Pattern across 7 matches: every goal we conceded came in minute 1 (7 of 7); most of our goals come in minute 2.

| E2 | Stock + coach chat + possession bug fix + forwards track back/INTERCEPT when opponent has ball | eb81b22 | Benchmark | W 4-3 | 73% poss, 6 shots (4 on target) |
| E2 | (same) | eb81b22 | Total Attack | L 1-2 | 52% poss, 4 shots (1) vs 12 (2) |
| E2 | (same) | eb81b22 | Fort Knox | W 1-0 | 56% poss, clean sheet |

| E2 | (same) — played by mistake: portal still had squad B ARNs (Saturn had 0 invocations) | eb81b22 | Total Attack | L 1-3 | 67% poss, 4 shots (1) vs 8 (3); their GK scored twice |

| E2 + COACHING | (same squad B code) + coach typed "shoot" whenever we won the ball in space | eb81b22 | Total Attack | **W 3-2** | came back from 0-2; 58% poss, 5 shots (3 on target); verified via logs squad B served it (13:12) |

**E2 total: 5 played, W3 L2, 9 pts, GF 10 GA 10 (GD 0).**

| C + COACHING | Squad C TeamSaturnCounter (verified via logs: served 13:42-13:50) + coach typed "shoot" | 3a0ce91 | Total Attack | **W 5-1** | 54% poss, 7 shots (5 on target) |

Log analysis (match_reconstruct.py, 502 model decisions): goals at game time 30/44/52/67/83 s, conceded 114 s.
"shoot" seen by players from t=12 s (2nd at 24 s, 3rd at 35 s; after that the 3-message window is full, so later
identical messages are not distinguishable). 3 of 5 goals (52, 67, 83 s) follow an open-play SHOOT decision by our
ball-holder 1-4 s earlier, taken from x=-3.9..+0.6 (6-11 units from their goal line on a ~14-unit pitch);
goals at 30 and 44 s have no ball-holding SHOOT in the 10 s before them (not attributable from our logs).
Open play with the ball: 9 of 10 decisions were SHOOT. Siuuu's SHOOTs at x=-1.0 were all during RESETTING (after goals).
Coaching finding (user, live): typing "shoot" the moment we won the ball with space produced long shots that
scored — first win vs Total Attack since stock. One-word orders are what a coach can type fast enough.
Total Attack record across all versions: E0 W2-0, E1 L1-2, E2 L1-2, E2 L1-3. Their GOALKEEPER has scored in
3 of our losses — their AWS prompt (manual appendix) pushes the keeper to the halfway line and lets it shoot
within ~35 units; their DEF joins every attack. Our counter-plan: squad C (see below).

### All versions (per match)
| | Played | Pts/match | GF/match | GA/match | GD/match |
|---|---|---|---|---|---|
| E0 stock | 4 | **2.25** | 1.50 | **0.50** | **+1.00** |
| E1 hybrid | 3 | 2.00 | **2.67** | 1.67 | **+1.00** |
| E2 fix+defending fwds | 3 | 2.00 | 2.00 | 1.67 | +0.33 |

| Opponent | E0 | E1 | E2 |
|---|---|---|---|
| Benchmark | W1-0, L0-2 | W5-2 | W4-3 |
| Total Attack | **W2-0** | L1-2 | L1-2 |
| Fort Knox | W3-0 | W2-1 | W1-0 |

Verdict: stock remains best by our rule. Honest caveat: with 3-4 matches each, these differences are within
LLM noise — no variant is proven better or worse. Only consistent signals: every version beats Fort Knox;
only stock has beaten Total Attack; stock concedes least.

E2 caveat: it bundles a bug fix (stock possession misread) with the prompt change, so a better result can't be
credited to the prompt alone. Accepted for time; base without the prompt change is branch exp-coach (2cb06b6).
Live evidence before deploy: with the fix, FWD2 answered INTERCEPT 4/4 when the opponent attacked (stock answered
SHOOT 4/4 without the ball). Coach chat: our "Nani, pass to Siuuu" turned SHOOT into PASS 3/3; the same text from
the opponent and an order for another player were ignored 3/3.

## Archived (custom code, abandoned — kept in git branch saturn-v1)
| Version | Opponent | Score |
|---|---|---|
| v1.1 | Fort Knox | W 1-0 |
| v1.2 | Total Attack | L 1-2 |
| v1.2 | Benchmark | L 0-4 |

## Queue (manual-sourced, prompt-only)
- E1: Hybrid from the manual — defensive GK + defensive DEF, balanced MID, aggressive FWDs ("counter-attacking style").
- E2: Prefer coordinate-free commands (PRESS_BALL / MARK / INTERCEPT / PASS by id) over MOVE_TO;
      evidence: stock won with mostly maintained commands; the server pitch is far smaller than the
      ±55 the prompts describe, so MOVE_TO coordinates get clamped to the edges.
- E3: Stamina wording (sprint only in key moments, lower press intensity).
- Later (optional, AWS features): coach chat reading, AgentCore Memory, Gateway.
