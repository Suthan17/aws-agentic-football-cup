"""Tests for coach chat in the state summary (run: python test_coach_chat.py)."""

import copy
import sys

from state import summarize_state, coach_lines
from test_helpers import GAME_STATE

failures = 0


def check(name, cond):
    global failures
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    failures += 0 if cond else 1


def msg(team, text):
    return {"senderTeamCode": team, "message": text, "timestamp": 0}


print("=== COACH CHAT ===")
gs = copy.deepcopy(GAME_STATE)
check("no chat -> summary unchanged", "COACH" not in summarize_state(gs, 0, 3, "FWD1"))

gs["teamChat"] = [msg("home", "Nani shoot now"), msg("away", "everyone defend")]
s = summarize_state(gs, 0, 3, "FWD1")
check("our message reaches HOME agent", "Nani shoot now" in s)
check("opponent message dropped for HOME agent", "everyone defend" not in s)
check("agent is told its own name", "You are NANI" in s)

s_away = summarize_state(gs, 1, 3, "FWD1")
check("AWAY agent sees only the away coach", "everyone defend" in s_away and "Nani shoot now" not in s_away)

gs["teamChat"] = [msg("home", f"order {i}") for i in range(6)]
lines = coach_lines(gs, 0, 2)
check("only the latest 3 kept", "order 5" in "\n".join(lines) and "order 2" not in "\n".join(lines))

gs["teamChat"] = ["plain string", None, 42, {"message": "no sender"}, msg("home", "   "), msg("HOME", "Busqets pass")]
lines = coach_lines(gs, 0, 2)
check("malformed entries ignored, team code case-insensitive", lines and "Busqets pass" in lines[-1] and len(lines) == 3)

gs["teamChat"] = [msg("home", "x" * 1000)]
check("very long message truncated", len(coach_lines(gs, 0, 1)[-1]) < 220)

print(f"\n{'All' if not failures else failures} tests {'passed' if not failures else 'FAILED'}")
sys.exit(1 if failures else 0)
