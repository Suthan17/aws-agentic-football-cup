"""Read-only: does a runtime's log group contain the model input (coach text, score)?"""
import sys
import time

import boto3

PREFIX = sys.argv[1]
MINUTES = float(sys.argv[2]) if len(sys.argv) > 2 else 60
L = boto3.client("logs", region_name="us-east-1")
g = L.describe_log_groups(logGroupNamePrefix="/aws/bedrock-agentcore/runtimes/" + PREFIX)["logGroups"][0]["logGroupName"]
start = int((time.time() - MINUTES * 60) * 1000)
for pattern in ['"COACH INSTRUCTIONS"', '"Score:"', '"LLM returned"', '"fallback"', '"agent error"']:
    r = L.filter_log_events(logGroupName=g, startTime=start, filterPattern=pattern, limit=50)
    ev = r["events"]
    print(f"{pattern:22s} events(first page)={len(ev)}")
    if ev and pattern in ('"COACH INSTRUCTIONS"', '"Score:"'):
        print("   sample:", ev[0]["message"][:300].replace("\n", " | "))
