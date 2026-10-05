extends RefCounted
## ボス「閂」のテスト：始まり、段階の移り変わり、弱点（錠前核）、腕の破壊、攻撃、撃破、やられたらやり直し

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _arena() -> GameSim:
	return h.make_game({"geometry": Arena.geometry(16.0), "placement": Arena.placement("kannuki")})


func _hit(g: GameSim, dmg: float, extra := {}) -> Dictionary:
	var b = g.boss
	var info := {"melee": true, "at": b.axis_center()}
	info.merge(extra, true)
	var before: float = b.hp
	g.damage_enemy(b, dmg, g.player.pos, info)
	return {"dealt": before - b.hp}


func test_boss_setup_and_start() -> void:
	var g := _arena()
	await h.settle()
	h.expect(g.boss is Kannuki and g.boss.alive, "ボスが部屋にいる")
	h.expect(g.boss_status().is_empty(), "戦いが始まる前は体力バーを出さない")
	h.near(g.boss.hp, 1200.0, 0.01, "HP は 1,200")
	h.expect(g.breakables.size() == 4, "壊れる柱が 4 本")
	await h.run(g, TestHelpers.seconds(3), {})
	h.expect(g.boss.state != "idle", "部屋に入ると戦いが始まる（%s）" % g.boss.state)
	var st := g.boss_status()
	h.expect(not st.is_empty() and st.phase == 1 and st.max_hp == 1200.0, "体力バーの情報が出る")
	h.free_game(g)


func test_boss_armor_and_weak_point() -> void:
	var g := _arena()
	await h.settle()
	await h.run(g, TestHelpers.seconds(3), {})
	var b = g.boss
	b.set_state("recover")   # 攻撃の合間（核は閉じている）
	b.core_open = false
	var r := _hit(g, 4.0, {"melee": false})
	h.near(r.dealt, 1.0, 0.01, "核が閉じている間、通常弾は ×0.25")
	r = _hit(g, 10.0)
	h.near(r.dealt, 10.0, 0.01, "光刃は ×1.0")
	b.core_open = true
	r = _hit(g, 10.0, {"melee": false})
	h.near(r.dealt, 15.0, 0.01, "核が開いている間は ×1.5")
	r = _hit(g, 10.0, {"special": true})
	h.near(r.dealt, 20.0, 0.01, "核が開いている間の特殊武器は ×2.0")
	h.free_game(g)


func test_boss_core_exposed_after_wall_thrust() -> void:
	var g := _arena()
	await h.settle()
	g.god_mode = true
	var b = g.boss
	var stuck := [false]
	var opened := [false]
	await h.run(g, TestHelpers.seconds(80), func(_i):
		if b.state == "stuck":
			stuck[0] = true
			opened[0] = opened[0] or b.core_open
		return {})
	h.expect(stuck[0], "削岩突きが壁に刺さって止まる")
	h.expect(opened[0], "壁に刺さると錠前核が露出する")
	h.free_game(g)


func test_boss_phase_transitions() -> void:
	var g := _arena()
	await h.settle()
	g.god_mode = true
	await h.run(g, TestHelpers.seconds(2), {})
	var b = g.boss
	b.core_open = true
	_hit(g, 600.0)
	h.expect(b.hp >= 1200.0 * 0.66 - 0.5, "HP は 66%% の境で止まる（段階を飛ばさない）：%.0f" % b.hp)
	var saw_invuln := [false]
	await h.run(g, TestHelpers.seconds(14), func(_i):
		if b.state == "shift":
			saw_invuln[0] = true
			var before: float = b.hp
			g.damage_enemy(b, 50.0, g.player.pos, {"melee": true, "at": b.axis_center()})
			h.expect(b.hp == before, "段階の変わり目は無敵")
		return {})
	h.expect(b.phase == 2 and saw_invuln[0], "66%% を割ると第 2 段階に移る（%d）" % b.phase)
	h.expect(not b.overheat, "第 2 段階はまだ過熱しない")
	b.core_open = true
	_hit(g, 600.0)
	h.expect(b.hp >= 1200.0 * 0.33 - 0.5, "HP は 33%% の境でも止まる：%.0f" % b.hp)
	await h.run(g, TestHelpers.seconds(14), {})
	h.expect(b.phase == 3 and b.overheat, "33%% を割ると第 3 段階：過熱する（%d）" % b.phase)
	h.free_game(g)


func test_boss_arm_break() -> void:
	var g := _arena()
	await h.settle()
	await h.run(g, TestHelpers.seconds(3), {})
	var b = g.boss
	b.set_state("recover")
	var hp0: float = b.hp
	var n := 0
	while not b.arm_broken["fl"] and n < 20:
		g.damage_enemy(b, 20.0, g.player.pos, {"melee": true, "at": b.arm_center("fl")})
		n += 1
	h.expect(b.arm_broken["fl"] and n <= 6, "削岩腕は個別に壊せる（%d 回）" % n)
	h.expect(b.hp < hp0 and b.hp > hp0 - 100.0, "腕への攻撃は本体にも少し通る（%.0f）" % (hp0 - b.hp))
	h.expect(b.arms_alive() == 3 and not b.arm_broken["fr"], "ほかの腕は無事")
	h.free_game(g)


func test_boss_attacks_hurt_and_vary() -> void:
	var g := _arena()
	await h.settle()
	var b = g.boss
	b.debug_set_phase(1)
	var seen := {}
	var hurt := [0]
	await h.run(g, TestHelpers.seconds(100), func(_i):
		seen[b.state] = true
		if g.player.hp < g.player.max_hp:
			hurt[0] += 1
			g.player.hp = g.player.max_hp
		return {})
	h.expect(hurt[0] > 0, "ボスの攻撃はプレイヤーに当たる")
	var attacks := 0
	for k in ["thrust", "spin", "volley"]:
		if seen.has(k):
			attacks += 1
	h.expect(attacks >= 2, "第 1 段階は 突き・回転・破片 のうち 2 種以上を使う（%s）" % str(seen.keys()))
	h.expect(not seen.has("slam") and not seen.has("summon_windup"), "第 1 段階では叩きつけ・呼び出しを使わない")
	h.free_game(g)


func test_boss_phase2_slam_and_summon() -> void:
	var g := _arena()
	await h.settle()
	g.god_mode = true
	var b = g.boss
	b.debug_set_phase(2)
	var seen := {}
	var sentries := [0]
	await h.run(g, TestHelpers.seconds(120), func(_i):
		seen[b.state] = true
		var n := 0
		for e in g.enemies:
			if e is Sentry and e.alive:
				n += 1
		sentries[0] = maxi(sentries[0], n)
		return {})
	h.expect(seen.has("slam"), "第 2 段階：叩きつけ（%s）" % str(seen.keys()))
	h.expect(seen.has("slam_open"), "叩きつけのあとは核が開く")
	h.expect(sentries[0] >= 2, "第 2 段階：歩哨型を 2 体呼ぶ（%d）" % sentries[0])
	h.free_game(g)


func test_boss_slam_wave_jumpable() -> void:
	var g := _arena()
	await h.settle()
	var b = g.boss
	b.debug_set_phase(2)
	b.pos = Vector3.ZERO
	g.phys.set_feet(b.body, Vector3.ZERO)
	g.player.teleport(Vector3(0, 0, 10), PI)
	b.set_state("slam_windup")
	var hp0: float = g.player.hp
	await h.run(g, TestHelpers.seconds(2.5), {})
	h.expect(g.player.hp < hp0, "地面にいると衝撃波が当たる")
	var g2 := _arena()
	await h.settle()
	var b2 = g2.boss
	b2.debug_set_phase(2)
	b2.pos = Vector3.ZERO
	g2.phys.set_feet(b2.body, Vector3.ZERO)
	g2.player.teleport(Vector3(0, 0, 10), PI)
	b2.set_state("slam_windup")
	var hp1: float = g2.player.hp
	# 波が来るころにジャンプする
	await h.run(g2, TestHelpers.seconds(2.5), func(_i):
		return {"jump": b2.wave_r > 4.0 and b2.wave_r < 9.5})
	h.expect(g2.player.hp >= hp1, "ジャンプで衝撃波を越えられる（%.0f）" % g2.player.hp)
	h.free_game(g)
	h.free_game(g2)


func test_boss_defeat() -> void:
	var g := _arena()
	await h.settle()
	g.god_mode = true
	var b = g.boss
	b.debug_set_phase(3)
	await h.run(g, 30, {})
	b.core_open = true
	g.drain_events()
	var n := 0
	while b.alive and n < 100:
		_hit(g, 50.0)
		n += 1
	h.expect(not b.alive, "核を狙えば倒せる（%d 回）" % n)
	var types := {}
	for e in g.drain_events():
		types[e.type] = true
	h.expect(types.has("bossDefeated"), "撃破の出来事が出る")
	h.expect(g.story.flags.get("ch1.boss_defeated", false), "フラグ ch1.boss_defeated が立つ")
	h.expect(g.boss_status().is_empty(), "撃破後は体力バーを消す")
	h.expect(g.pickups.size() > 5, "閂のコア（セル）を落とす")
	h.free_game(g)


func test_boss_retry_after_player_death() -> void:
	var g := _arena()
	await h.settle()
	await h.run(g, TestHelpers.seconds(3), {})
	var b = g.boss
	b.debug_set_phase(2)
	g.damage_enemy(b, 30.0, g.player.pos, {"melee": true, "at": b.arm_center("fr")})
	g.player.take_damage(9999.0, b.pos, true)
	h.expect(g.player.dead, "やられる")
	await h.run(g, TestHelpers.seconds(2.5), {})
	h.expect(not g.player.dead and g.player.hp == g.player.max_hp, "やられたら再開する")
	h.near(g.player.pos.z, 13.0, 0.5, "部屋の入口から再開")
	h.expect(b.alive and b.phase == 1 and b.hp == b.max_hp and (b.state == "idle" or b.state == "intro"), "ボスは最初からやり直し（%s）" % b.state)
	h.expect(b.arms_alive() == 4, "壊した腕も戻る")
	h.free_game(g)
