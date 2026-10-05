extends RefCounted
## 番機 3 種（子番機・盾型・浮遊型）のテスト：現れる、倒せる（銃・光刃）、攻撃が当たる、型ごとの仕組み

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _one(type: String, at: Vector3, yaw := PI) -> GameSim:
	var g := h.make_game({
		"markers": {"e1": at},
		"placement": {"enemies": [{"type": type, "at": "e1"}]},
	})
	g.enemies[0].yaw = yaw
	return g


# ---------------------------------------------------------------- 子番機

func test_mini_hurts_and_dies_to_gun() -> void:
	var g := _one("mini", Vector3(0, 0, 6))
	await h.settle()
	h.expect(g.enemies[0] is Mini and g.enemies[0].alive, "子番機が現れる")
	var hurt := [false]
	await h.run(g, TestHelpers.seconds(8), func(_i):
		if g.player.hp < g.player.max_hp:
			hurt[0] = true
		return {})
	h.expect(hurt[0], "子番機は跳びついて体当たりしてくる（HP %.0f）" % g.player.hp)
	h.expect(g.player.hp > g.player.max_hp - 30.0, "子番機の体当たりは弱い（残り %.0f）" % g.player.hp)
	h.free_game(g)
	var g2 := _one("mini", Vector3(0, 0, 8))
	await h.settle()
	g2.god_mode = true
	await h.run(g2, TestHelpers.seconds(6), {"lock_on": true, "fire": true})
	h.expect(not g2.enemies[0].alive, "子番機は銃で倒せる")
	h.free_game(g2)


func test_mini_dies_to_blade() -> void:
	var g := _one("mini", Vector3(0, 0, 1.5))
	await h.settle()
	g.god_mode = true
	await h.run(g, TestHelpers.seconds(3), func(i): return {"sword": i % 8 < 2})
	h.expect(not g.enemies[0].alive, "子番機は光刃で倒せる")
	h.free_game(g)


func test_mini_whole_body_weak() -> void:
	var g := _one("mini", Vector3(0, 0, 8))
	await h.settle()
	var r: Dictionary = g.enemies[0].receive(4.0, Vector3.ZERO, {})
	h.expect(r.kind == "weak" and absf(r.dealt - 6.0) < 0.01, "子番機は全身が弱点（×1.5）")
	h.free_game(g)


# ---------------------------------------------------------------- 盾型

func test_shield_multipliers() -> void:
	var g := _one("shield", Vector3(0, 0, 8), 0.0)   # +Z を向く
	await h.settle()
	var s = g.enemies[0]
	var front := Vector3(0, 1, 14)
	var back := Vector3(0, 1, 2)
	var r: Dictionary = s.receive(4.0, front, {})
	h.expect(r.kind == "armor" and absf(r.dealt - 1.0) < 0.01, "正面の通常弾は ×0.25（装甲）：%.2f" % r.dealt)
	r = s.receive(4.0, back, {})
	h.expect(r.kind == "weak" and absf(r.dealt - 6.0) < 0.01, "背面は弱点 ×1.5：%.2f" % r.dealt)
	var guard0: float = s.guard
	r = s.receive(10.0, front, {"melee": true})
	h.expect(absf(r.dealt - 10.0) < 0.01, "正面でも光刃は ×1.0：%.2f" % r.dealt)
	h.expect(s.guard < guard0, "光刃は盾の守りを削る")
	h.free_game(g)


func test_shield_guard_break_and_blade_kill() -> void:
	var g := _one("shield", Vector3(0, 0, 2.2))
	await h.settle()
	g.god_mode = true
	var s = g.enemies[0]
	var broke := [false]
	await h.run(g, TestHelpers.seconds(14), func(i):
		if s.state == "stunned":
			broke[0] = true
		return {"sword": i % 10 < 2})
	h.expect(broke[0], "光刃で盾を崩すと動けなくなる（stunned）")
	h.expect(not s.alive, "光刃で盾型を倒せる（残り %.0f）" % s.hp)
	h.free_game(g)


func test_shield_back_gun_kill() -> void:
	var g := _one("shield", Vector3(0, 0, 8), 0.0)
	await h.settle()
	var s = g.enemies[0]
	var n := 0
	while s.alive and n < 40:
		g.damage_enemy(s, 4.0, Vector3(0, 1, 0), {})   # 背後（原点）から銃
		n += 1
	h.expect(not s.alive and n <= 14, "背面からなら銃で倒せる（%d 発）" % n)
	h.free_game(g)


func test_shield_punch_hurts() -> void:
	var g := _one("shield", Vector3(0, 0, 3.0))
	await h.settle()
	var hurt := [false]
	var first := [0.0]
	await h.run(g, TestHelpers.seconds(6), func(_i):
		if g.player.hp < g.player.max_hp and not hurt[0]:
			hurt[0] = true
			first[0] = g.player.hp
		return {})
	h.expect(hurt[0], "盾型は殴ってくる")
	h.near(first[0], g.player.max_hp - 12.0, 0.1, "殴りは 12 ダメージ")
	h.free_game(g)


func test_shield_turns_slowly() -> void:
	# 回り込めば背後を取れる：向きを変える速さが遅い
	var g := _one("shield", Vector3(0, 0, 6))
	await h.settle()
	g.god_mode = true
	var s = g.enemies[0]
	s.become_alert()
	await h.run(g, 40, {})
	var yaw0: float = s.yaw
	g.player.teleport(Vector3(6, 0, 6), 0.0)
	await h.run(g, 30, {})
	var turned: float = absf(U.wrap_angle(s.yaw - yaw0)) / U.DEG
	h.expect(turned < 70.0, "盾型は 0.5 秒で 70 度までしか向きを変えられない（%.0f 度）" % turned)
	h.free_game(g)


# ---------------------------------------------------------------- 浮遊型

func test_floater_flies_and_shoots() -> void:
	var g := _one("floater", Vector3(0, 0, 10))
	await h.settle()
	var f = g.enemies[0]
	var hurt := [false]
	var max_y := [0.0]
	await h.run(g, TestHelpers.seconds(10), func(_i):
		max_y[0] = maxf(max_y[0], f.pos.y)
		if g.player.hp < g.player.max_hp:
			hurt[0] = true
		return {})
	h.expect(max_y[0] > 1.0, "浮遊型は宙に浮く（高さ %.1f m）" % max_y[0])
	h.expect(hurt[0], "浮遊型は撃ってくる")
	h.expect(g.player.hp >= g.player.max_hp - 18.0, "弾は 6 ダメージ（残り %.0f）" % g.player.hp)
	h.free_game(g)


func test_floater_gun_kill() -> void:
	var g := _one("floater", Vector3(0, 0, 8))
	await h.settle()
	g.god_mode = true
	await h.run(g, TestHelpers.seconds(12), {"lock_on": true, "fire": true})
	h.expect(not g.enemies[0].alive, "浮遊型は銃で撃ち落とせる")
	h.free_game(g)


func test_floater_weak_when_exposed() -> void:
	var g := _one("floater", Vector3(0, 0, 8))
	await h.settle()
	var f = g.enemies[0]
	var r: Dictionary = f.receive(4.0, Vector3(0, 0.5, 0), {})
	h.expect(r.kind == "normal", "浮遊型：ふだんは通常")
	f.set_state("recover")
	r = f.receive(4.0, Vector3(0, 0.5, 0), {})
	h.expect(r.kind == "weak", "浮遊型：降下のあとは上部の核が出て弱点")
	h.free_game(g)
