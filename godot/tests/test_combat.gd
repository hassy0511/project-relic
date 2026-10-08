extends RefCounted
## 戦闘・仕掛け・会話・セーブのテスト（three.js 版の combat.test.ts と同じ内容）

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _enemies(list: Array) -> Dictionary:
	return {"enemies": list}


func test_lock_on_and_release() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(0, 0, 10), "e2": Vector3(0, 0, -10)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}, {"type": "sentry", "at": "e2"}]),
	})
	await h.settle()
	await h.run(g, 2, {"lock_on": true})
	h.expect(g.lock_on.target == g.enemies[0], "カメラの前方にいる敵をロックオンする")
	await h.run(g, 2, {"lock_on": false})
	h.expect(g.lock_on.target == null, "離すと解除する")
	h.free_game(g)


func test_switch_target() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(0, 0, 10), "e2": Vector3(5, 0, 10)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}, {"type": "sentry", "at": "e2"}]),
	})
	await h.settle()
	# カメラは +Z を見ている。+X は画面の左
	await h.run(g, 2, {"lock_on": true})
	h.expect(g.lock_on.target == g.enemies[0], "最初は正面の敵")
	await h.run(g, 1, {"lock_on": true, "switch_left": true})
	h.expect(g.lock_on.target == g.enemies[1], "スティックを弾くと、画面の左にいる敵に切り替わる")
	h.free_game(g)


func test_no_lock_through_wall() -> void:
	var g := h.make_game({
		"boxes": [[Vector3(0, 2, 5), Vector3(10, 4, 1)]],
		"markers": {"e1": Vector3(0, 0, 10)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}]),
	})
	await h.settle()
	await h.run(g, 2, {"lock_on": true})
	h.expect(g.lock_on.target == null, "壁の向こうの敵はロックオンできない")
	h.free_game(g)


## 押し続けている間は、押した瞬間に誰もいなくても、見えた刻みで捉える（押し直さなくてよい）
func test_lock_on_acquires_while_held() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(0, 0, -15)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}]),
	})
	await h.settle()
	await h.run(g, 40, {"lock_on": true})
	h.expect(g.lock_on.target == null, "背後 15 m の敵は、押した瞬間には捉えない")
	g.cam.yaw = U.dir_to_yaw(0.0, -15.0)
	await h.run(g, 2, {"lock_on": true})
	h.expect(g.lock_on.target == g.enemies[0], "押したままカメラを向けると、押し直さずに捉える")
	h.free_game(g)


## すぐ近く（8 m 以内）の敵は、カメラの向きに関係なく捉える
func test_lock_on_near_enemy_any_angle() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(0, 0, -5)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}]),
	})
	await h.settle()
	await h.run(g, 2, {"lock_on": true})
	h.expect(g.lock_on.target == g.enemies[0], "背後 5 m の敵も捉える")
	h.free_game(g)


func test_gun_kills_sentry() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(0, 0, 8)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}]),
	})
	await h.settle()
	g.god_mode = true
	await h.run(g, TestHelpers.seconds(6), {"lock_on": true, "fire": true})
	h.expect(not g.enemies[0].alive, "ロックオンして撃ち続けると歩哨型を倒せる")
	h.expect(g.pickups.size() + g.cells > 0, "倒すとセルが出る")
	h.free_game(g)


## ロックオンしていない弾は、ハルの体の向きへ水平に飛ぶ。カメラを 90° 横へ回して見上げても、カメラの方へは撃たず、
## ハルも向きを変えない（カメラの先に敵がいても狙わない）。チャージ弾も同じ
func test_unlocked_shot_follows_body_facing() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(10, 0, 0)},
		"placement": _enemies([{"type": "sentry", "at": "e1", "passive": true}]),
	})
	await h.settle()
	g.god_mode = true
	var e = g.enemies[0]
	var hp0: float = e.hp
	g.player.yaw = 0.0
	g.cam.yaw = PI / 2
	g.cam.pitch = -30.0 * U.DEG
	await h.run(g, 1, {"fire": true})
	h.expect(g.shots.size() == 1, "撃つと弾が 1 発出る（%d）" % g.shots.size())
	var s: Shot = g.shots[0]
	h.near(s.dir.x, 0.0, 0.001, "弾はカメラの向き（+X）ではなく体の向き（+Z）へ飛ぶ：横の成分")
	h.near(s.dir.y, 0.0, 0.001, "カメラで見上げても弾は水平")
	h.expect(s.dir.z > 0.999, "弾は体の正面（+Z）へ")
	h.expect(s.homing == null, "ロックオンしていない弾は追わない")
	h.near(g.player.yaw, 0.0, 0.0001, "撃ってもハルはカメラの方へ向きを変えない")
	var x0: float = s.pos.x
	await h.run(g, 12, {})
	h.expect(s.pos.z > 4.0 and absf(s.pos.x - x0) < 0.001, "弾は体の正面へまっすぐ進む（z=%.2f）" % s.pos.z)
	h.expect(e.hp == hp0, "カメラの先（+X）の敵には当たらない")
	h.near(g.player.yaw, 0.0, 0.0001, "撃ったあとも体の向きはそのまま")
	# チャージ弾も体の向きへ
	g.equipped_chips["chip.charge"] = true
	g.player.gun_cooldown = 0.0
	g.cam.yaw = -PI / 2
	await h.run(g, TestHelpers.seconds(1.4), {"fire": true})
	await h.run(g, 1, {})
	var last: Shot = g.shots[g.shots.size() - 1]
	h.expect(last.kind == "charge2", "長押しして離すと溜め 2 段目の弾（%s）" % last.kind)
	h.expect(last.dir.z > 0.999 and absf(last.dir.y) < 0.001, "チャージ弾も体の正面へ水平に飛ぶ")
	h.near(g.player.yaw, 0.0, 0.0001, "チャージ弾でも体は向きを変えない")
	h.free_game(g)


## 弱い自動照準は体の正面が基準：体の正面から少しずれた敵には狙いが合う（上下の角度も）。カメラの正面の敵は狙わない
func test_soft_aim_uses_body_facing() -> void:
	# 正面から 7° ずれた高い台（上面 2.5m）の上に的の歩哨型、カメラの正面（-X）に歩哨型
	var g := h.make_game({
		"boxes": [[Vector3(1.2, 1.25, 10), Vector3(2, 2.5, 2)]],
		"markers": {"e1": Vector3(1.2, 2.5, 10), "e2": Vector3(-10, 0, 0)},
		"placement": _enemies([{"type": "sentry", "at": "e1", "passive": true}, {"type": "sentry", "at": "e2", "passive": true}]),
	})
	await h.settle()
	g.god_mode = true
	var front = g.enemies[0]
	var side = g.enemies[1]
	var side_hp: float = side.hp
	await h.run(g, 10, {})
	g.player.yaw = 0.0
	g.cam.yaw = -PI / 2
	await h.run(g, 1, {"fire": true})
	var s: Shot = g.shots[0]
	var c: Vector3 = front.center()
	h.expect(c.y > 2.5, "的は高い所にいる（%.2f）" % c.y)
	var want: Vector3 = (c - s.origin).normalized()
	h.expect(s.dir.dot(want) > 0.9999, "体の正面から 7° の敵へ狙いが合う（上下も。dir.y=%.3f）" % s.dir.y)
	h.between(g.player.yaw / U.DEG, 5.0, 9.0, "狙った分だけ体が向く")
	h.expect(await h.run_until(g, 40, {}, func(): return front.hp < front.max_hp), "高い所の敵に当たる")
	h.expect(side.hp == side_hp, "カメラの正面（-X）の敵は狙わない")
	h.free_game(g)


## ロックオン中は、体の向きやカメラに関係なく対象へ撃ち、弾は対象を追う
func test_locked_shot_goes_to_target() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(6, 0, 6)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}]),
	})
	await h.settle()
	g.god_mode = true
	var e = g.enemies[0]
	await h.run(g, 2, {"lock_on": true})
	h.expect(g.lock_on.target == e, "斜め前（45°）の敵をロックオンする")
	await h.run(g, 1, {"lock_on": true, "fire": true})
	var s: Shot = g.shots[0]
	var want: Vector3 = (e.center() - s.origin).normalized()
	h.expect(s.dir.dot(want) > 0.999, "ロックオン中の弾は対象へ向けて撃つ")
	h.expect(s.homing == e, "ロックオン中の弾は対象を追う")
	h.expect(await h.run_until(g, 40, {"lock_on": true}, func(): return e.hp < e.max_hp), "対象に当たる")
	h.free_game(g)


func test_sword_combo() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(0, 0, 1.6)},
		"placement": _enemies([{"type": "charger", "at": "e1"}]),
	})
	await h.settle()
	g.god_mode = true
	var hp0: float = g.enemies[0].hp
	await h.run(g, TestHelpers.seconds(1.5), func(i): return {"sword": i % 8 < 2})
	h.expect(g.enemies[0].hp < hp0 - 30.0, "光刃の 3 段コンボが当たる（残り %.0f）" % g.enemies[0].hp)
	h.free_game(g)


func test_sentry_keeps_distance_and_shoots() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(0, 0, 6)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}]),
	})
	await h.settle()
	g.enemies[0].yaw = PI  # プレイヤーの方を向かせる
	await h.run(g, TestHelpers.seconds(6), {})
	var d: float = g.enemies[0].pos.distance_to(g.player.pos)
	h.expect(d > 7.0, "歩哨型は距離を保つ（%.2fm）" % d)
	h.expect(g.player.hp < g.player.max_hp, "歩哨型は撃ってくる")
	h.free_game(g)


func test_charger_crashes_into_wall() -> void:
	var g := h.make_game({
		"boxes": [[Vector3(0, 2, -6), Vector3(20, 4, 1)]],
		"markers": {"e1": Vector3(0, 0, 10)},
		"placement": _enemies([{"type": "charger", "at": "e1"}]),
	})
	await h.settle()
	var c = g.enemies[0]
	c.yaw = PI
	var stunned := [false]
	await h.run(g, TestHelpers.seconds(8), func(_i):
		if c.state == "stunned":
			stunned[0] = true
		# 突進が来たら横へダッシュで避ける
		var dodge: bool = c.state == "attack" and c.pos.distance_to(g.player.pos) < 5.0
		return {"move_x": 1.0 if dodge else 0.0, "dash": dodge})
	h.expect(stunned[0], "突撃型はダッシュで避けられると壁に激突して動けなくなる")
	h.free_game(g)


func test_attack_tokens() -> void:
	var g := h.make_game({
		"markers": {"e1": Vector3(-3, 0, 9), "e2": Vector3(0, 0, 9), "e3": Vector3(3, 0, 9), "e4": Vector3(6, 0, 9)},
		"placement": _enemies([
			{"type": "sentry", "at": "e1"}, {"type": "sentry", "at": "e2"},
			{"type": "sentry", "at": "e3"}, {"type": "sentry", "at": "e4"},
		]),
	})
	await h.settle()
	for e in g.enemies:
		e.yaw = PI
	g.god_mode = true
	var max_attackers := [0]
	await h.run(g, TestHelpers.seconds(8), func(_i):
		max_attackers[0] = maxi(max_attackers[0], g.tokens.count())
		return {})
	h.expect(max_attackers[0] <= 2 and max_attackers[0] > 0, "同時に攻撃してくるのは最大 2 体（%d）" % max_attackers[0])
	h.free_game(g)


func test_drill_breaks_wall() -> void:
	var opts := {
		"markers": {"wall": Vector3(0, 0, 1.4)},
		"placement": {"props": [{"type": "breakable", "id": "w1", "at": "wall", "size": [4, 4, 1], "breaksWith": "drill"}]},
	}
	var g1 := h.make_game(opts)
	await h.settle()
	await h.run(g1, TestHelpers.seconds(2), {"special": true})
	h.expect(not g1.breakables[0].broken, "ドリルを持っていなければ壊せない")
	h.free_game(g1)
	var g2 := h.make_game(opts)
	await h.settle()
	g2.give_item("special.drill")
	await h.run(g2, TestHelpers.seconds(2), {"special": true})
	h.expect(g2.breakables[0].broken, "ドリルでひび割れた壁を壊せる")
	h.expect(g2.player.weapon_energy < 100.0, "ドリルはエネルギーを使う")
	h.free_game(g2)


func test_chest() -> void:
	var g := h.make_game({
		"markers": {"c": Vector3(0, 0, 1.2)},
		"placement": {"props": [{"type": "chest", "id": "c1", "at": "c", "contents": {"cells": 200, "item": "chip.charge"}}]},
	})
	await h.settle()
	await h.run(g, 2, {})
	h.expect(g.focus != null and g.focus.id == "c1", "宝箱の前で「調べる」対象になる")
	await h.run(g, 1, {"jump": true})
	h.expect(g.cells == 200, "中身のセルが手に入る")
	h.expect(g.has_item("chip.charge") and g.charge_type(), "中身のチップが手に入り、装着される")
	h.free_game(g)


func test_trigger_event_dialogue() -> void:
	var g := h.make_game({
		"markers": {"t": Vector3(0, 0, 3)},
		"placement": {"triggers": [{"id": "t1", "at": "t", "size": [4, 2, 2], "event": "ev", "once": true}]},
	})
	await h.settle()
	await h.run(g, TestHelpers.seconds(1), {"move_y": 1.0})
	h.expect(g.story.flags.get("x", false), "トリガーに入るとイベントが走る")
	h.expect(g.story.dialogue.get("text", "") == "やあ", "会話が始まる")
	# 決定ボタンで全文表示 → 次へ
	await h.run(g, 2, {"jump": true})
	await h.run(g, 1, {})
	await h.run(g, 2, {"jump": true})
	await h.run(g, 2, {})
	h.expect(g.story.dialogue.is_empty(), "会話が終わる")
	h.expect(g.has_item("special.drill"), "会話の途中でアイテムを受け取る")
	h.free_game(g)


func test_save_restore() -> void:
	var g := h.make_game()
	await h.settle()
	g.give_cells(123)
	g.give_item("special.drill")
	await h.run(g, TestHelpers.seconds(0.5), {"move_y": 1.0})
	var save := g.to_save("test")
	var text := JSON.stringify(save)
	var parsed = GameSim.parse_save(text)
	h.expect(parsed != null, "セーブのデータを読める")
	var g2 := h.make_game({"save": parsed})
	await h.settle()
	h.expect(g2.cells == 123, "セルが戻る")
	h.expect(g2.has_item("special.drill"), "持ち物が戻る")
	h.expect(g2.player.pos.distance_to(g.player.pos) < 0.05, "位置が戻る")
	h.free_game(g)
	h.free_game(g2)


func test_deterministic() -> void:
	var script := func(i: int) -> Dictionary:
		return {"move_y": 1.0, "move_x": sin(i / 20.0), "fire": i % 30 < 10, "lock_on": i > 60}
	var opts := {
		"markers": {"e1": Vector3(0, 0, 12), "e2": Vector3(4, 0, 14)},
		"placement": _enemies([{"type": "sentry", "at": "e1"}, {"type": "charger", "at": "e2"}]),
	}
	var a := h.make_game(opts)
	var b := h.make_game(opts)
	await h.settle()
	for i in TestHelpers.seconds(5):
		await h.tree.physics_frame
		var d: Dictionary = script.call(i)
		a.step(InputFrame.of(d))
		b.step(InputFrame.of(d))
	h.expect(a.player.pos.is_equal_approx(b.player.pos), "同じ入力なら同じ位置（%s / %s）" % [a.player.pos, b.player.pos])
	h.expect(a.enemies.map(func(e): return e.hp) == b.enemies.map(func(e): return e.hp), "同じ入力なら同じ敵の体力")
	h.free_game(a)
	h.free_game(b)
