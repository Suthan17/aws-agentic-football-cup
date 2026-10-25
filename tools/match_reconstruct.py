"""Read-only match reconstruction from OTEL model-input/output records.

Usage: python match_reconstruct.py <runtime prefix e.g. TeamSaturnCounter> <start HH:MM UTC> <end HH:MM UTC>
For each player: every model input (game time, score, hasBall, keeper flag, coach lines)
joined with the model's output command via traceId. Prints:
  - score timeline (game time of each score change)
  - coach message states as seen by players
  - every SHOOT decision by a player who had the ball, with what happened to the score next
"""
import collections
import datetime as dt
import json
import re
import sys

import boto3

PREFIX, START, END = sys.argv[1], sys.argv[2], sys.argv[3]
L = boto3.client("logs", region_name="us-east-1")
NAMES = {"gk": "Iker", "def": "Piyol", "mid": "Busqets", "fwd1": "Nani", "fwd2": "Siuuu"}


def ms(hhmm):
    h, m = map(int, hhmm.split(":"))
    t = dt.datetime.now(dt.timezone.utc).replace(hour=h, minute=m, second=0, microsecond=0)
    return int(t.timestamp() * 1000)


def records(group):
    kw = dict(logGroupName=group, startTime=ms(START), endTime=ms(END))
    while True:
        r = L.filter_log_events(**kw)
        for e in r["events"]:
            if e["message"].startswith("{"):
                try:
                    yield e["timestamp"], json.loads(e["message"])
                except json.JSONDecodeError:
                    pass
        if "nextToken" not in r:
            break
        kw["nextToken"] = r["nextToken"]


def text_of(body):
    if isinstance(body, dict):
        parts = []
        for c in body.get("content") or []:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                parts.append(c["text"])
        msg = body.get("message")
        if isinstance(msg, dict):
            parts.append(text_of(msg))
        return "\n".join(parts)
    return body if isinstance(body, str) else ""


ticks = []  # (wall_ts, player, input_text, output_text)
event_names = collections.Counter()
for key, name in NAMES.items():
    groups = L.describe_log_groups(logGroupNamePrefix=f"/aws/bedrock-agentcore/runtimes/{PREFIX}_ai_{key}_agent")["logGroups"]
    if not groups:
        continue
    by_trace = collections.defaultdict(dict)
    for ts, d in records(groups[0]["logGroupName"]):
        ev = d.get("eventName") or ""
        event_names[ev] += 1
        tr = d.get("traceId")
        txt = text_of(d.get("body"))
        if not tr or not txt:
            continue
        if "Time:" in txt and "Score:" in txt:
            by_trace[tr]["in"] = txt
            by_trace[tr]["ts"] = ts
        elif "commandType" in txt:
            by_trace[tr]["out"] = txt
    for tr, v in by_trace.items():
        if "in" in v:
            ticks.append((v["ts"], name, v["in"], v.get("out", "")))

ticks.sort()
print("event names seen:", dict(event_names.most_common(6)))
print(f"model decisions reconstructed: {len(ticks)}")


def parse(inp):
    t = re.search(r"Time: (\d+)s \| Score: (\d+)-(\d+) \| Team: (\d)", inp)
    hb = re.search(r"hasBall=(True|False)", inp)
    ball = re.search(r"^Ball: \(([^)]*)\) held by (.*)$", inp, re.M)
    pos = re.search(r"pos=\((-?[\d.]+),(-?[\d.]+)\)", inp)
    coach = re.findall(r"^  - (.*)$", inp.split("COACH INSTRUCTIONS", 1)[1], re.M) if "COACH INSTRUCTIONS" in inp else []
    return {
        "t": int(t.group(1)) if t else None, "home": int(t.group(2)) if t else None,
        "away": int(t.group(3)) if t else None, "team": int(t.group(4)) if t else None,
        "has_ball": hb and hb.group(1) == "True", "x": float(pos.group(1)) if pos else None,
        "keeper_out": "OUT OF GOAL" in inp, "coach": coach,
        "ball": f"({ball.group(1)}) {ball.group(2)}" if ball else "?",
        "mode": (re.search(r"PlayMode: (\S+)", inp) or [None, "?"])[1],
    }


def cmd_of(out):
    m = re.search(r'"commandType"\s*:\s*"([A-Z_]+)"', out)
    return m.group(1) if m else "?"


rows = [(ts, who, parse(i), cmd_of(o)) for ts, who, i, o in ticks]
rows = [r for r in rows if r[2]["t"] is not None]

# Split matches on game-clock reset.
matches, cur, last_t = [], [], None
for r in rows:
    if cur and last_t is not None and r[2]["t"] + 10 < last_t:
        matches.append(cur)
        cur = []
    cur.append(r)
    last_t = r[2]["t"]
if cur:
    matches.append(cur)

for mi, m in enumerate(matches, 1):
    team = m[0][2]["team"]
    mine = "home" if team == 0 else "away"
    print(f"\n######## MATCH {mi}: {len(m)} decisions, game time {m[0][2]['t']}..{m[-1][2]['t']}s, we are {mine.upper()}")
    # Score timeline (as seen in inputs, by game time).
    print("  score changes (game time -> home-away):")
    prev = None
    for ts, who, p, c in m:
        sc = (p["home"], p["away"])
        if sc != prev:
            print(f"    t={p['t']:3d}s  {sc[0]}-{sc[1]}")
            prev = sc
    # Coach states.
    print("  coach messages as seen by players (first game time each state appeared):")
    prev = None
    for ts, who, p, c in m:
        if p["coach"] != prev:
            print(f"    t={p['t']:3d}s  {p['coach']}")
            prev = p["coach"]
    # Ball-carrier decisions.
    carrier = [(p["t"], who, c, p["keeper_out"], p["coach"][-1] if p["coach"] else "-", p["x"])
               for ts, who, p, c in m if p["has_ball"]]
    print(f"  decisions while holding the ball: {len(carrier)}  -> {dict(collections.Counter(c for _, _, c, *_ in carrier))}")
    print("  every SHOOT while holding the ball (t, player, keeper_out, latest coach msg, x):")
    for t, who, c, ko, lc, x in carrier:
        if c == "SHOOT":
            print(f"    t={t:3d}s {who:8s} keeper_out={ko!s:5s} coach='{lc}' x={x}")
    # The 10 s before each score change: ball status + every carrier decision.
    print("  build-up to each score change (unique ball status per game second):")
    prev = None
    for ts, who, p, c in m:
        sc = (p["home"], p["away"])
        if prev is not None and sc != prev:
            goal_t = p["t"]
            scorer = "WE scored" if (sc[0] > prev[0]) == (team == 0) else "THEY scored"
            print(f"   -- {scorer}, first seen at t={goal_t}s ({prev[0]}-{prev[1]} -> {sc[0]}-{sc[1]})")
            seen = set()
            for ts2, who2, p2, c2 in m:
                if goal_t - 10 <= p2["t"] < goal_t and (p2["t"], p2["ball"]) not in seen:
                    seen.add((p2["t"], p2["ball"]))
                    print(f"      t={p2['t']:3d}s ball: {p2['ball']}")
                if goal_t - 10 <= p2["t"] < goal_t and p2["has_ball"]:
                    print(f"      t={p2['t']:3d}s   {who2} HAS BALL -> {c2} (keeper_out={p2['keeper_out']}, x={p2['x']})")
        prev = sc
    print("  non-SHOOT ball decisions and kickoff-spot shots (t, player, cmd, playMode, x):")
    for ts, who, p, c in m:
        if p["has_ball"] and (c != "SHOOT" or p["x"] in (-1.0, 1.0)):
            print(f"    t={p['t']:3d}s {who:8s} {c:14s} mode={p['mode']} x={p['x']}")
    ko = [p["keeper_out"] for _, _, p, _ in m]
    print(f"  opponent keeper flagged OUT on {sum(ko)}/{len(ko)} inputs ({100 * sum(ko) / max(1, len(ko)):.0f}%)")
