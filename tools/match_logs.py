"""Summarise what each Saturn agent did in the last N minutes, from CloudWatch.

Usage: python match_logs.py [minutes=10]
"""
import collections
import re
import sys
import time

import boto3

import datetime as dt

ARG = sys.argv[1] if len(sys.argv) > 1 else "10"
END_ARG = sys.argv[2] if len(sys.argv) > 2 else None
AGENTS = ["gk", "def", "mid", "fwd1", "fwd2"]
NAMES = {"gk": "Iker", "def": "Piyol", "mid": "Busqets", "fwd1": "Nani", "fwd2": "Siuuu"}

logs = boto3.client("logs", region_name="us-east-1")


def _ms(arg):
    """Minutes-ago number, or a UTC time like 13:21 (today)."""
    if ":" in arg:
        h, m = map(int, arg.split(":"))
        t = dt.datetime.now(dt.timezone.utc).replace(hour=h, minute=m, second=0, microsecond=0)
        return int(t.timestamp() * 1000)
    return int((time.time() - float(arg) * 60) * 1000)


start = _ms(ARG)
end = _ms(END_ARG) if END_ARG else None


def group_for(agent):
    prefix = f"/aws/bedrock-agentcore/runtimes/TeamStrandsBalanced_ai_{agent}_agent"
    groups = logs.describe_log_groups(logGroupNamePrefix=prefix)["logGroups"]
    return groups[0]["logGroupName"] if groups else None


def messages(group):
    kwargs = dict(logGroupName=group, startTime=start)
    if end:
        kwargs["endTime"] = end
    while True:
        resp = logs.filter_log_events(**kwargs)
        for e in resp["events"]:
            m = e["message"]
            if m[:4].isdigit():  # plain-text line; the OTEL JSON copies are duplicates
                yield m
        if "nextToken" not in resp:
            break
        kwargs["nextToken"] = resp["nextToken"]


for a in AGENTS:
    g = group_for(a)
    if not g:
        print(f"{a}: no log group")
        continue
    cmds = collections.Counter()
    src = collections.Counter()
    guards, chats, errors = [], [], []
    for m in messages(g):
        body = m.split("] - ", 1)[-1]
        if "RULE returned" in body:
            src["rule"] += 1
            cmds.update(re.findall(r"'([A-Z_]+)'", body.split("(mode")[0]))
        elif "LLM returned" in body:
            src["llm"] += 1
        elif "using fallback" in body:
            src["fallback"] += 1
        elif "GUARD replaced" in body:
            guards.append(body)
        elif "teamChat=" in body:
            chats.append(body)
        elif re.search(r"agent error|Traceback|Exception", body):
            errors.append(body)
        m2 = re.search(r"LLM returned \d+ commands: \['([A-Z_]+)'", body)
        if m2:
            cmds[m2.group(1)] += 1
    print(f"\n=== {NAMES[a]} ({a}) — rule={src['rule']} llm={src['llm']} fallback={src['fallback']} "
          f"guard={len(guards)} errors={len(errors)}")
    print("   commands:", dict(cmds.most_common()))
    for gline in collections.Counter(re.sub(r"\s+", " ", x) for x in guards).most_common(4):
        print("   guard:", gline[0][:110], "x", gline[1])
    if chats:
        print("   last chat:", chats[-1][:160])
    for e in errors[:3]:
        print("   ERROR:", e[:200])
