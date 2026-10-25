"""Measure the real coordinate ranges seen in a replay dump (jsonl from replay.py --dump)."""
import json
import sys

xs, ys, bxs, bys, gk = [], [], [], [], []
kick = []
for line in open(sys.argv[1], encoding="utf-8"):
    p = json.loads(line)["payload"]
    gs = p["gameState"]
    b = (gs.get("ball") or {}).get("position")
    if not b or len(gs.get("players", [])) < 10:
        continue  # skip my manual smoke-test payloads
    bxs.append(b["x"]); bys.append(b["y"])
    for q in gs["players"]:
        xs.append(q["position"]["x"]); ys.append(q["position"]["y"])
        if q["agentId"].endswith("_0"):
            gk.append((q["teamCode"], round(q["position"]["x"], 2), round(q["position"]["y"], 2)))
    if gs.get("playMode") != "OPEN_PLAY" or gs.get("gameTime", 0) < 3:
        kick.append((gs.get("gameTime"), gs.get("playMode"),
                     [(q["teamCode"][0], q["agentId"][-1], round(q["position"]["x"], 1), round(q["position"]["y"], 1)) for q in gs["players"]]))


def rng(v):
    return f"min {min(v):7.2f}  max {max(v):7.2f}"


print("players x:", rng(xs)); print("players y:", rng(ys))
print("ball    x:", rng(bxs)); print("ball    y:", rng(bys))
home_gk = [g for g in gk if g[0] == "home"]; away_gk = [g for g in gk if g[0] == "away"]
print("home GK x range:", rng([g[1] for g in home_gk]))
print("away GK x range:", rng([g[1] for g in away_gk]))
print("\nkick-off / non-open-play ticks (team, idx, x, y):")
for k in kick[:4]:
    print(" ", k)
sample = json.loads(open(sys.argv[1], encoding="utf-8").readline())["payload"]
print("\nfirst payload player fields:", sorted(sample["gameState"]["players"][0].keys()))
print("gameState fields:", sorted(sample["gameState"].keys()))
