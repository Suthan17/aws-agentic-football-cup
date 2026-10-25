"""Offline checks for Saturn v1.1: coach chat parsing, rules_first, guard."""
import copy
import sys

sys.path.insert(0, r"C:\dev\sample-ai-possibilities\agentic-football-sample-agents\lib")

import coach
from tactics import rules_first, guard, smart_aim
from fallback import build_fallback, FWD1_CONFIG, DEF_CONFIG
from test_helpers import GAME_STATE

ok = True


def check(label, cond):
    global ok
    ok &= bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")


print("=== coach chat parsing ===")
for text, want in [
    ("nani shoot", ({3}, "SHOOT", False)),
    ("naani shot!", ({3}, "SHOOT", False)),
    ("Siuuu press", ({4}, "PRESS", False)),
    ("piyol stay back", ({1}, "DEFEND", False)),
    ("keeper stay home, defend", ({0}, "DEFEND", False)),
    ("sf attack", (set(), "ATTACK", True)),
    ("sf defnd", (set(), "DEFEND", True)),
    ("saturn hold possession", (set(), "HOLD", True)),
    ("attack", (set(), "ATTACK", False)),
]:
    got = coach.parse_message(text)
    check(f"{text!r} -> {got}", got == want)

print("=== team mode only from prefix or names ===")
gs = copy.deepcopy(GAME_STATE)
gs["teamChat"] = ["everyone attack now"]  # no prefix: could be the opponent
coach.update_from_chat(gs, 0)
check("unprefixed team order ignored", coach.current_orders(gs, 0, 3)[2] is False)
gs["teamChat"] = ["everyone attack now", "sf attack"]
coach.update_from_chat(gs, 0)
check("prefixed order sets ATTACK", coach.current_orders(gs, 0, 3)[:1] == ("ATTACK",))
gs["teamChat"] = [{"teamCode": "away", "message": "sf defend"}]
coach.update_from_chat(gs, 0)
check("opponent-tagged message ignored", coach.current_orders(gs, 0, 3)[0] == "ATTACK")
gs["teamChat"] = ["nani shoot"]
coach.update_from_chat(gs, 0)
check("named order reaches Nani", coach.current_orders(gs, 0, 3)[1] == "SHOOT")
check("named order not given to Siuuu", coach.current_orders(gs, 0, 4)[1] is None)
later = copy.deepcopy(gs); later["gameTime"] = gs["gameTime"] + 30
check("named order expires", coach.current_orders(later, 0, 3)[1] is None)
newmatch = copy.deepcopy(GAME_STATE); newmatch["gameTime"] = 3.0; newmatch["teamChat"] = []
coach.update_from_chat(newmatch, 0)
check("new match clears coach mode", coach.current_orders(newmatch, 0, 3)[2] is False)

print("=== real server chat format ===")
rs = copy.deepcopy(GAME_STATE); rs["gameTime"] = 2.0; rs["teamChat"] = []
coach.update_from_chat(rs, 0)  # fresh match
rs["gameTime"] = 10.0
rs["teamChat"] = [{"senderTeamCode": "home", "message": "attack", "timestamp": 0}]
coach.update_from_chat(rs, 0)
check("our tagged 'attack' (no sf) sets ATTACK", coach.current_orders(rs, 0, 2)[0] == "ATTACK")
rs["teamChat"].append({"senderTeamCode": "away", "message": "sf defend", "timestamp": 0})
coach.update_from_chat(rs, 0)
check("opponent's tagged 'sf defend' ignored", coach.current_orders(rs, 0, 2)[0] == "ATTACK")
saved = copy.deepcopy(coach._state)
coach._state.update(seen={}, mode=None, player={})
coach.update_from_chat(rs, 1)
check("as AWAY team, the away 'sf defend' is ours", coach.current_orders(rs, 1, 2)[0] == "DEFEND")
coach._state.clear(); coach._state.update(saved)
nani = {"senderTeamCode": "home", "message": "nani shoot", "timestamp": 0}
rs["teamChat"] = [nani]
coach.update_from_chat(rs, 0)
check("nani shoot heard", coach.current_orders(rs, 0, 3)[1] == "SHOOT")
rs["gameTime"] = 40.0
coach.update_from_chat(rs, 0)
check("nani order expired after 15s", coach.current_orders(rs, 0, 3)[1] is None)
rs["teamChat"] = [nani, nani]
coach.update_from_chat(rs, 0)
check("repeated 'nani shoot' re-applies", coach.current_orders(rs, 0, 3)[1] == "SHOOT")

print("=== rules_first ===")
# Nani (3) holds the ball at x=14 → 41 from goal: no auto shot, LLM decides
check("far from goal -> LLM", rules_first(GAME_STATE, 0, 3, "FWD1", "BALANCED", None) is None)
close = copy.deepcopy(GAME_STATE)
close["players"][3]["position"] = {"x": 42, "y": -3}
close["ball"]["position"] = {"x": 42.3, "y": -3.1, "z": 0}  # ball is at the carrier's feet
r = rules_first(close, 0, 3, "FWD1", "BALANCED", None)
check(f"close -> auto SHOOT {r and r[0]['parameters']}", r and r[0]["commandType"] == "SHOOT")
mid_range = copy.deepcopy(GAME_STATE)
mid_range["players"][3]["position"] = {"x": 22, "y": -5}
mid_range["ball"]["position"] = {"x": 22.3, "y": -5.1, "z": 0}
check("33 units, no order -> LLM", rules_first(mid_range, 0, 3, "FWD1", "BALANCED", None) is None)
r = rules_first(mid_range, 0, 3, "FWD1", "BALANCED", "SHOOT")
check("coach SHOOT order from 33 units -> SHOOT", r and r[0]["commandType"] == "SHOOT")
gk = copy.deepcopy(GAME_STATE); gk["ball"]["possessionAgentId"] = "agentId_0"
gk["ball"]["position"] = {"x": -49.6, "y": 0.2, "z": 0}  # in our keeper's hands
r = rules_first(gk, 0, 0, "GK", "BALANCED", None)
check(f"GK with ball -> {r and r[0]['commandType']} to {r and r[0]['parameters']}", r and r[0]["commandType"] == "GK_DISTRIBUTE")
away = copy.deepcopy(close)
for p in away["players"]:
    p["teamCode"] = "away" if p["teamCode"] == "home" else "home"
    p["position"]["x"] = -p["position"]["x"]
away["ball"]["position"]["x"] = -away["ball"]["position"]["x"]
r = rules_first(away, 1, 3, "FWD1", "BALANCED", None)
check("AWAY side close -> auto SHOOT", r and r[0]["commandType"] == "SHOOT")

r = rules_first(GAME_STATE, 0, 0, "GK", "BALANCED", None)
check(f"GK without ball always ruled -> {r and r[0]}", r and r[0]["commandType"] == "MOVE_TO"
      and r[0]["parameters"]["target_x"] <= -45)
r = rules_first(away, 1, 0, "GK", "BALANCED", None)
check(f"AWAY GK stays at +x goal -> {r and r[0]['parameters']}", r and r[0]["parameters"]["target_x"] >= 45)

print("=== possession: same agentId on both teams ===")
from state import holder_is_me, get_possession_info  # noqa: E402
ps = copy.deepcopy(GAME_STATE)
# Opponent #3 (away, at 30,-12) has the ball; our #3 (home) is at 14,-5.
ps["ball"]["possessionAgentId"] = "agentId_3"
ps["ball"]["position"] = {"x": 30.3, "y": -11.8, "z": 0}
check("HOME: our #3 does NOT have opponent #3's ball", not holder_is_me(ps["ball"], ps["players"], 0, 3))
check("HOME: possession reads as OPP", get_possession_info(ps["ball"], ps["players"], 0)[2] is False)
check("AWAY view: we (#3 away) DO have it", holder_is_me(ps["ball"], ps["players"], 1, 3))
ps["ball"]["position"] = {"x": 14.2, "y": -5.1, "z": 0}
check("HOME: our #3 on the ball has it", holder_is_me(ps["ball"], ps["players"], 0, 3))
ps["ball"]["possessionTeamCode"] = "away"
check("explicit possessionTeamCode wins over distance", not holder_is_me(ps["ball"], ps["players"], 0, 3))

print("=== guard ===")
fb1 = build_fallback(FWD1_CONFIG)
mv ={"commandType": "MOVE_TO", "playerId": 3, "parameters": {"target_x": 20, "target_y": -12, "sprint": True}, "duration": 0}
for role, p in [("FWD1", 3), ("MID", 2), ("FWD2", 4), ("DEF", 1)]:
    c = dict(mv, playerId=p, parameters={"target_x": -20, "target_y": -12, "sprint": True})
    g = guard([c], GAME_STATE, 0, p, role, "BALANCED", None, fb1)
    check(f"{role}: valid MOVE_TO passes through unchanged", g == [c])
fb1 = build_fallback(FWD1_CONFIG)
g = guard([{"commandType": "RESET", "playerId": 3, "parameters": {}, "duration": 0}],
          GAME_STATE, 0, 3, "FWD1", "BALANCED", None, fb1)
check(f"RESET replaced -> {[c['commandType'] for c in g]}", all(c["commandType"] != "RESET" for c in g))
g = guard([{"commandType": "SHOOT", "playerId": 3, "parameters": {"aim_location": "TR", "power": 0.5}, "duration": 0}],
          GAME_STATE, 0, 3, "FWD1", "BALANCED", None, fb1)
check(f"41-unit shot replaced -> {[c['commandType'] for c in g]}", g[0]["commandType"] != "SHOOT")
g = guard([{"commandType": "SLIDE_TACKLE", "playerId": 3, "parameters": {"target_player_id": 1}, "duration": 0}],
          GAME_STATE, 0, 3, "FWD1", "BALANCED", None, fb1)
check("slide tackle -> PRESS_BALL", g[0]["commandType"] == "PRESS_BALL")
fbd = build_fallback(DEF_CONFIG)
g = guard([{"commandType": "MOVE_TO", "playerId": 1, "parameters": {"target_x": 30, "target_y": 0, "sprint": True}, "duration": 0}],
          GAME_STATE, 0, 1, "DEF", "BALANCED", None, fbd)
check(f"DEF upfield run clamped -> x={g[0]['parameters']['target_x']}", g[0]["parameters"]["target_x"] < 0)
g = guard([{"commandType": "PRESS_BALL", "playerId": 1, "parameters": {"intensity": 0.9}, "duration": 3}],
          GAME_STATE, 0, 1, "DEF", "BALANCED", None, fbd)
check(f"DEF chasing in opp half -> {g[0]['commandType']}", g[0]["commandType"] == "MOVE_TO")
g = guard([{"commandType": "MOVE_TO", "playerId": 0, "parameters": {"target_x": 0, "target_y": 0, "sprint": True}, "duration": 0}],
          GAME_STATE, 0, 0, "GK", "BALANCED", None, fbd)
check(f"GK leaving goal clamped -> x={g[0]['parameters']['target_x']}", g[0]["parameters"]["target_x"] <= -43)

print("=== stamina guard ===")
from tactics import stamina_guard  # noqa: E402
tired = copy.deepcopy(GAME_STATE)
tired["players"][2]["stamina"] = 0.2           # Busqets tired, ball far from our goal
tired["ball"]["possessionAgentId"] = "agentId_4"
tired["ball"]["position"] = {"x": 20.2, "y": 15.1, "z": 0}
c = stamina_guard([{"commandType": "MOVE_TO", "playerId": 2, "parameters": {"target_x": 10, "target_y": 0, "sprint": True}, "duration": 0}],
                  tired, 0, 2)
check("tired player in calm moment does not sprint", c[0]["parameters"]["sprint"] is False)
tired["ball"]["position"] = {"x": -45, "y": 0, "z": 0}  # danger near our goal
tired["ball"]["possessionAgentId"] = "agentId_4"
c = stamina_guard([{"commandType": "MOVE_TO", "playerId": 2, "parameters": {"target_x": -40, "target_y": 0, "sprint": True}, "duration": 0}],
                  tired, 0, 2)
check("tired player may sprint when ball is near our goal", c[0]["parameters"]["sprint"] is True)
fresh = copy.deepcopy(GAME_STATE)
c = stamina_guard([{"commandType": "MOVE_TO", "playerId": 4, "parameters": {"target_x": 30, "target_y": 0, "sprint": True}, "duration": 0}],
                  fresh, 0, 4)
check("fresh player keeps sprint", c[0]["parameters"]["sprint"] is True)

print("=== auto mode on a 120 s match ===")
am = copy.deepcopy(GAME_STATE)
am["score"] = {"home": 0, "away": 1}; am["gameTime"] = 85.0
check("losing at 85 s -> ATTACK", coach.auto_mode(am, 0) == "ATTACK")
am["score"] = {"home": 1, "away": 0}; am["gameTime"] = 100.0
check("winning by 1 at 100 s -> DEFEND", coach.auto_mode(am, 0) == "DEFEND")
am["gameTime"] = 30.0
check("winning by 1 at 30 s -> BALANCED", coach.auto_mode(am, 0) == "BALANCED")

print("=== frame adapter ===")
import frame  # noqa: E402
srv = {"ball": {"position": {"x": 6.43, "y": 0.16, "z": -3.48}}, "players": [{"position": {"x": -6.4, "y": 1.0}}]}
cv = frame.to_canonical(srv)
check(f"ball width from z, scaled -> {cv['ball']['position']}", abs(cv["ball"]["position"]["y"] - (-3.48 * frame.S)) < 1e-6
      and abs(cv["ball"]["position"]["x"] - 6.43 * frame.S) < 1e-6)
check("documented-frame payload left untouched", frame.to_canonical(GAME_STATE) is GAME_STATE)
back = frame.to_server([{"commandType": "MOVE_TO", "parameters": {"target_x": 55.0, "target_y": -100.0, "sprint": False}}], True)
check(f"outgoing MOVE_TO scaled + clamped -> {back[0]['parameters']}",
      back[0]["parameters"]["target_x"] == frame.SERVER_MAX_X and back[0]["parameters"]["target_y"] == -frame.SERVER_MAX_Y)

print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
