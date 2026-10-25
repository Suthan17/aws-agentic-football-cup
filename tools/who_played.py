"""Which squad actually served recent matches? Counts agent invocations per runtime."""
import datetime as dt
import sys
import time

import boto3

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3
L = boto3.client("logs", region_name="us-east-1")
start = int((time.time() - HOURS * 3600) * 1000)
for g in L.describe_log_groups(logGroupNamePrefix="/aws/bedrock-agentcore/runtimes/")["logGroups"]:
    name = g["logGroupName"].split("/")[-1]
    ts, kw = [], dict(logGroupName=g["logGroupName"], startTime=start, filterPattern='"agent invoked"')
    while True:
        r = L.filter_log_events(**kw)
        ts += [e["timestamp"] for e in r["events"] if e["message"][:4].isdigit()]
        if "nextToken" not in r:
            break
        kw["nextToken"] = r["nextToken"]
    f = lambda t: dt.datetime.fromtimestamp(t / 1000).strftime("%H:%M")  # noqa: E731
    print(f"{name[:48]:48s} invocations={len(ts):4d} " + (f"first {f(min(ts))} last {f(max(ts))}" if ts else ""))
