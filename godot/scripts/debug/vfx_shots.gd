class_name VfxShots
## エフェクト（W2-09）の確認の撮影と、描画の回数の計測。Demo（--demo=<フォルダ>）から使う：
##   --vfx_shots           エフェクトの決まった場面を撮る（vfx_<群>_<場面>.png）。撮るたびに「描画 …」の行を出す
##   --vfx_shots=h         残りの仕上げ（H 群：解析の光の帯・盾の亀裂・フレームの装着・遺物・ノードの記憶・ビーコン・フラッシュの強さ）だけ
##   --vfx_bench=r09,r15,r19,arena  戦闘の重い場面（配管広間・伝導路・ボス部屋・試しの部屋の閂）を数秒ずつ毎こま描いて、描画の回数の最大・平均を出す
## どちらも god_mode で、ゲームの中身には手を加えない（状態を作るのは確認用の関数・敵の状態の書き換えだけ）

static func _draws() -> String:
	return "draw %d・物 %d・三角形 %d" % [RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)]


static func _shot(name: String, extra := {}) -> Dictionary:
	var d := {"ticks": 1, "shot": "vfx_" + name, "input": {}, "after": func(): print("描画 vfx_%s：%s" % [name, _draws()])}
	d.merge(extra, true)
	return d


## 敵を動かない的にする（keep 以外は消す）
static func _targets(g: GameSim, keep: Array) -> void:
	for e in g.enemies:
		if not keep.has(e):
			e.alive = false
			e.dead_time = 99.0
			g.phys.remove(e.body)
		else:
			e.passive = true


## 撮る向き：ハルの向きから off（rad）だけカメラを回す（後ろからでは、ハルの前の光が体に隠れる）
static func _view(d, off: float) -> void:
	var g: GameSim = d.main.game
	g.cam.yaw = g.player.yaw + off
	d.main.snap_views()


static func _place(g: GameSim, e, at: Vector3, face: Vector3) -> void:
	e.pos = at
	e.yaw = U.dir_to_yaw(face.x - at.x, face.z - at.z)
	g.phys.set_feet(e.body, at)


static func steps(d) -> Array:
	var m = d.main
	# --vfx_shots=h：残りの仕上げ（H 群）だけを撮る
	if String(m.args.get("vfx_shots", "")) == "h":
		return leftover_steps(d)
	# --vfx_shots=machines：番機 5 種と閂の見た目だけ（W2_番機3D化の結果.md の 3e。前後の比べ）
	if String(m.args.get("vfx_shots", "")) == "machines":
		return machine_steps(d)
	var s := []
	# ---- A：主武器（連射・溜め・弱点・装甲）
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("sentry")
			var g: GameSim = m.game
			var e = g.enemies[0]
			_targets(g, [e])
			_place(g, e, Vector3(0, 0, 5), Vector3(0, 0, 10))
			d._stand(Vector3(0, 0, 10), Vector3(0, 0, 5))
			_view(d, 0.75)},
		{"ticks": 30, "input": {}},
		{"ticks": 3, "input": {"fire": true}},
		_shot("a1_rapid_muzzle", {"input": {"fire": true}}),
		{"ticks": 6, "input": {"fire": true}},
		_shot("a2_rapid_hit", {"input": {"fire": true}}),
		{"ticks": 40, "input": {}, "setup": func():
			m.game.items["chip.charge"] = true
			m.game.equipped_chips["chip.charge"] = true},
		{"ticks": 45, "input": {"fire": true}},
		_shot("a3_charge_lv1", {"input": {"fire": true}}),
		{"ticks": 35, "input": {"fire": true}},
		_shot("a4_charge_lv2", {"input": {"fire": true}}),
		{"ticks": 4, "input": {}},
		_shot("a5_charge_bolt"),
		{"ticks": 6, "input": {}},
		_shot("a6_charge_hit"),
		# 背中の弱点・正面の装甲（盾型）を撃つ
		{"ticks": 2, "setup": func():
			var g: GameSim = m.game
			g.equipped_chips.erase("chip.charge")
			var e = g.enemies[0]
			_place(g, e, Vector3(0, 0, 5), Vector3(0, 0, -6))
			d._stand(Vector3(0, 0, 10), Vector3(0, 0, 5))
			_view(d, 0.75)},
		{"ticks": 20, "input": {}},
		{"ticks": 10, "input": {"fire": true}},
		_shot("a7_weak_hit", {"input": {"fire": true}}),
	])
	# ---- B：光刃（3 段・空中・ダッシュ斬り・踏み込み・溜め）
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("sentry")
			var g: GameSim = m.game
			var e = g.enemies[0]
			_targets(g, [e])
			_place(g, e, Vector3(0, 0, 4), Vector3(0, 0, 9))
			e.hp = 9999.0
			e.max_hp = 9999.0
			d._stand(Vector3(0, 0, 6.2), Vector3(0, 0, 4))
			_view(d, 1.0)},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "input": {"sword": true}},
		{"ticks": 5, "input": {}},
		_shot("b1_combo1"),
		{"ticks": 16, "input_fn": func(i): return {"sword": i % 8 == 0}},
		{"ticks": 1, "input": {"sword": true}},
		{"ticks": 7, "input": {}},
		_shot("b2_combo2"),
		{"ticks": 14, "input_fn": func(i): return {"sword": i == 2}},
		{"ticks": 9, "input": {}},
		_shot("b3_combo3"),
		{"ticks": 40, "input": {}, "setup": func():
			d._stand(Vector3(0, 0, 8.0), Vector3(0, 0, 4))
			_view(d, 1.1)},
		{"ticks": 1, "input": {"jump": true}},
		{"ticks": 14, "input": {"jump": true}},
		{"ticks": 1, "input": {"sword": true}},
		{"ticks": 9, "input": {}},
		_shot("b4_air"),
		{"ticks": 60, "input": {}, "setup": func():
			d._stand(Vector3(0, 0, 9.0), Vector3(0, 0, 4))
			_view(d, 1.3)},
		{"ticks": 1, "input": {"dash": true, "move_y": 1.0}},
		{"ticks": 3, "input": {"move_y": 1.0}},
		{"ticks": 1, "input": {"sword": true}},
		{"ticks": 10, "input": {}},
		_shot("b5_dash_slash"),
		{"ticks": 40, "input": {}, "setup": func():
			d._stand(Vector3(0, 0, 9.0), Vector3(0, 0, 4))
			_view(d, 1.2)},
		{"ticks": 20, "input": {"lock_on": true}},
		{"ticks": 1, "input": {"lock_on": true, "sword": true}},
		{"ticks": 3, "input": {"lock_on": true}},
		_shot("b6_lunge_approach", {"input": {"lock_on": true}}),
		{"ticks": 30, "input": {}},
		{"ticks": 2, "setup": func():
			d._stand(Vector3(0, 0, 10.0), Vector3(0, 0, 4))
			_view(d, 1.0)},
		{"ticks": 30, "input": {"sword": true}},
		_shot("b7_blade_charge_low", {"input": {"sword": true}}),
		{"ticks": 25, "input": {"sword": true}},
		_shot("b8_blade_charge_full", {"input": {"sword": true}}),
		{"ticks": 9, "input": {}},
		_shot("b9_charge_slash"),
		{"ticks": 9, "input": {}},
		_shot("b10_charge_wave"),
	])
	# ---- C：ドリル・壁・ダッシュ・被弾・回復
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("sentry")
			var g: GameSim = m.game
			var e = g.enemies[0]
			_targets(g, [e])
			g.items["special.drill"] = true
			_place(g, e, Vector3(0, 0, 4), Vector3(0, 0, 9))
			e.hp = 9999.0
			d._stand(Vector3(0, 0, 5.5), Vector3(0, 0, 4))
			_view(d, 1.2)},
		{"ticks": 30, "input": {}},
		{"ticks": 18, "input": {"special": true}},
		_shot("c1_drill", {"input": {"special": true}}),
		{"ticks": 2, "setup": func():
			d._arena_start("kannuki")
			var g: GameSim = m.game
			g.boss.passive = true
			g.items["special.drill"] = true
			var b = g.breakables[0]
			var c: Vector3 = b.center
			var away := Vector3(c.x, 0, c.z).normalized()
			d._stand(Vector3(c.x, 0, c.z) - away * 1.9, Vector3(c.x, 0, c.z))
			_view(d, 1.25)},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "input": {"fire": true}},
		{"ticks": 5, "input": {}},
		_shot("c2a_mark_wrong"),
		{"ticks": 30, "input": {"special": true}},
		_shot("c2_drill_wall", {"input": {"special": true}}),
		{"ticks": 1, "input": {"special": true}, "setup": func():
			var b = m.game.breakables[0]
			b.progress = maxf(b.progress, b.toughness - 0.12)},
		{"ticks": 12, "input_fn": func(_i): return {"special": not m.game.breakables[0].broken}},
		_shot("c3_wall_break", {"check": func(): return d._check(m.game.breakables[0].broken, "ドリルで柱を壊せる（エフェクトの確認）")}),
		{"ticks": 24, "input": {}},
		_shot("c4_wall_break_late"),
		{"ticks": 2, "setup": func():
			d._arena_start("sentry")
			var g: GameSim = m.game
			_targets(g, [])
			d._stand(Vector3(-4, 0, 2), Vector3(4, 0, 2))
			_view(d, 1.57)},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "input": {"dash": true, "move_y": 1.0}},
		{"ticks": 2, "input": {"move_y": 1.0}},
		_shot("c5_dash_start", {"input": {"move_y": 1.0}}),
		{"ticks": 5, "input": {"move_y": 1.0}},
		_shot("c6_dash_trail", {"input": {"move_y": 1.0}}),
		{"ticks": 40, "input": {}, "setup": func():
			d._stand(Vector3(0, 0, 2), Vector3(0, 0, -6))
			_view(d, 1.1)},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			g.god_mode = false
			g.player.take_damage(6.0, g.player.pos + U.yaw_to_dir(g.player.yaw) * 3.0 + Vector3(0, 1, 0), false)
			g.god_mode = true},
		{"ticks": 3, "input": {}},
		_shot("c7_hurt"),
		{"ticks": 20, "input": {}},
		_shot("c8_hurt_blink"),
		{"ticks": 60, "input": {}, "setup": func():
			var g: GameSim = m.game
			g.god_mode = false
			g.player.take_damage(20.0, g.player.pos + U.yaw_to_dir(g.player.yaw) * 3.0, true)
			g.god_mode = true},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			g.player.heals = 2
			g.player.hp = 40.0},
		{"ticks": 1, "input": {"heal": true}},
		{"ticks": 20, "input": {}},
		_shot("c9_heal"),
	])
	# ---- D：番機（警戒・予兆・弾・激突・盾・撃破・命中の 3 種）
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("sentry")
			var g: GameSim = m.game
			for i in 3:
				var e = g.enemies[i]
				_place(g, e, Vector3(-2.5 + 2.5 * i, 0, 4.0 + absf(i - 1) * 0.8), Vector3(0, 0, 11))
				e.passive = true
			d._stand(Vector3(0, 0, 10), Vector3(0, 0, 4))
			_view(d, 0.45)},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func():
			for e in m.game.enemies:
				e.passive = false
				e.become_alert()},
		{"ticks": 8, "input": {}},
		_shot("d1_alert"),
		{"ticks": 1, "input": {}, "setup": func():
			for e in m.game.enemies:
				e.set_state("windup")},
		{"ticks": 22, "input": {}},
		_shot("d2_windup"),
		{"ticks": 14, "input": {}},
		_shot("d3_banki_shot"),
		{"ticks": 10, "input": {}},
		_shot("d4_banki_shot_impact"),
		{"ticks": 2, "setup": func():
			d._arena_start("charger")
			var g: GameSim = m.game
			var e = g.enemies[0]
			_targets(g, [e])
			e.passive = false
			_place(g, e, Vector3(-9, 0, 0), Vector3(-16, 0, 0))
			e._charge_dir = Vector3(-1, 0, 0)
			e.set_state("attack")
			d._stand(Vector3(-10.5, 0, 3.5), Vector3(-15.5, 0, -0.5))},
		{"ticks": 40, "input_fn": func(_i): return {}},
		{"ticks": 1, "input": {}, "check": func(): return d._check(m.game.enemies[0].state == "stunned", "突撃型が壁に激突して動けない（エフェクトの確認）")},
		_shot("d5_crash"),
		{"ticks": 40, "input": {}},
		_shot("d6_stunned"),
		{"ticks": 2, "setup": func():
			d._arena_start("shield")
			var g: GameSim = m.game
			var e = g.enemies[1]
			_targets(g, [e])
			_place(g, e, Vector3(0, 0, 3), Vector3(0, 0, 9))
			d._stand(Vector3(0, 0, 6.5), Vector3(0, 0, 3))
			_view(d, 0.9)},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			var e = g.enemies[1]
			g.damage_enemy(e, 41.0, g.player.pos, {"melee": true, "at": e.center() + e.forward() * 0.6})},
		{"ticks": 5, "input": {}},
		_shot("d7_shield_break"),
		{"ticks": 2, "setup": func():
			d._arena_start("sentry")
			var g: GameSim = m.game
			for i in 3:
				var e = g.enemies[i]
				e.passive = true
				_place(g, e, Vector3(-2.0 + 2.0 * i, 0, 4.5), Vector3(0, 0, 10) if i != 1 else Vector3(0, 0, -6))
			d._stand(Vector3(0, 0, 9), Vector3(0, 0, 4.5))
			_view(d, 0.35)},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			var es: Array = g.enemies
			g.emit_event({"type": "hit", "at": es[0].center() + Vector3(0, 0, 0.4), "kind": "normal"})
			g.emit_event({"type": "hit", "at": es[1].center() + Vector3(0, 0, 0.4), "kind": "weak"})
			g.emit_event({"type": "hit", "at": es[2].center() + Vector3(0, 0, 0.4), "kind": "armor"})},
		{"ticks": 3, "input": {}},
		_shot("d8_hits_normal_weak_armor"),
		{"ticks": 20, "input": {}, "setup": func():
			var g: GameSim = m.game
			g.damage_enemy(g.enemies[1], 999.0, g.player.pos, {})},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			g.damage_enemy(g.enemies[0], 999.0, g.player.pos, {})},
		{"ticks": 4, "input": {}},
		_shot("d9_destroy"),
		{"ticks": 30, "input": {}},
		_shot("d10_destroy_late"),
	])
	# ---- E：閂
	var boss_start := func(phase: int, st: String, at := Vector3(0, 0, -3), stand := Vector3(0, 0, 12)):
		var g: GameSim = m.game
		var b = g.boss
		b.debug_set_phase(phase)
		b.pos = at
		b.yaw = U.dir_to_yaw(stand.x - at.x, stand.z - at.z)
		g.phys.set_feet(b.body, at)
		b.spin_r = 0.0
		b.lane = false
		b.wave_r = -1.0
		b.core_open = false
		b.set_state(st)
		d._stand(stand, at)
		_view(d, 0.3)
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("kannuki")
			# 柱は撮る向きをふさぐので、壊れたことにして隠す（出来事は出さない）
			var g: GameSim = m.game
			for b in g.breakables:
				b.broken = true
				g.phys.remove(b.body)
				b.body = null},
		{"ticks": 150, "input": {}},
		{"ticks": 2, "setup": func(): boss_start.call(1, "thrust_windup", Vector3(0, 0, -8), Vector3(0, 0, 10))},
		{"ticks": 34, "input": {}},
		_shot("e1_thrust_windup"),
		{"ticks": 20, "input": {}},
		_shot("e2_thrust"),
		{"ticks": 2, "setup": func():
			d._stand(Vector3(-7, 0, 6), Vector3(0, 0, 12))
			_view(d, 0.0)},
		{"ticks": 60, "input_fn": func(_i): return {}},
		_shot("e3_stuck_core"),
		{"ticks": 2, "setup": func(): boss_start.call(1, "spin_windup", Vector3(0, 0, -3), Vector3(0, 0, 9))},
		{"ticks": 34, "input": {}},
		_shot("e4_spin_windup"),
		{"ticks": 30, "input": {}},
		_shot("e5_spin"),
		{"ticks": 2, "setup": func(): boss_start.call(1, "volley_windup", Vector3(0, 0, -6), Vector3(3, 0, 8))},
		{"ticks": 24, "input": {}},
		_shot("e6_debris_windup"),
		{"ticks": 30, "input": {}},
		_shot("e7_debris"),
		{"ticks": 2, "setup": func(): boss_start.call(2, "slam_windup", Vector3(0, 0, -2), Vector3(0, 0, 10))},
		{"ticks": 40, "input": {}},
		_shot("e8_slam_windup"),
		{"ticks": 20, "input": {}},
		_shot("e9_slam_impact"),
		{"ticks": 34, "input": {}},
		_shot("e10_slam_ring"),
		{"ticks": 2, "setup": func(): boss_start.call(2, "summon_windup", Vector3(0, 0, -2), Vector3(0, 0, 10))},
		{"ticks": 40, "input": {}},
		_shot("e11_summon_windup"),
		{"ticks": 40, "input": {}},
		_shot("e12_summon_hatch"),
		{"ticks": 2, "setup": func():
			boss_start.call(3, "recover", Vector3(0, 0, -2), Vector3(0, 0, 9))
			for e in m.game.enemies:
				if e != m.game.boss:
					e.alive = false
			m.game.boss.heat_state = 1
			m.game.boss.heat_time = 0.0},
		{"ticks": 30, "input": {}},
		_shot("e13_overheat_warn"),
		{"ticks": 2, "setup": func():
			m.game.boss.heat_state = 2
			m.game.boss.heat_time = 0.0},
		{"ticks": 50, "input": {}},
		_shot("e14_overheat_hot"),
		{"ticks": 2, "setup": func():
			boss_start.call(2, "recover", Vector3(0, 0, -2), Vector3(-2, 0, 9))
			m.game.boss.heat_state = 0
			m.game.boss.overheat = false},
		{"ticks": 10, "input": {}},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			var b = g.boss
			g.damage_enemy(b, 200.0, g.player.pos, {"melee": true, "at": b.arm_center("fr")})},
		{"ticks": 5, "input": {}},
		_shot("e15_arm_break"),
		{"ticks": 45, "input": {}},
		_shot("e16_arm_smoke"),
		{"ticks": 2, "setup": func():
			var g: GameSim = m.game
			var b = g.boss
			b.debug_set_phase(3)
			b.core_open = true
			var guard := 0
			while b.alive and guard < 100:
				g.damage_enemy(b, 60.0, g.player.pos, {"melee": true, "at": b.axis_center()})
				guard += 1},
		{"ticks": 20, "input": {}},
		_shot("e17_destroy_open"),
		{"ticks": 45, "input": {}},
		_shot("e18_destroy_collapse"),
		{"ticks": 70, "input": {}},
		_shot("e19_destroy_core"),
	])
	# ---- F：拾い物・解析・フレームの装着（解析の相手は大きな閂。小さな番機はロックオンのカメラでハルの陰に入る）
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("kannuki")
			var g: GameSim = m.game
			g.boss.passive = true
			for b in g.breakables:
				b.broken = true
				g.phys.remove(b.body)
				b.body = null
			d._stand(Vector3(0, 0, 9), Vector3(0, 0, -10))
			_view(d, 0.5)},
		{"ticks": 20, "input": {}},
		{"ticks": 30, "input": {"lock_on": true}},
		_shot("f1_scan", {"input": {"lock_on": true}}),
		{"ticks": 70, "input": {"lock_on": true}},
		_shot("f2_scan_done", {"input": {"lock_on": true}}),
		{"ticks": 2, "setup": func():
			var g: GameSim = m.game
			for i in 6:
				g.spawn_pickup("cells" if i % 3 else ("energy" if i == 0 else "repair"), 3, g.player.pos + U.yaw_to_dir(g.player.yaw) * 3.0 + Vector3(0, 0.5, 0))},
		{"ticks": 34, "input": {}},
		_shot("f3_pickup"),
		{"ticks": 2, "setup": func():
			d._stand(Vector3(0, 0, 9), Vector3(0, 0, 4.5))
			_view(d, 2.6)
			m.fx._frame_fit(m.game.player, "arm")},
		{"ticks": 20, "input": {}},
		_shot("f4_frame_fit_gather"),
		{"ticks": 30, "input": {}},
		_shot("f5_frame_fit_done"),
	])
	# ---- G：宝箱・ビーコン・封印（見本の部屋 sample.hub）
	s.append_array([
		{"ticks": 2, "setup": func():
			m.arena_kind = ""
			m.args["room"] = "sample.hub"
			m.start_game(null)
			m.game.god_mode = true
			d._stand(Vector3(-8, 0, 6.4), Vector3(-8, 0, 8))
			_view(d, 0.6)},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "input": {"jump": true}},
		{"ticks": 14, "input": {}},
		_shot("g1_chest", {"check": func(): return d._check(m.game.chests.any(func(c): return c.opened), "宝箱が開く（エフェクトの確認）")}),
		{"ticks": 40, "input": {}, "setup": func():
			d._stand(Vector3(-4, 0, -7.2), Vector3(-4, 0, -9))
			_view(d, 0.7)},
		{"ticks": 1, "input": {"jump": true}},
		{"ticks": 30, "input": {}},
		_shot("g2_beacon"),
		{"ticks": 2, "setup": func():
			# 扉の前（部屋の中の側：ハルの今いる側）に立つ
			var dr = m.game.doors[0]
			var f := U.yaw_to_dir(dr.yaw)
			var here: Vector3 = m.game.player.pos
			var at: Vector3 = dr.pos + f * 3.5 if (dr.pos + f * 3.5).distance_to(here) < (dr.pos - f * 3.5).distance_to(here) else dr.pos - f * 3.5
			d._stand(Vector3(at.x, dr.pos.y, at.z), dr.pos)
			_view(d, 0.4)
			m.fx._seal_open(dr)},
		{"ticks": 30, "input": {}},
		_shot("g3_seal_open"),
	])
	s.append_array(leftover_steps(d))
	return s


# ---------------------------------------------------------------- H 群：残りの仕上げ

## 撮る直前にカメラを置く（ゲームのカメラは次の刻みで戻る）
static func _cam_at(d, at: Vector3, look: Vector3) -> void:
	var c: Camera3D = d.main.camera
	c.global_position = at
	c.look_at(look, Vector3.UP)
	c.reset_physics_interpolation()


## 第 1 章の部屋から、フラグを立てて始める（イベントの途中の場面を撮るため）。quiet：部屋のトリガーを走らせない
## （フラグは部屋を作ったあとに立つので、trigger.<id> のフラグでは止まらない）・敵を消す
static func _room_start(d, room: String, flags: String, quiet := false) -> void:
	var m = d.main
	m.arena_kind = ""
	m.args["room"] = room
	m.args["flags"] = flags
	m.start_game(null)
	m.args.erase("flags")
	m.game.god_mode = true
	if quiet:
		for t in m.game.triggers:
			t.fired = true
		_targets(m.game, [])


## 会話 id が出て、閉じたあとに真になる条件
static func _after_dialogue(d, id: String) -> Callable:
	var st := {"seen": false}
	return func() -> bool:
		var dl: Dictionary = d.main.game.story.dialogue
		if String(dl.get("id", "")) == id:
			st.seen = true
		return st.seen and String(dl.get("id", "")) != id


## 盾型（試しの部屋の盾型の組の 2 体目）の盾を光刃で削る（守り 40 から amount 減る。崩れはしない）
static func _chip(g: GameSim, amount: float) -> void:
	var e = g.enemies[1]
	g.damage_enemy(e, amount, g.player.pos, {"melee": true, "at": e.center() + e.forward() * 0.6})


## cond が真になった刻みから、offsets（刻み）ごとに撮る（vfx_<names>）。真になるまでは会話を決定で送る（台本のイベントを進める）。
## 撮り終えたら次の手順へ。max_ticks までに真にならなければ ✗
static func _shots_after(d, what: String, cond: Callable, offsets: Array, names: Array, max_ticks := 3600) -> Dictionary:
	var st := {"t0": -1}
	var fn := func(i: int) -> Dictionary:
		var g: GameSim = d.main.game
		if st.t0 < 0:
			if not cond.call():
				if i == max_ticks - 1:
					d._check(false, "%s：撮る場面にならなかった" % what)
				return {"jump": g.story.blocking() and (i % 6) < 3}
			st.t0 = i
			d._check(true, what)
		var k: int = i - st.t0
		if offsets.has(k - 1):
			print("描画 vfx_%s：%s" % [names[offsets.find(k - 1)], _draws()])
		if offsets.has(k):
			d._pending_shot = "vfx_" + String(names[offsets.find(k)])
		if k > int(offsets[-1]):
			d._tick = max_ticks
		return {}
	return {"ticks": max_ticks, "input_fn": fn}


## H 群：W2-09 の残りの仕上げ（docs/art_orders/W2_エフェクトの結果.md 4 章）。前と後を同じ手順で撮って並べる
static func leftover_steps(d) -> Array:
	var m = d.main
	var s := []
	# ---- 解析の光の帯：ナゴミの目から相手へ（横から撮る）
	var side_cam := func(): _cam_at(d, Vector3(5.4, 2.1, 9.8), Vector3(0, 0.95, 7.5))
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("sentry")
			var g: GameSim = m.game
			var e = g.enemies[0]
			_targets(g, [e])
			_place(g, e, Vector3(0, 0, 5.4), Vector3(0, 0, 10))
			d._stand(Vector3(0, 0, 10), Vector3(0, 0, 5.4))},
		{"ticks": 30, "input": {}},
		{"ticks": 36, "input": {"lock_on": true}},
		_shot("h01_scan_beam", {"input": {"lock_on": true}, "cam": side_cam}),
		{"ticks": 55, "input": {"lock_on": true}},
		_shot("h02_scan_done", {"input": {"lock_on": true}, "cam": side_cam}),
	])
	# ---- 盾の亀裂：光刃で守りを削っている間（亀裂 0.25）。盾は前と外へ向けて斜めに構えているので、表を斜め前から
	var shield_cam := func(): _cam_at(d, Vector3(2.9, 1.8, 6.2), Vector3(0.55, 1.05, 3.15))
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("shield")
			var g: GameSim = m.game
			var e = g.enemies[1]
			_targets(g, [e])
			_place(g, e, Vector3(0, 0, 3), Vector3(0, 0, 9))
			d._stand(Vector3(0.3, 0, 5.4), Vector3(0.3, 0, 3))},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func(): _chip(m.game, 12.0)},
		{"ticks": 6, "input": {}},
		_shot("h03_shield_chip", {"cam": shield_cam}),
		{"ticks": 1, "input": {}, "setup": func(): _chip(m.game, 16.0)},
		{"ticks": 40, "input": {}},
		_shot("h04_shield_cracked", {"cam": shield_cam}),
	])
	# ---- フレームの装着（台本のカメラと時間のまま。会話は決定で送る）
	# 封印室の適合（胴）：入口から歩いてきてトリガーに入った所
	s.append_array([
		{"ticks": 2, "setup": func():
			_room_start(d, "ch1.r08", "ch1.got_spark,ch1.fell_to_b2")
			d._stand(Vector3(0, 0, -6.5), Vector3(0, 0, 0))},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func(): d._stand(Vector3(0, 0, -5.4), Vector3(0, 0, 0))},
		_shots_after(d, "封印室で適合のフラグが立つ（エフェクトの確認）", func(): return m.game.flag("ch1.frame_fitted"),
			[12, 36, 66, 100], ["h05_fit_02", "h06_fit_06", "h07_fit_11", "h08_fit_17"]),
	])
	# 弁の間の籠手（腕）
	s.append_array([
		{"ticks": 2, "setup": func():
			_room_start(d, "ch1.r10", "ch1.got_spark,ch1.fell_to_b2,ch1.frame_fitted")
			_targets(m.game, [])
			d._stand(Vector3(0, 0, -9.5), Vector3(0, 0, 0))},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func(): d._stand(Vector3(0, 0, -7.0), Vector3(0, 0, 0))},
		_shots_after(d, "弁の間で籠手が目覚める（エフェクトの確認）", func(): return m.game.flag("ch1.blade_online"),
			[12, 40, 70], ["h09_arm_02", "h10_arm_07", "h11_arm_12"]),
	])
	# 駆動回廊の脚：動力が通った瞬間（カメラはピストンへ）と、ナゴミの「動力の伝達を確認」のあと
	s.append_array([
		{"ticks": 2, "setup": func():
			_room_start(d, "ch1.r12", "ch1.got_spark,ch1.fell_to_b2,ch1.frame_fitted,ch1.blade_online,ch1.first_beacon")
			for t in m.game.triggers:
				if t.id == "ch1.r12.enter":
					t.fired = true
			_targets(m.game, [])
			d._stand(Vector3(0, 0, -14.5), Vector3(0, 0, -5))},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func():
			m.game.set_flag("switch.ch1.r12.s1")
			m.game.set_flag("switch.ch1.r12.s2")},
		_shots_after(d, "駆動回廊に動力が通る（エフェクトの確認）", func(): return m.game.flag("ch1.drive_powered"),
			[18], ["h12_legs_power_03"]),
		_shots_after(d, "ナゴミの「動力の伝達を確認」が終わる（エフェクトの確認）", _after_dialogue(d, "ch1.r12.powered"),
			[18, 48, 78], ["h13_legs_03", "h14_legs_08", "h15_legs_13"]),
	])
	# ---- 遺物：開ける前の宝箱の縁と目印、開けて遺物を拾う（弁の間の宝箱）
	s.append_array([
		{"ticks": 2, "setup": func():
			_room_start(d, "ch1.r10", "ch1.got_spark,ch1.fell_to_b2,ch1.frame_fitted,ch1.blade_online", true)
			d._stand(Vector3(6.3, 0, -6.3), Vector3(9, 0, -9))
			_view(d, 0.5)},
		{"ticks": 30, "input": {}},
		_shot("h16_chest_idle"),
		{"ticks": 2, "setup": func():
			d._stand(Vector3(8.0, 0, -8.0), Vector3(9, 0, -9))
			_view(d, 0.75)},
		{"ticks": 10, "input": {}},
		{"ticks": 1, "input": {"jump": true}},
		{"ticks": 11, "input": {}},
		_shot("h17_relic_02", {"check": func(): return d._check(m.game.relics.size() > 0, "宝箱から遺物を拾う（エフェクトの確認）")}),
		{"ticks": 15, "input": {}},
		_shot("h18_relic_045"),
		{"ticks": 20, "input": {}},
		_shot("h19_relic_08"),
	])
	# ---- 置いてある遺物の目印と、拾ったとき（ジャンク溜まりの台の上）
	s.append_array([
		{"ticks": 2, "setup": func():
			_room_start(d, "ch1.r02", "ch1.got_spark", true)
			d._stand(Vector3(2.6, 0, 0.6), Vector3(7.2, 0, 5.2))
			_view(d, 0.3)},
		{"ticks": 30, "input": {}},
		_shot("h20_relic_loot_idle"),
		{"ticks": 2, "setup": func():
			d._stand(Vector3(7.2, 1.8, 4.5), Vector3(7.2, 1.8, 6.0))
			_view(d, 0.9)},
		{"ticks": 16, "input": {}},
		_shot("h21_relic_loot_taken", {"check": func(): return d._check(m.game.relics.size() > 0, "置いてある遺物を拾う（エフェクトの確認）")}),
	])
	# ---- ノードの記憶：炉心の再始動のイベント（台本のカメラと時間のまま）
	s.append_array([
		{"ticks": 2, "setup": func():
			_room_start(d, "ch1.r20", "ch1.got_spark,ch1.fell_to_b2,ch1.frame_fitted,ch1.blade_online,ch1.first_beacon,ch1.drive_powered,ch1.shortcut_open,ch1.diagnosis,ch1.boss_defeated,ch1.night")
			d._stand(Vector3(0, 0, -8), Vector3(0, 0, 2))},
		{"ticks": 20, "input": {}},
		# 入口から歩いてくると、トリガーの手前の柱（中央、z −6.5〜−5.5）の脇を通ってトリガーに入る
		{"ticks": 1, "input": {}, "setup": func(): d._stand(Vector3(0.9, 0, -6.3), Vector3(0.9, 0, 2))},
		_shots_after(d, "炉心で「ch1.node」の会話が始まる（エフェクトの確認）", func(): return String(m.game.story.dialogue.get("id", "")) == "ch1.node",
			[10, 40, 72], ["h22_node_02", "h23_node_07", "h24_node_12"]),
	])
	# ---- ビーコンの定常の光（心臓部前室）
	s.append_array([
		{"ticks": 2, "setup": func():
			_room_start(d, "ch1.r18", "ch1.got_spark,ch1.fell_to_b2,ch1.frame_fitted,ch1.blade_online,ch1.first_beacon,ch1.drive_powered,ch1.shortcut_open", true)
			d._stand(Vector3(1.0, 0, -3.0), Vector3(-5, 0, 3))
			_view(d, 0.35)},
		{"ticks": 30, "input": {}},
		_shot("h25_beacon_steady"),
		_shot("h26_beacon_steady_far", {"cam": func(): _cam_at(d, Vector3(6.5, 3.4, -9.5), Vector3(-5, 4.2, 3))}),
	])
	# ---- フラッシュの強さ（標準・弱め・最小）：閂の鼻先の弱点の命中と体の被弾の光、被弾（画面の赤）、突きが壁に刺さった衝突の光
	for fl in PadConfig.FLASH_STEPS:
		var tag: String = {1.0: "std", 0.5: "half", 0.2: "min"}[fl]
		s.append_array([
			{"ticks": 2, "setup": func():
				PadConfig.flash = fl
				d._arena_start("kannuki")
				var g: GameSim = m.game
				g.boss.passive = true
				for b in g.breakables:
					b.broken = true
					g.phys.remove(b.body)
					b.body = null},
			{"ticks": 150, "input": {}},
			{"ticks": 2, "setup": func():
				var g: GameSim = m.game
				var bs = g.boss
				bs.debug_set_phase(2)
				bs.pos = Vector3(0, 0, -2)
				bs.yaw = U.dir_to_yaw(-2.0, 11.0)
				g.phys.set_feet(bs.body, bs.pos)
				bs.set_state("recover")
				d._stand(Vector3(-2, 0, 9), Vector3(0, 0, -2))
				_view(d, 0.3)},
			{"ticks": 10, "input": {}},
			{"ticks": 1, "input": {}, "setup": func():
				var g: GameSim = m.game
				var bs = g.boss
				var nose: Vector3 = bs.axis_center() + bs.forward() * (float(g.tuning.boss.bodyHalfLen) + 0.4)
				g.emit_event({"type": "hit", "at": nose, "kind": "weak"})
				g.damage_enemy(bs, 4.0, g.player.pos, {})},
			{"ticks": 2, "input": {}},
			_shot("h27_flash_%s_hit" % tag),
			{"ticks": 40, "input": {}},
			{"ticks": 1, "input": {}, "setup": func():
				var g: GameSim = m.game
				g.god_mode = false
				g.player.take_damage(6.0, g.player.pos + U.yaw_to_dir(g.player.yaw) * 3.0 + Vector3(0, 1, 0), false)
				g.god_mode = true},
			{"ticks": 2, "input": {}},
			_shot("h28_flash_%s_hurt" % tag),
			{"ticks": 40, "input": {}},
			{"ticks": 1, "input": {}, "setup": func():
				var g: GameSim = m.game
				var bs = g.boss
				g.emit_event({"type": "bossStuck", "at": bs.axis_center() + bs.forward() * (float(g.tuning.boss.bodyHalfLen) + 0.4)})},
			{"ticks": 2, "input": {}},
			_shot("h29_flash_%s_crash" % tag),
		])
	s.append({"ticks": 1, "setup": func(): PadConfig.flash = 1.0})
	# ---- 設定の画面：フラッシュの強さの行を選んだところ（スマホの寸法の画面では、画面の操作（タッチ）の見た目で）
	s.append(_shot("h30_settings_flash", {"setup": func():
		if m.get_window().size.y < 500:
			m.touch.activate()
		m.pause()
		m.menu.show_controls(func(): m.resume(), PadConfig.ACTIONS.size() + 4),
		"after": func(): m.resume()}))
	s.append({"ticks": 2, "input": {}})
	return s


# ---------------------------------------------------------------- 描画の回数の計測

## 戦闘の重い場面を毎こま描いて、描画の回数を数える。name：r09 | r15 | r19 | arena
static func bench_steps(d, names: Array) -> Array:
	var m = d.main
	var s := []
	for nm in names:
		var stats := {"draws": [], "objs": [], "phys": []}
		var room: String = {"r09": "ch1.r09", "r15": "ch1.r15", "r19": "ch1.r19"}.get(nm, "")
		var flags: String = {"r09": "ch1.frame_fitted", "r15": "ch1.drive_powered", "r19": "ch1.diagnosis"}.get(nm, "")
		s.append({"ticks": 2, "setup": func():
			if room == "":
				d._arena_start("kannuki")
			else:
				m.arena_kind = ""
				m.args["room"] = room
				m.args["flags"] = flags
				m.start_game(null)
				m.game.god_mode = true})
		# 会話・導入を送る
		s.append({"ticks": 240, "input_fn": func(i): return {"jump": (i % 6) < 3 and m.game.story.blocking()}})
		s.append({"ticks": 2, "setup": func():
			var g: GameSim = m.game
			if nm == "r19" or nm == "arena":
				d._stand(Vector3(0, 0, 6), Vector3(0, 0, -6))
			for e in g.enemies:
				if e.alive and e.state == "idle":
					e.become_alert()})
		s.append({"ticks": 60, "input_fn": func(i): return {"jump": (i % 6) < 3 and m.game.story.blocking()}})
		# 計測：ロックオンして連射、時々光刃とダッシュ（使える力だけ）。閂は途中で第 3 段階（過熱）に
		s.append({"ticks": 2, "setup": func(): RenderingServer.render_loop_enabled = true})
		s.append({"ticks": 480, "input_fn": func(i):
			var g: GameSim = m.game
			if i > 2:
				stats.draws.append(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME))
				stats.objs.append(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME))
				stats.phys.append(Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0)
			if i == 240 and g.boss != null and g.boss.alive:
				g.boss.debug_set_phase(3)
			# 倒しきらないように、敵の HP を戻す（混戦を続ける）
			for e in g.enemies:
				if e.alive and e != g.boss:
					e.hp = maxf(e.hp, e.max_hp * 0.5)
			var blocking: bool = g.story.blocking()
			return {"lock_on": true, "fire": (i % 8) < 4, "sword": i % 90 == 45, "dash": i % 150 == 100, "move_x": sin(i * 0.02) * 0.6,
				"jump": blocking and (i % 6) < 3}})
		s.append({"ticks": 1, "setup": func():
			var arr: Array = stats.draws
			if arr.is_empty():
				print("描画の計測 %s：こまが描かれていない" % nm)
				return
			var sorted := arr.duplicate()
			sorted.sort()
			var sum := 0
			for v in arr:
				sum += int(v)
			var objs: Array = stats.objs.duplicate()
			objs.sort()
			var ph: Array = stats.phys
			var ph_sum := 0.0
			for v in ph:
				ph_sum += float(v)
			print("描画の計測 %s（%s、%d こま）：最大 %d・95%% %d・平均 %.1f・中央 %d／物 最大 %d／物理の刻み 平均 %.2f ms" % [nm, RenderingServer.get_current_rendering_method(), arr.size(),
				sorted[-1], sorted[int(sorted.size() * 0.95)], float(sum) / arr.size(), sorted[sorted.size() / 2], objs[-1], ph_sum / maxf(1.0, ph.size())])})
		s.append({"ticks": 1, "shot": "bench_" + nm, "input": {}})
	return s


## 番機 5 種と閂の見た目の確認（--vfx_shots=machines。machine_<名前>.png）：ゲームのカメラで、型ごとに 3 体の警戒・予備動作、
## 突撃型の激突のあと（核の蓋）、盾型の盾が崩れた所、閂の待機・突きの予備動作・核が開いた所・回転・過熱・腕の破壊・撃破のあとの核。
## モデル（banki_parts.py・kannuki.py）を直したときに、同じ場面を前と後で撮って並べる
static func machine_steps(d) -> Array:
	var m = d.main
	# cam：撮る直前にカメラを置く（ゲームのカメラより近くから、機械が画面の大きな部分を占めるように）
	var shot := func(name: String, cam = null) -> Dictionary:
		var r := {"ticks": 1, "shot": "machine_" + name, "input": {}, "after": func(): print("描画 machine_%s：%s" % [name, _draws()])}
		if cam != null:
			r["cam"] = cam
		return r
	var near := func(kind: String, dist: float) -> Callable:
		var hv: float = float(m.game.tuning.enemies.floater.hover) if m.game != null else 1.2
		var f: Array = {"sentry": [2.0, 1.7, 3.8, 0.7], "mini": [0.35, 0.85, 2.7, 0.16], "shield": [3.0, 2.6, 6.0, 1.05],
				"floater": [1.4, hv + 1.6, 3.4, hv + 0.2], "charger": [3.4, 2.4, 5.6, 0.6]}[kind]
		return func(): _cam_at(d, Vector3(f[0], f[1], dist + f[2]), Vector3(0, f[3], dist + 0.4))
	var boss_cam := func(off: Vector3, look_y := 2.6) -> Callable:
		return func():
			var b = m.game.boss
			_cam_at(d, b.pos + off, b.pos + Vector3(0, look_y, 0))
	var trio := func(kind: String, dist := 4.0, gap := 2.5, off := 0.45):
		d._arena_start(kind)
		var g: GameSim = m.game
		# 浮遊型は動かない的（passive）にすると浮かないので、浮く高さに置く
		var y: float = float(g.tuning.enemies.floater.hover) if kind == "floater" else 0.0
		for i in 3:
			var e = g.enemies[i]
			_place(g, e, Vector3(-gap + gap * i, y, dist + absf(i - 1) * 0.8), Vector3(0, y, dist + 7.0))
			e.passive = true
		d._stand(Vector3(0, 0, dist + 6.0), Vector3(0, 0, dist))
		_view(d, off)
	var alert := func():
		for e in m.game.enemies:
			e.passive = false
			e.become_alert()
	var windup := func():
		for e in m.game.enemies:
			e.set_state("windup")
	var s := []
	for kind in ["sentry", "mini", "shield", "floater", "charger"]:
		var dist: float = {"sentry": 4.0, "mini": 3.0, "shield": 4.5, "floater": 3.5, "charger": 4.5}[kind]
		var gap: float = {"sentry": 2.5, "mini": 0.9, "shield": 3.2, "floater": 2.0, "charger": 3.4}[kind]
		s.append_array([
			{"ticks": 2, "setup": func(): trio.call(kind, dist, gap)},
			{"ticks": 30, "input": {}},
			shot.call("%s_1_idle" % kind, near.call(kind, dist)),
			{"ticks": 1, "input": {}, "setup": alert},
			{"ticks": 8, "input": {}},
			{"ticks": 1, "input": {}, "setup": windup},
			{"ticks": 20, "input": {}},
			shot.call("%s_2_windup" % kind, near.call(kind, dist)),
		])
	# 突撃型：壁に激突して動けない（本人の右の核の蓋が開く）
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("charger")
			var g: GameSim = m.game
			var e = g.enemies[0]
			_targets(g, [e])
			e.passive = false
			_place(g, e, Vector3(-9, 0, 0), Vector3(-16, 0, 0))
			e._charge_dir = Vector3(-1, 0, 0)
			e.set_state("attack")
			d._stand(Vector3(-10.5, 0, 3.5), Vector3(-15.5, 0, -0.5))},
		{"ticks": 60, "input_fn": func(_i): return {}},
		{"ticks": 1, "input": {}, "check": func(): return d._check(m.game.enemies[0].state == "stunned", "突撃型が壁に激突して動けない（機械の確認）")},
		{"ticks": 20, "input": {}},
		shot.call("charger_3_stunned_core", func():
			var e = m.game.enemies[0]
			_cam_at(d, e.pos + Vector3(1.6, 2.2, -4.6), e.pos + Vector3(0, 0.6, 0))),
	])
	# 盾型：盾が崩れる（盾を横へ振り出す）
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("shield")
			var g: GameSim = m.game
			var e = g.enemies[1]
			_targets(g, [e])
			_place(g, e, Vector3(0, 0, 3), Vector3(0, 0, 9))
			d._stand(Vector3(0, 0, 6.5), Vector3(0, 0, 3))
			_view(d, 0.9)},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			var e = g.enemies[1]
			g.damage_enemy(e, 41.0, g.player.pos, {"melee": true, "at": e.center() + e.forward() * 0.6})},
		{"ticks": 12, "input": {}},
		shot.call("shield_3_guard_broken", func(): _cam_at(d, Vector3(2.6, 2.4, 8.0), Vector3(0, 1.0, 3.0))),
	])
	# 閂
	var boss_start := func(phase: int, st: String, at := Vector3(0, 0, -3), stand := Vector3(0, 0, 12), off := 0.3):
		var g: GameSim = m.game
		var b = g.boss
		b.debug_set_phase(phase)
		b.pos = at
		b.yaw = U.dir_to_yaw(stand.x - at.x, stand.z - at.z)
		g.phys.set_feet(b.body, at)
		b.spin_r = 0.0
		b.lane = false
		b.wave_r = -1.0
		b.core_open = false
		b.set_state(st)
		d._stand(stand, at)
		_view(d, off)
	s.append_array([
		{"ticks": 2, "setup": func():
			d._arena_start("kannuki")
			var g: GameSim = m.game
			for b in g.breakables:
				b.broken = true
				g.phys.remove(b.body)
				b.body = null},
		{"ticks": 150, "input": {}},
		{"ticks": 2, "setup": func(): boss_start.call(1, "recover", Vector3(0, 0, -3), Vector3(4, 0, 11), 0.5)},
		{"ticks": 40, "input": {}},
		shot.call("kannuki_1_idle", boss_cam.call(Vector3(8.5, 5.5, 9.5))),
		{"ticks": 2, "setup": func(): boss_start.call(1, "thrust_windup", Vector3(0, 0, -8), Vector3(0, 0, 10))},
		{"ticks": 34, "input": {}},
		shot.call("kannuki_2_thrust_windup", boss_cam.call(Vector3(7.5, 5.0, 9.0))),
		# 突進が壁で止まった所（核が開く）：時間で待たず、壁の手前に置いて止まった状態にする
		{"ticks": 2, "setup": func():
			boss_start.call(1, "recover", Vector3(0, 0, 9.0), Vector3(-6, 0, 2), 0.0)
			m.game.boss._thrust_end(true)},
		{"ticks": 40, "input": {}},
		{"ticks": 1, "input": {}, "check": func(): return d._check(m.game.boss.core_open, "閂が突進のあと壁で止まり、核が開く（機械の確認）")},
		shot.call("kannuki_3_core_open", func():
			# 突進のあと壁ぎわで止まる：部屋の中心の側の上から、開いた核を見下ろす
			var b = m.game.boss
			var to_c: Vector3 = b.arena - b.pos
			to_c.y = 0.0
			var dir := to_c.normalized() if to_c.length() > 0.1 else Vector3(0, 0, 1)
			var side := dir.cross(Vector3.UP)
			_cam_at(d, b.pos + dir * 6.5 + side * 2.5 + Vector3(0, 8.0, 0), b.pos + Vector3(0, 3.4, 0))),
		{"ticks": 2, "setup": func(): boss_start.call(1, "spin_windup", Vector3(0, 0, -3), Vector3(0, 0, 9))},
		{"ticks": 64, "input": {}},
		shot.call("kannuki_4_spin", boss_cam.call(Vector3(8.0, 5.5, 9.0))),
		{"ticks": 2, "setup": func():
			boss_start.call(3, "recover", Vector3(0, 0, -2), Vector3(3, 0, 10), 0.5)
			for e in m.game.enemies:
				if e != m.game.boss:
					e.alive = false
			m.game.boss.heat_state = 2
			m.game.boss.heat_time = 0.0},
		{"ticks": 80, "input": {}},
		shot.call("kannuki_5_overheat", boss_cam.call(Vector3(8.0, 5.5, 8.5))),
		{"ticks": 2, "setup": func():
			boss_start.call(2, "recover", Vector3(0, 0, -2), Vector3(-2, 0, 9))
			m.game.boss.heat_state = 0
			m.game.boss.overheat = false},
		{"ticks": 10, "input": {}},
		{"ticks": 1, "input": {}, "setup": func():
			var g: GameSim = m.game
			var b = g.boss
			g.damage_enemy(b, 200.0, g.player.pos, {"melee": true, "at": b.arm_center("fr")})},
		{"ticks": 70, "input": {}},
		shot.call("kannuki_6_arm_broken", boss_cam.call(Vector3(-8.5, 5.5, 8.5))),
		{"ticks": 2, "setup": func():
			var g: GameSim = m.game
			var b = g.boss
			b.debug_set_phase(3)
			b.core_open = true
			var guard := 0
			while b.alive and guard < 100:
				g.damage_enemy(b, 60.0, g.player.pos, {"melee": true, "at": b.axis_center()})
				guard += 1},
		{"ticks": 135, "input": {}},
		shot.call("kannuki_7_destroyed_core", boss_cam.call(Vector3(7.5, 6.0, 8.0), 2.0)),
	])
	return s
