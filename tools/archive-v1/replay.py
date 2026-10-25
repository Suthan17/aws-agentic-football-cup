"""Rebuild matches tick by tick from the goalkeeper's PAYLOAD logs.

Usage: python replay.py <start UTC HH:MM> [end UTC HH:MM] [--dump file.jsonl]
Prints per match: our side, possession split, where our carriers were, and the
ticks leading up to every goal (ball + nearest players), so goals can be
explained from data instead of guessed.
"""
import datetime as dt
import json
import math
import sys

import boto3

sys.path.insert(0, r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents\lib")
from state import _resolve_holder, _is_my_team, _player_idx, get_goal_positions  # noqa: E402
import frame  # noqa: E402

NAMES = {0: "Iker", 1: "Piyol", 2: "Busqets", 3: "Nani", 4: "Siuuu"}
argv = sys.argv[1:]
dump = None
if "--dump" in argv:
    i = argv.index("--dump")
    dump = argv[i + 1]
    argv = argv[:i] + argv[i + 2:]
args = argv


def _ms(hhmm):
    h, m = map(int, hhmm.split(":"))
    t = dt.datetime.now(dt.timezone.utc).replace(hour=h, minute=m, second=0, microsecond=0)
    return int(t.timestamp() * 1000)


logs = boto3.client("logs", region_name="us-east-1")
group = logs.describe_log_groups(
    logGroupNamePrefix="/aws/bedrock-agentcore/runtimes/TeamStrandsBalanced_ai_gk_agent")["logGroups"][0]["logGroupName"]
kw = dict(logGroupName=group, startTime=_ms(args[0]), filterPattern='"PAYLOAD"')
if len(args) > 1:
    kw["endTime"] = _ms(args[1])

payloads = []
while True:
    r = logs.filter_log_events(**kw)
    for e in r["events"]:
        m = e["message"]
        if not m[:4].isdigit() or "PAYLOAD {" not in m:
            continue
        try:
            payloads.append((e["timestamp"], json.loads(m.split("PAYLOAD ", 1)[1])))
        except json.JSONDecodeError:
            pass
    if "nextToken" not in r:
        break
    kw["nextToken"] = r["nextToken"]
payloads.sort(key=lambda x: x[0])
if dump:
    with open(dump, "w", encoding="utf-8") as f:
        for ts, p in payloads:
            f.write(json.dumps({"ts": ts, "payload": p}) + "\n")
print(f"{len(payloads)} payloads")

# Split into matches: gameTime goes backwards, or a gap of > 60 s wall clock.
matches, cur, last_t, last_ts = [], [], None, None
for ts, p in payloads:
    gt = float(p.get("gameState", {}).get("gameTime", 0) or 0)
    if cur and ((last_t is not None and gt + 5 < last_t) or ts - last_ts > 60_000):
        matches.append(cur)
        cur = []
    cur.append((ts, p))
    last_t, last_ts = gt, ts
if cur:
    matches.append(cur)


def d(a, b):
    return math.hypot(a.get("x", 0) - b.get("x", 0), a.get("y", 0) - b.get("y", 0))


for mi, match in enumerate(matches, 1):
    if len(match) < 10:
        continue
    team = match[0][1].get("teamId", 0)
    my_goal_x, opp_goal_x = get_goal_positions(team)
    side = "HOME" if team == 0 else "AWAY"
    t0 = dt.datetime.fromtimestamp(match[0][0] / 1000, dt.timezone.utc).strftime("%H:%M:%S")
    print(f"\n######## MATCH {mi} — start {t0} UTC — we are {side} (attack toward x={opp_goal_x:+.0f}) — {len(match)} ticks")
    poss = {"us": 0, "them": 0, "free/unknown": 0}
    carrier_dist = {pid: [] for pid in range(5)}
    prev_score = None
    history = []
    for ts, p in match:
        gs = frame.to_canonical(p.get("gameState", {}))
        ball, players = gs.get("ball", {}) or {}, gs.get("players", []) or []
        h = _resolve_holder(ball, players) if ball.get("isFree") is not True else None
        if h is None:
            poss["free/unknown"] += 1
        elif _is_my_team(h, team):
            poss["us"] += 1
            carrier_dist[_player_idx(h)].append(d(h.get("position", {}), {"x": opp_goal_x, "y": 0}))
        else:
            poss["them"] += 1
        score = gs.get("score", {})
        history.append((gs, h))
        if prev_score is not None and score != prev_score:
            us_scored = (score.get("home", 0) > prev_score.get("home", 0)) == (team == 0)
            print(f"\n  GOAL at {gs.get('gameTime', 0):.0f}s — {'WE scored' if us_scored else 'THEY scored'} — score {score}")
            for g2, h2 in history[-5:-1]:
                b2 = (g2.get("ball") or {}).get("position", {})
                who = "free"
                if h2 is not None:
                    who = ("OUR " + NAMES.get(_player_idx(h2), "?")) if _is_my_team(h2, team) else f"THEIR #{_player_idx(h2)}"
                ours = {NAMES[_player_idx(q)]: (round(q['position']['x']), round(q['position']['y']))
                        for q in g2.get("players", []) if _is_my_team(q, team)}
                theirs = sorted(((round(d(q["position"], b2)), _player_idx(q), round(q["position"]["x"]), round(q["position"]["y"]))
                                 for q in g2.get("players", []) if not _is_my_team(q, team)))[:2]
                print(f"    t={g2.get('gameTime', 0):5.0f}s mode={g2.get('playMode')} ball=({b2.get('x', 0):.0f},{b2.get('y', 0):.0f}) "
                      f"holder={who} | ours={ours} | their nearest to ball (dist,#,x,y)={theirs}")
        prev_score = score
    tot = sum(poss.values()) or 1
    print(f"  final score {match[-1][1]['gameState'].get('score')}")
    print("  possession (ticks): " + ", ".join(f"{k} {v} ({100 * v / tot:.0f}%)" for k, v in poss.items()))
    for pid, ds in carrier_dist.items():
        if ds:
            ds.sort()
            print(f"  {NAMES[pid]:8s} had ball {len(ds):3d} ticks; dist to goal min {ds[0]:.0f} median {ds[len(ds) // 2]:.0f}")
