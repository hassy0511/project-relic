extends RefCounted
## 世界と進行のテスト：部屋の移動、扉・鍵、宝箱、壊れる壁、仕掛け、セーブ、やられたとき、イベント、会話、経済。

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


## 20m 四方の部屋 2 つ（a の東の開口と b の西の開口でつながる）。a の出口は東（+X）の壁の開口
func _world(extra_a: Dictionary = {}, extra_b: Dictionary = {}) -> Dictionary:
	var a := {
		"geometry": [{"t": "shell", "pos": [0, 0, 0], "size": [20, 8, 20], "openings": [{"side": "e", "at": 0, "w": 4, "h": 4}]}],
		"markers": {"start": {"pos": [0, 0, 0], "yaw": 90}, "from_b": {"pos": [7.5, 0, 0], "yaw": 90}},
		"props": [
			{"type": "exit", "id": "to_b", "pos": [10, 0, 0], "size": [1.5, 4, 4], "to": "b", "spawn": "from_a"},
			{"type": "beacon", "id": "bc_a", "pos": [-5, 0, 0]},
		],
		"triggers": [], "enemies": [], "checkpoints": [], "playerStart": "start", "objective": "テスト",
	}
	var b := {
		"geometry": [{"t": "shell", "pos": [0, 0, 0], "size": [20, 8, 20], "openings": [{"side": "w", "at": 0, "w": 4, "h": 4}]}],
		"markers": {"start": {"pos": [0, 0, 0], "yaw": 90}, "from_a": {"pos": [-7.5, 0, 0], "yaw": 90}},
		"props": [
			{"type": "exit", "id": "to_a", "pos": [-10, 0, 0], "size": [1.5, 4, 4], "to": "a", "spawn": "from_b"},
		],
		"triggers": [], "enemies": [], "checkpoints": [],
	}
	for k in extra_a:
		if a.has(k) and a[k] is Array:
			a[k].append_array(extra_a[k])
		else:
			a[k] = extra_a[k]
	for k in extra_b:
		if b.has(k) and b[k] is Array:
			b[k].append_array(extra_b[k])
		else:
			b[k] = extra_b[k]
	return {
		"start": {"room": "t.a", "spawn": "start"},
		"areas": [{"id": "t", "name": "テスト", "rooms": {"a": a, "b": b}}],
		"dialogues": {
			"hello": {"lines": [{"who": "a", "face": "normal", "text": "やあ"}]},
			"ask": {"lines": [{"who": "a", "text": "どうする？", "choices": [{"text": "はい", "set": "yes"}, {"text": "いいえ", "set": "no"}]}]},
		},
		"events": {},
		"items": {"relic.gear": {"name": "歯車", "sell": 100}, "key.a": {"name": "鍵"}},
	}


func test_room_transition() -> void:
	var g := h.make_world_game(_world())
	await h.settle()
	h.expect(g.room_id == "t.a", "最初の部屋にいる")
	await h.run_until(g, TestHelpers.seconds(3), {"move_y": 1.0}, func(): return g.room_id != "t.a")
	h.expect(g.room_id == "t.b", "東の開口の出口に入ると次の部屋に移る（%s）" % g.room_id)
	h.expect(g.flag("visited.t.a") and g.flag("visited.t.b"), "入った部屋が記録される")
	h.near(g.player.pos.x, -7.5, 1.0, "移った先の入口に立つ")
	h.expect(g.beacons.is_empty(), "前の部屋の物は消える")
	var ev := g.drain_events().filter(func(e): return e.type == "autosave" or e.type == "roomChanged")
	h.expect(ev.any(func(e): return e.type == "autosave"), "部屋を移るとオートセーブの出来事が出る")
	# 立っているだけでは戻らない（入口は出口の範囲の外）
	await h.run(g, TestHelpers.seconds(1), {})
	h.expect(g.room_id == "t.b", "入口に立っていても勝手に戻らない")
	# 戻る：西へ（向きを反転）
	g.player.yaw = -PI / 2
	g.cam.yaw = -PI / 2
	await h.run_until(g, TestHelpers.seconds(3), {"move_y": 1.0}, func(): return g.room_id != "t.b")
	h.expect(g.room_id == "t.a" and g.beacons.size() == 1, "戻れて、前の部屋の物が作り直される（%s）" % g.room_id)
	h.expect(g.visited_rooms().size() == 2, "地図の入った部屋の一覧")
	h.free_game(g)


func test_wall_blocks_and_ramp() -> void:
	var w := _world({"geometry": [{"t": "ramp", "pos": [-4, 0, 4], "size": [4, 2, 6], "yaw": 90}]})
	var g := h.make_world_game(w)
	await h.settle()
	# 壁（北）へ向かう：開口の無い壁で止まる
	g.player.teleport(Vector3(0, 0, 0), 0.0)
	g.cam.yaw = 0.0
	await h.run(g, TestHelpers.seconds(3), {"move_y": 1.0})
	h.between(g.player.pos.z, 8.5, 10.0, "壁の手前で止まる")
	# 斜面（pos の中心から +X 側が高い）を登る
	g.player.teleport(Vector3(-8.2, 0, 4), PI / 2)
	g.cam.yaw = PI / 2
	await h.run_until(g, TestHelpers.seconds(1.5), {"move_y": 1.0}, func(): return g.player.pos.y > 1.2)
	h.expect(g.player.pos.y > 1.2, "斜面を登って高い所に着く（y=%.2f）" % g.player.pos.y)
	h.free_game(g)


func test_door_key_and_shortcut() -> void:
	var door := {"type": "door", "id": "d1", "pos": [3, 0, 0], "yaw": 90, "size": [4, 4, 0.5], "lock": {"item": "key.a"}, "consume": "key.a", "text": "鍵がいる"}
	var g := h.make_world_game(_world({"props": [door]}))
	await h.settle()
	g.player.teleport(Vector3(1.5, 0, 0), PI / 2)
	g.cam.yaw = PI / 2
	await h.run(g, 2, {})
	h.expect(g.focus != null and g.focus.id == "d1", "扉の前で調べる対象になる")
	await h.run(g, 1, {"jump": true})
	h.expect(not g.doors[0].is_open, "鍵が無ければ開かない")
	h.expect(g.drain_events().any(func(e): return e.type == "message" and e.text == "鍵がいる"), "鍵が必要だと知らせる")
	await h.run(g, TestHelpers.seconds(1.5), {"move_y": 1.0})
	h.between(g.player.pos.x, 0.5, 2.9, "閉じた扉で止まる")
	g.give_item("key.a")
	await h.run(g, 2, {})
	await h.run(g, 1, {"jump": true})
	h.expect(g.doors[0].is_open and g.flag("door.d1"), "鍵があれば開く（フラグ door.d1）")
	h.expect(not g.has_item("key.a"), "鍵は使うと無くなる（consume）")
	await h.run(g, TestHelpers.seconds(1.5), {"move_y": 1.0})
	print("DBG ", g.player.pos, g.player.yaw, g.cam.yaw, g.doors[0].body, g.story.blocking())
	h.expect(g.player.pos.x > 3.5, "開いた扉を通れる")
	h.free_game(g)
	# 近道の扉：内側（背面）からだけ開けられる。開けたら残る
	var sc := {"type": "door", "id": "sc", "pos": [3, 0, 0], "yaw": 90, "size": [4, 4, 0.5], "side": "back"}
	var g2 := h.make_world_game(_world({"props": [sc]}))
	await h.settle()
	g2.player.teleport(Vector3(1.5, 0, 0), PI / 2)
	await h.run(g2, 2, {})
	h.expect(g2.focus == null or g2.focus.id != "sc", "外側（正面）からは開けられない")
	g2.player.teleport(Vector3(4.5, 0, 0), -PI / 2)
	await h.run(g2, 2, {})
	h.expect(g2.focus != null and g2.focus.id == "sc", "内側（背面）からは調べられる")
	await h.run(g2, 1, {"jump": true})
	h.expect(g2.doors[0].is_open, "近道の扉が開く")
	# 別の部屋へ行って戻っても開いたまま
	g2.go_to("b", "from_a")
	await h.run(g2, 5, {})
	g2.go_to("a", "start")
	await h.run(g2, 5, {})
	h.expect(g2.doors[0].is_open and g2.doors[0].body == null, "部屋を出入りしても開いたまま")
	h.free_game(g2)


func test_chest_once_and_persist() -> void:
	var chest := {"type": "chest", "id": "c1", "pos": [0, 0, 1.2], "yaw": 0, "contents": {"cells": 150, "materials": {"scrap": 3}, "relics": ["relic.gear"], "items": ["key.a"]}}
	var g := h.make_world_game(_world({"props": [chest]}))
	await h.settle()
	await h.run(g, 2, {})
	await h.run(g, 1, {"jump": true})
	h.expect(g.cells == 150 and g.material_count("scrap") == 3 and g.relics.has("relic.gear") and g.has_item("key.a"), "セル・素材・遺物・アイテムが入る")
	h.expect(g.chests[0].opened and g.flag("chest.c1"), "開いた宝箱はフラグになる")
	await h.run(g, 3, {})
	await h.run(g, 1, {"jump": true})
	h.expect(g.cells == 150 and g.material_count("scrap") == 3, "2 回目は何も出ない")
	h.expect(g.focus == null, "開けた宝箱は調べる対象にならない")
	g.go_to("b", "from_a")
	await h.run(g, 5, {})
	g.go_to("a", "start")
	await h.run(g, 5, {})
	h.expect(g.chests[0].opened, "部屋を出入りしても開いたまま")
	await h.run(g, 3, {"jump": true})
	h.expect(g.cells == 150, "作り直した部屋でも中身は 1 度だけ")
	h.free_game(g)


func test_loot_once() -> void:
	var g := h.make_world_game(_world({"props": [{"type": "loot", "id": "l1", "pos": [0, 0, 0.5], "contents": {"relics": ["relic.gear"], "cells": 20}}]}))
	await h.settle()
	await h.run(g, 3, {})
	h.expect(g.relics.has("relic.gear") and g.cells == 20, "置いてある遺物に触れると手に入る")
	g.go_to("b")
	await h.run(g, 5, {})
	g.go_to("a", "start")
	await h.run(g, 5, {})
	await h.run(g, 3, {})
	h.expect(g.cells == 20, "取ったものは戻ってこない")
	h.free_game(g)


func test_breakable_persists() -> void:
	var wall := {"type": "breakable", "id": "w1", "pos": [0, 0, 1.4], "size": [4, 4, 1], "breaksWith": "drill"}
	var g := h.make_world_game(_world({"props": [wall]}))
	await h.settle()
	g.give_item("special.drill")
	g.player.teleport(Vector3(0, 0, 0), 0.0)
	await h.run(g, TestHelpers.seconds(2), {"special": true})
	h.expect(g.breakables[0].broken and g.flag("broken.w1"), "ドリルで壊すとフラグが立つ")
	g.go_to("b")
	await h.run(g, 5, {})
	g.go_to("a", "start")
	await h.run(g, 5, {})
	h.expect(g.breakables[0].broken and g.breakables[0].body == null, "壊した壁は戻ってこない")
	h.free_game(g)


func test_power_gimmick() -> void:
	# 動力の球を 2 つ撃つと、ピストンの足場が上がる。足場に乗っていると運ばれる
	var props := [
		{"type": "switch", "id": "s1", "pos": [-6, 1.5, 6], "mode": "shoot"},
		{"type": "switch", "id": "s2", "pos": [-3, 1.5, 6], "mode": "shoot"},
		{"type": "mover", "id": "lift", "pos": [4, 0, -4], "size": [4, 0.5, 4], "move": [0, 3, 0], "speed": 3.0, "mode": "toggle", "cond": {"all": ["switch.s1", "switch.s2"]}},
	]
	var g := h.make_world_game(_world({"props": props}))
	await h.settle()
	h.expect(g.movers[0].pos.y < 0.01, "動力が無いうちは下にある")
	var shoot := func(target: Vector3):
		var o := Vector3(target.x, target.y, target.z - 5.0)
		g.spawn_player_shot({"origin": o, "dir": Vector3(0, 0, 1), "speed": 40.0, "range": 30.0, "damage": 5.0, "radius": 0.2, "pierce": false, "kind": "normal"})
	shoot.call(Vector3(-6, 1.5, 6))
	await h.run(g, 20, {})
	h.expect(g.switch_by_id("s1").on and g.flag("switch.s1"), "撃つとスイッチが入る")
	await h.run(g, 60, {})
	h.expect(g.movers[0].pos.y < 0.01, "片方だけでは動かない")
	shoot.call(Vector3(-3, 1.5, 6))
	# 足場の上に立って待つ
	g.player.teleport(Vector3(4, 0.5, -4), 0.0)
	await h.run(g, 10, {})
	h.expect(g.player.grounded, "足場の上に立てる")
	await h.run(g, TestHelpers.seconds(1.5), {})
	h.expect(g.movers[0].pos.y > 1.0, "動力が通ると足場が上がる（y=%.2f）" % g.movers[0].pos.y)
	h.expect(g.player.pos.y > 1.5, "乗っているハルも運ばれる（y=%.2f）" % g.player.pos.y)
	await h.run(g, TestHelpers.seconds(2), {})
	h.near(g.movers[0].pos.y, 3.0, 0.01, "上の端で止まる")
	h.near(g.player.pos.y, 3.5, 0.15, "ハルは足場の上にいる")
	h.free_game(g)


func test_timed_switch_and_pingpong() -> void:
	var props := [
		{"type": "switch", "id": "t1", "pos": [0, 0, 0], "mode": "interact", "timer": 1.0},
		{"type": "mover", "id": "pp", "pos": [4, 0, 4], "size": [2, 0.5, 2], "move": [4, 0, 0], "speed": 4.0, "mode": "pingpong", "wait": 0.5, "cond": "switch.t1"},
	]
	var g := h.make_world_game(_world({"props": props}))
	await h.settle()
	await h.run(g, 2, {})
	await h.run(g, 1, {"jump": true})
	h.expect(g.flag("switch.t1"), "調べるとスイッチが入る")
	await h.run(g, TestHelpers.seconds(0.6), {})
	h.expect(g.movers[0].pos.x > 4.5, "入っている間は往復する足場が動く")
	await h.run(g, TestHelpers.seconds(0.8), {})
	h.expect(not g.flag("switch.t1"), "時間が来るとスイッチが切れる")
	var x0: float = g.movers[0].pos.x
	await h.run(g, TestHelpers.seconds(1.0), {})
	h.near(g.movers[0].pos.x, x0, 0.001, "切れている間は止まる")
	h.free_game(g)


func test_save_roundtrip() -> void:
	var props := [
		{"type": "chest", "id": "c1", "pos": [0, 0, 1.2], "yaw": 0, "contents": {"cells": 150}},
		{"type": "door", "id": "d9", "pos": [3, 0, 5], "yaw": 90, "lock": null},
		{"type": "switch", "id": "s1", "pos": [-6, 1.5, 6], "mode": "interact"},
		{"type": "mover", "id": "lift", "pos": [4, 0, -4], "size": [4, 0.5, 4], "move": [0, 3, 0], "mode": "toggle", "cond": "switch.s1"},
		{"type": "breakable", "id": "w1", "pos": [0, 0, 8], "size": [4, 2, 1]},
	]
	var g := h.make_world_game(_world({"props": props}))
	await h.settle()
	await h.run(g, 2, {})
	await h.run(g, 1, {"jump": true})
	g.open_door("d9")
	g.activate_switch(g.switch_by_id("s1"))
	g.break_breakable(g.breakables[0])
	g.add_material("scrap", 4)
	g.give_relic("relic.gear")
	g.set_mark("降下許可")
	g.requests["r1"] = "accepted"
	g.set_flag("ch1.drive_powered")
	g.go_to("b", "from_a")
	await h.run(g, 5, {})
	var text := JSON.stringify(g.to_save("t"))
	var parsed = GameSim.parse_save(text)
	h.expect(parsed != null, "セーブを読める")
	var g2 := h.make_world_game(_world({"props": props}), {"save": parsed})
	await h.settle()
	h.expect(g2.room_id == "t.b", "いた部屋から再開する")
	h.expect(g2.cells == 150 and g2.material_count("scrap") == 4 and g2.relics.has("relic.gear"), "セル・素材・遺物が戻る")
	h.expect(g2.mark == "降下許可" and g2.requests.get("r1") == "accepted", "印・依頼が戻る")
	h.expect(g2.flag("ch1.drive_powered") and g2.flag("visited.t.a") and g2.flag("visited.t.b"), "フラグ・入った部屋が戻る")
	h.expect(g2.player.pos.distance_to(g.player.pos) < 0.05, "位置が戻る")
	# 前の部屋に戻って仕掛けの状態を見る
	g2.go_to("a", "start")
	await h.run(g2, 5, {})
	h.expect(g2.chests[0].opened, "開けた宝箱は開いたまま")
	h.expect(g2.doors[0].is_open, "開けた扉は開いたまま")
	h.expect(g2.breakables[0].broken, "壊した壁は壊れたまま")
	h.expect(g2.switch_by_id("s1").on and g2.movers[0].pos.y > 2.9, "入れたスイッチと動いた足場の状態が戻る")
	h.free_game(g)
	h.free_game(g2)


func test_death_returns_to_beacon() -> void:
	var boss := {"type": "sentry", "id": "boss", "pos": [5, 0, 5], "unless": "ch1.boss_defeated"}
	var g := h.make_world_game(_world({"enemies": []}, {"enemies": [boss]}))
	await h.settle()
	# a の灯り（ビーコン）を使う
	g.player.teleport(Vector3(-4, 0, 0), 0.0)
	await h.run(g, 2, {})
	await h.run(g, 1, {"jump": true})
	h.expect(g.respawn.room == "t.a" and g.checkpoint == "bc_a", "ビーコンを使うと戻る場所になる")
	h.expect(g.drain_events().any(func(e): return e.type == "saved"), "ビーコンでセーブの出来事が出る")
	g.go_to("b", "from_a")
	await h.run(g, 5, {})
	h.expect(g.room_id == "t.b" and g.enemies.size() == 1, "b には敵がいる")
	g.player.take_damage(9999.0, Vector3(0, 0, 0), true, true)
	h.expect(g.player.dead, "やられる")
	await h.run(g, TestHelpers.seconds(2.3), {})
	h.expect(not g.player.dead and g.room_id == "t.a", "最後のビーコンの部屋で再開する（%s）" % g.room_id)
	h.expect(g.player.pos.distance_to(Vector3(-5, 0, 0)) < 1.0, "ビーコンの位置に立つ")
	h.expect(g.player.hp == g.player.max_hp, "HP が戻る")
	# 倒したボスは戻ってこない
	g.set_flag("ch1.boss_defeated")
	g.go_to("b", "from_a")
	await h.run(g, 5, {})
	h.expect(g.enemies.is_empty(), "倒したボスは部屋に入り直しても出ない（unless）")
	h.free_game(g)


func test_event_chain() -> void:
	var w := _world({
		"props": [{"type": "door", "id": "arena_door", "pos": [3, 0, 0], "yaw": 90, "open": true}],
		"triggers": [
			{"id": "t_enter", "pos": [0, 0, 3], "size": [4, 2, 2], "event": "ev.start"},
			{"id": "t_watch", "on": "flag", "cond": "arena_done", "event": "ev.after"},
		],
	})
	w.events = {
		"ev.start": {"steps": [
			{"flag": "started"}, {"close": "arena_door"},
			{"spawn": [{"type": "sentry", "pos": [6, 0, 6], "group": "g1"}]},
			{"wait_until": {"cleared": "g1"}},
			{"open": "arena_door"}, {"give": {"cells": 77}}, {"flag": "arena_done"},
		]},
		"ev.after": {"steps": [{"if": "arena_done", "then": [{"flag": "after_ran"}], "else": [{"flag": "wrong"}]}]},
	}
	var g := h.make_world_game(w)
	await h.settle()
	g.player.teleport(Vector3(0, 0, 2), 0.0)
	await h.run(g, 3, {})
	h.expect(g.flag("started") and g.flag("trigger.t_enter"), "トリガーに入るとイベントが走る")
	h.expect(not g.doors[0].is_open, "イベントが扉を閉める")
	h.expect(g.enemies.size() == 1 and g.enemies[0].group == "g1", "イベントが敵を出す")
	await h.run(g, 30, {})
	h.expect(not g.flag("arena_done"), "敵がいるあいだは先に進まない（wait_until）")
	g.damage_enemy(g.enemies[0], 9999.0, Vector3.ZERO, {})
	await h.run(g, 6, {})
	h.expect(g.flag("cleared.g1"), "グループを全部倒すとフラグが立つ")
	h.expect(g.doors[0].is_open and g.cells >= 77 and g.flag("arena_done"), "続きの手順が走る（開く・渡す・フラグ）")
	h.expect(g.flag("after_ran") and not g.flag("wrong"), "フラグが立つとトリガーが働き、if が分岐する")
	h.free_game(g)


func test_dialogue_choice_and_freeze() -> void:
	var w := _world({"triggers": [{"id": "t", "pos": [0, 0, 3], "size": [4, 2, 2], "event": "ev.ask"}]})
	w.events = {"ev.ask": {"steps": [{"freeze": true}, {"say": "ask"}, {"freeze": false}, {"flag": "after"}]}}
	var g := h.make_world_game(w)
	await h.settle()
	g.player.teleport(Vector3(0, 0, 2), 0.0)
	await h.run(g, 3, {})
	h.expect(g.story.dialogue.has("choices") and g.story.dialogue.choices.size() == 2, "選択肢つきの会話が出る")
	await h.run(g, 60, {})
	await h.run(g, 1, {"move_y": -1.0})
	await h.run(g, 2, {})
	h.expect(g.story.dialogue.sel == 1, "下を入れると選択肢が動く")
	await h.run(g, 1, {"jump": true})
	await h.run(g, 3, {})
	h.expect(g.flag("no") and not g.flag("yes"), "決定で選んだ答えのフラグが立つ")
	h.expect(g.story.dialogue.is_empty() and g.flag("after") and not g.player_locked, "会話が終わると続きが走り、ロックが解ける")
	h.free_game(g)


func test_locked_exit_and_objective() -> void:
	var w := _world()
	w.areas[0].rooms.a.props[0]["lock"] = "gate_open"
	w.areas[0].rooms.a.props[0]["text"] = "動力が来ていない"
	var g := h.make_world_game(w)
	await h.settle()
	await h.run(g, TestHelpers.seconds(2.5), {"move_y": 1.0})
	h.expect(g.room_id == "t.a", "条件を満たさない出口は通れない")
	h.expect(g.drain_events().any(func(e): return e.type == "message" and e.text == "動力が来ていない"), "通れない理由を知らせる")
	g.set_flag("gate_open")
	await h.run_until(g, TestHelpers.seconds(1), {"move_y": 1.0}, func(): return g.room_id != "t.a")
	h.expect(g.room_id == "t.b", "条件が満ちると通れる")
	h.free_game(g)


func test_economy() -> void:
	var w := _world()
	w.economy = {
		"shops": {"zakka": {"name": "雑貨屋", "buys_relics": true, "stock": [{"item": "consumable.repair", "price": 100}, {"item": "key.a", "price": 500, "cond": "shop_open"}]}},
		"workshops": {"yana": {"name": "工房", "recipes": [{"id": "drill", "name": "ドリル", "cost": 50, "needs": {"core": 1}, "gives": {"item": "special.drill"}}]}},
		"guild": {"requests": [{"id": "r1", "name": "探し物", "done": {"item": "key.a"}, "reward": {"cells": 300, "gp": 10}}]},
	}
	var g := h.make_world_game(w)
	await h.settle()
	g.give_cells(250)
	var heals0: int = g.player.heals
	h.expect(Economy.buy(g, "zakka", "consumable.repair").ok and g.cells == 150 and g.player.heals == heals0 + 1, "店で買える")
	h.expect(not Economy.buy(g, "zakka", "key.a").ok, "条件を満たさない品は買えない")
	g.set_flag("shop_open")
	h.expect(not Economy.buy(g, "zakka", "key.a").ok and g.cells == 150, "セルが足りなければ買えない")
	g.give_relic("relic.gear")
	h.expect(Economy.sell_relic(g, "zakka", "relic.gear").ok and g.cells == 250 and not g.relics.has("relic.gear"), "遺物を売れる（items の sell）")
	h.expect(not Economy.craft(g, "yana", "drill").ok, "素材が無ければ作れない")
	g.add_material("core", 1)
	h.expect(Economy.craft(g, "yana", "drill").ok and g.has_item("special.drill") and g.cells == 200 and g.material_count("core") == 0, "工房で素材とセルを払って作る")
	h.expect(not Economy.complete_request(g, "r1").ok, "受けていない依頼は完了できない")
	h.expect(Economy.accept_request(g, "r1").ok and g.requests["r1"] == "accepted", "依頼を受ける")
	h.expect(not Economy.complete_request(g, "r1").ok, "達成していない依頼は完了できない")
	g.give_item("key.a")
	h.expect(Economy.complete_request(g, "r1").ok and g.cells == 500 and g.guild_points == 10 and g.requests["r1"] == "done", "達成すると報酬が入る")
	h.free_game(g)
