"""Read-only: print the structure of one OTEL log record that contains the model input."""
import json
import sys
import time

import boto3

PREFIX = sys.argv[1] if len(sys.argv) > 1 else "TeamSaturnCounter_ai_fwd1"
L = boto3.client("logs", region_name="us-east-1")
g = L.describe_log_groups(logGroupNamePrefix="/aws/bedrock-agentcore/runtimes/" + PREFIX)["logGroups"][0]["logGroupName"]
r = L.filter_log_events(logGroupName=g, startTime=int((time.time() - 40 * 60) * 1000),
                        filterPattern='"COACH INSTRUCTIONS"', limit=1)
d = json.loads(r["events"][0]["message"])
print("top keys:", list(d.keys()))
print("scope:", d.get("scope"))
print("attributes:", {k: str(v)[:80] for k, v in (d.get("attributes") or {}).items()})
print("body type:", type(d.get("body")).__name__)
print(json.dumps(d.get("body"))[:1800])
