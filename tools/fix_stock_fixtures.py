"""Make stock test fixtures realistic: when a test gives our player the ball,
put the ball at that player's feet (the possession fix resolves ambiguous
agentIds by distance to the ball)."""
import pathlib

import sys
TEAM = pathlib.Path(r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents") / (sys.argv[1] if len(sys.argv) > 1 else "ai-team-strands-balanced")
SYNC = '    state["ball"]["position"] = dict(state["players"][MY_PLAYER_ID]["position"], z=0)  # carrier stands on the ball\n'
MARK = 'state["ball"]["possessionAgentId"] = f"agentId_{MY_PLAYER_ID}"'

for test in sorted(TEAM.glob("ai-*/test_local.py")):
    lines = test.read_text(encoding="utf-8").splitlines(keepends=True)
    if SYNC in lines:
        print(f"{test.parent.name}: already patched")
        continue
    out, i, n = [], 0, 0
    while i < len(lines):
        out.append(lines[i])
        if MARK in lines[i]:
            if i + 1 < len(lines) and '["position"] = ' in lines[i + 1] and "players" in lines[i + 1]:
                i += 1
                out.append(lines[i])
            out.append(SYNC)
            n += 1
        i += 1
    test.write_text("".join(out), encoding="utf-8")
    print(f"{test.parent.name}: {n} fixture(s) patched")
