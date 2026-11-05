extends RefCounted
## 手触りの数値テスト。docs/design/20_ゲームシステム設計.md 4 章と
## docs/design/30_レベルデザイン設計.md 1.2 の値が守られていることを確かめる。

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func test_run_speed() -> void:
	var g := h.make_game()
	await h.settle()
	await h.run(g, TestHelpers.seconds(1), {"move_y": 1.0})
	h.near(g.player.speed(), 7.0, 0.1, "走る速さは 7m/s に達する")
	h.free_game(g)


func test_jump_height() -> void:
	var g := h.make_game()
	await h.settle()
	await h.run(g, 5, {})
	var max_y := [0.0]
	await h.run(g, TestHelpers.seconds(1.2), func(i):
		max_y[0] = maxf(max_y[0], g.player.pos.y)
		return {"jump": i < TestHelpers.seconds(0.6)})
	h.between(max_y[0], 2.1, 2.3, "ジャンプの最高点は約 2.2m")
	h.free_game(g)


func test_min_jump() -> void:
	var g := h.make_game()
	await h.settle()
	await h.run(g, 5, {})
	var max_y := [0.0]
	await h.run(g, TestHelpers.seconds(1), func(i):
		max_y[0] = maxf(max_y[0], g.player.pos.y)
		return {"jump": i < 1})
	h.between(max_y[0], 0.7, 1.05, "ボタンをすぐ離すと低いジャンプになる（約 0.8m）")
	h.free_game(g)


func test_dash_distance() -> void:
	var g := h.make_game()
	await h.settle()
	await h.run(g, 5, {})
	var z0: float = g.player.pos.z
	await h.run(g, TestHelpers.seconds(0.22), func(i): return {"dash": i == 0})
	h.between(absf(g.player.pos.z - z0), 3.0, 3.6, "ダッシュは約 3.3m 進む")
	h.free_game(g)


func test_ledges() -> void:
	for pair in [[1.8, true], [2.4, false]]:
		var ht: float = pair[0]
		var g := h.make_game({"boxes": [[Vector3(0, ht / 2.0, 6), Vector3(6, ht, 4)]]})
		await h.settle()
		await h.run(g, 5, {})
		# 段の手前まで走り、跳んで前へ進み続ける
		var on_top := [false]
		await h.run(g, TestHelpers.seconds(1.6), func(i):
			if g.player.grounded and g.player.pos.y > ht - 0.1:
				on_top[0] = true
			return {"move_y": 1.0, "jump": i > TestHelpers.seconds(0.35) and i < TestHelpers.seconds(0.9)})
		h.expect(on_top[0] == pair[1], "段の高さ %.1fm：登れる=%s（結果 %s）" % [ht, pair[1], on_top[0]])
		h.free_game(g)


## 高さ ht の段（手前の面が z=4、幅 60 m・奥行き 30 m）へ、向き yaw（ラジアン。0 で +Z）から stick の強さで歩いて行く。
## 返り値：{ top: 段の上に立った, y, z, max_y: いちばん高い足元, air: 接地していない刻みの数, dip: 段の上で下がった深さ,
##   bob: 1 刻みで足元が下がったいちばん大きな量（上る途中で上下に揺れていないか） }
func _walk_into_step(ht: float, stick: float = 1.0, yaw: float = 0.0, secs: float = 1.6) -> Dictionary:
	var g := h.make_game({"boxes": [[Vector3(0, ht / 2.0, 19), Vector3(60, ht, 30)]], "markers": {"start": Vector3(0, 0, 1.5)}})
	await h.settle()
	g.player.teleport(Vector3(0, 0, 1.5), yaw)
	g.cam.yaw = yaw
	await h.run(g, 5, {})
	var r := {"top": false, "max_y": 0.0, "air": 0, "dip": 0.0, "bob": 0.0, "last": 0.0}
	var top_y := [INF]
	await h.run(g, TestHelpers.seconds(secs), func(_i):
		var p: Vector3 = g.player.pos
		r.max_y = maxf(r.max_y, p.y)
		r.bob = maxf(r.bob, r.last - p.y)
		r.last = p.y
		if not g.player.grounded:
			r.air += 1
		if g.player.grounded and p.y > ht - 0.02 and p.z > 4.2:
			r.top = true
		if r.top:
			top_y[0] = minf(top_y[0], p.y)
		return {"move_y": stick})
	r["y"] = g.player.pos.y
	r["z"] = g.player.pos.z
	if r.top:
		r.dip = maxf(0.0, ht - top_y[0])
	h.free_game(g)
	return r


## 歩いて上る段（自動の乗り越え。Phys.STEP_HEIGHT の 0.35 m まで）：どの高さの段でも、歩いて当たると止まらずに上る。
## 前は 0.18〜0.24 m の段で、体の丸い底が段の角に当たる向き（法線の y が 0.3〜0.71）が、乗り越え（壁とみなす向き）にも床にもならず、
## 角に押し当てたまま止まった（N13、2026-11-05 に直した。Phys.move_character）。0.35 m より高い段は、今までどおり歩いては上れない
func test_stepup_heights() -> void:
	for pair in [[0.05, true], [0.10, true], [0.15, true], [0.18, true], [0.21, true], [0.24, true], [0.27, true], [0.30, true],
			[Phys.STEP_HEIGHT - 0.01, true], [Phys.STEP_HEIGHT, true], [0.38, false], [0.45, false], [0.60, false]]:
		var ht: float = pair[0]
		var r: Dictionary = await _walk_into_step(ht)
		var what := "段 %.2f m：歩いて上れる=%s（上った %s、足元 y=%.3f z=%.2f、最高 %.3f、宙 %d 刻み、揺れ %.3f）" % [ht, pair[1], r.top, r.y, r.z, r.max_y, r.air, r.bob]
		h.expect(r.top == pair[1], what)
		print("    ", what)
		if pair[1]:
			h.expect(r.z > 6.0 and absf(r.y - ht) < 0.01, "%s：段の上を先まで進み、段の高さに立つ" % what)
			h.expect(r.max_y < ht + 0.03 and r.dip < 0.01, "%s：段の上で跳ね上がったり沈んだりしない" % what)
			h.expect(r.air <= 2, "%s：上る間に宙に浮かない" % what)
		else:
			h.expect(r.z < 4.0 and r.y < 0.02, "%s：段の手前で止まり、床に立ったまま" % what)


## ゆっくり歩いて（スティックを少しだけ倒して）も、斜めに当たっても、0.18〜0.24 m の段を上れる
func test_stepup_slow_and_angled() -> void:
	for ht in [0.12, 0.18, 0.21, 0.24, 0.30]:
		for c in [[0.35, 0.0], [1.0, deg_to_rad(40.0)], [0.5, deg_to_rad(-60.0)]]:
			var r: Dictionary = await _walk_into_step(ht, c[0], c[1], 3.0)
			var what := "段 %.2f m、倒し %.2f、向き %.0f 度（足元 y=%.3f z=%.2f、宙 %d 刻み、揺れ %.3f）" % [ht, c[0], rad_to_deg(c[1]), r.y, r.z, r.air, r.bob]
			h.expect(r.top and absf(r.y - ht) < 0.01, "%s：上れる" % what)
			h.expect(r.max_y < ht + 0.03 and r.air <= 2, "%s：跳ね上がらず、宙に浮かない" % what)
	# 高すぎる段（0.38 m）は、ゆっくりでも斜めでも上れない
	for c in [[0.35, 0.0], [1.0, deg_to_rad(40.0)]]:
		var r: Dictionary = await _walk_into_step(0.38, c[0], c[1], 2.0)
		h.expect(not r.top and r.y < 0.02, "段 0.38 m は、倒し %.2f・向き %.0f 度でも歩いては上れない（y=%.3f）" % [c[0], rad_to_deg(c[1]), r.y])


## 坂・階段の上り下りは変わらない：0.3 m の段の階段を上って下り、14 度と 40 度の坂を上って下りる間、
## 足元の高さは行く向きにだけ変わり（上る間に下がらない・下りる間に上がらない）、ほとんど接地したまま
func test_stepup_stairs_and_ramps() -> void:
	var cases := [
		["階段（0.3 m × 6 段）", {"t": "stairs", "pos": [0, 0, 6.6], "size": [4, 1.8, 3.6], "steps": 6}, 1.8],
		["階段（0.2 m × 6 段）", {"t": "stairs", "pos": [0, 0, 6.6], "size": [4, 1.2, 3.6], "steps": 6}, 1.2],
		["坂（14 度）", {"t": "ramp", "pos": [0, 0, 7.8], "size": [4, 1.5, 6]}, 1.5],
		["坂（40 度）", {"t": "ramp", "pos": [0, 0, 6.6], "size": [4, 3.02, 3.6]}, 3.02],
	]
	for cs in cases:
		var name: String = cs[0]
		var top: float = cs[2]
		var shape: Dictionary = cs[1]
		var faces := [TestHelpers.box_faces(Vector3(0, -0.5, 0), Vector3(200, 1, 200))]
		faces.append_array(RoomGeo.shape(shape))
		# 上り口の先の平らな台（上りきった所）
		var land_z: float = float(shape.pos[2]) + float(shape.size[2]) * 0.5
		faces.append(TestHelpers.box_faces(Vector3(0, top * 0.5, land_z + 10.0), Vector3(4, top, 20)))
		var g := h.make_game({"geometry": {"faces": faces, "markers": {"start": {"pos": Vector3(0, 0, 1.0), "yaw": 0.0}}}})
		await h.settle()
		await h.run(g, 5, {})
		var st := {"drop": 0.0, "rise": 0.0, "air": 0, "last": 0.0, "t_top": -1}
		await h.run(g, TestHelpers.seconds(2.4), func(i):
			var y: float = g.player.pos.y
			st.drop = maxf(st.drop, st.last - y)
			st.last = y
			if not g.player.grounded:
				st.air += 1
			if st.t_top < 0 and y > top - 0.01:
				st.t_top = i
			return {"move_y": 1.0})
		h.expect(absf(g.player.pos.y - top) < 0.02, "%s：上りきる（y=%.3f）" % [name, g.player.pos.y])
		h.expect(st.drop < 0.01, "%s：上る間に足元が下がらない（いちばん下がった %.3f m）" % [name, st.drop])
		h.expect(st.air <= 3, "%s：上る間ほとんど接地したまま（宙 %d 刻み）" % [name, st.air])
		h.between(st.t_top, 0, TestHelpers.seconds(2.0), "%s：上りきるまでの刻み" % name)
		# 下りる
		g.cam.yaw = PI
		g.player.yaw = PI
		st.last = g.player.pos.y
		st.air = 0
		await h.run(g, TestHelpers.seconds(2.6), func(_i):
			var y: float = g.player.pos.y
			st.rise = maxf(st.rise, y - st.last)
			st.last = y
			if not g.player.grounded:
				st.air += 1
			return {"move_y": 1.0})
		h.expect(g.player.pos.y < 0.02 and g.player.pos.z < 3.0, "%s：下りきる（y=%.3f z=%.2f）" % [name, g.player.pos.y, g.player.pos.z])
		h.expect(st.rise < 0.01, "%s：下りる間に足元が上がらない（いちばん上がった %.3f m）" % [name, st.rise])
		print("    %s：上りきる %d 刻み、下りで宙 %d 刻み" % [name, st.t_top, st.air])
		h.free_game(g)


## g のハルを start から向き yaw（度。0 で +Z、正で +X へ）・倒し stick で最大 ticks 刻み歩かせ、接地して goal_y に届くまでを数える。
## 返り値：{ t: 届いた刻み（届かなければ -1）, air: それまでに接地していなかった刻み, lifts: 接地から離れた回数, y }
func _climb_to(g: GameSim, start: Vector3, yaw_deg: float, stick: float, ticks: int, goal_y: float) -> Dictionary:
	var yaw := deg_to_rad(yaw_deg)
	g.player.teleport(start, yaw)
	g.cam.yaw = yaw
	await h.run(g, 3, {})
	var r := {"t": -1, "air": 0, "lifts": 0, "was": true}
	await h.run_until(g, ticks, {"move_y": stick}, func():
		var gnd: bool = g.player.grounded
		if not gnd:
			r.air += 1
		if r.was and not gnd:
			r.lifts += 1
		r.was = gnd
		if gnd and g.player.pos.y > goal_y - 0.05:
			r.t = 1
			return true
		return false)
	r["y"] = g.player.pos.y
	return r


## 横に壁（手すり）のある階段・段を、壁へ斜めに歩いて上る：上りきり、上る間ずっと接地したまま（浮いては落ちるのを繰り返さない）。
## 前は 1 段上ったあと次の段の角に載り、乗り越えの確かめが横の壁に当たって失敗して、接地しないまま角の上で浮いては落ち、
## 上りきれなかった（町の下段の階段を手すりへ 40〜50 度で。Phys._try_step は、ふさがれたら壁に沿う向きで確かめ直す）
func test_stepup_stairs_along_wall() -> void:
	var wall := TestHelpers.box_faces(Vector3(3.8, 4, 20), Vector3(0.4, 8, 40))
	var cases := []
	for spec in [[0.2, 10, 5.0], [0.3, 6, 3.6], [0.35, 6, 3.6]]:
		var hh: float = spec[0] * spec[1]
		var faces := [TestHelpers.box_faces(Vector3(0, -0.5, 0), Vector3(200, 1, 200)), wall]
		faces.append_array(RoomGeo.shape({"t": "stairs", "pos": [0, 0, 4 + spec[2] / 2.0], "size": [7.2, hh, spec[2]], "steps": spec[1]}))
		faces.append(TestHelpers.box_faces(Vector3(0, hh / 2.0, 4 + spec[2] + 5), Vector3(7.2, hh, 10)))
		cases.append(["階段 %.2f m × %d 段" % [spec[0], spec[1]], faces, hh, [[30.0, 0.4], [50.0, 0.4], [40.0, 1.0], [50.0, 1.0]]])
	# 1 段だけの段へ、壁へ 60 度・ゆっくり（前は宙に浮いては落ちるのを繰り返した）
	for ht in [0.2, 0.3]:
		cases.append(["段 %.2f m" % ht, [TestHelpers.box_faces(Vector3(0, -0.5, 0), Vector3(200, 1, 200)), wall,
				TestHelpers.box_faces(Vector3(0, ht / 2.0, 19), Vector3(7.2, ht, 30))], ht, [[60.0, 0.4]]])
	for cs in cases:
		var g := h.make_game({"geometry": {"faces": cs[1], "markers": {"start": {"pos": Vector3(1, 0, 2), "yaw": 0.0}}}})
		await h.settle()
		for c in cs[3]:
			var r: Dictionary = await _climb_to(g, Vector3(1, 0, 2), c[0], c[1], TestHelpers.seconds(10), cs[2])
			var what := "%s、壁へ %.0f 度・倒し %.1f（届いた %s、y=%.3f、宙 %d 刻み、離れた %d 回）" % [cs[0], c[0], c[1], r.t >= 0, r.y, r.air, r.lifts]
			print("    ", what)
			h.expect(r.t >= 0, "%s：上りきる" % what)
			h.expect(r.air <= 2 and r.lifts <= 1, "%s：上る間ずっと接地したまま" % what)
		h.free_game(g)
	# 本物の部屋：町の下段の階段（z 16〜28、y 0〜5、両側に手すり x=±3.8）
	var g2 := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g2)
	g2.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	g2.set_flag("ch1.chores_started")
	g2.load_room("ch1.lower")
	await h.settle()
	for ang in [-50.0, 40.0, 60.0]:
		var r: Dictionary = await _climb_to(g2, Vector3(0, 0, 15.2), ang, 1.0, TestHelpers.seconds(10), 5.0)
		var what := "町の下段の階段、手すりへ %.0f 度（届いた %s、y=%.3f、宙 %d 刻み、離れた %d 回）" % [ang, r.t >= 0, r.y, r.air, r.lifts]
		print("    ", what)
		h.expect(r.t >= 0 and r.air <= 2, "%s：上りきり、ずっと接地したまま" % what)
	h.free_game(g2)


## 敵の大きさの体（地形だけに当たるカプセル）も、0.35 m までの段は上り、それより高い段は速く当たっても上らない。
## 前は段の角に沿って押し上げられた所から高さを数えたので、大きな体・速い動きでは 0.36〜0.42 m の段も上った（N13 の見直し）
func test_stepup_enemy_sizes() -> void:
	for rr in [[0.25, 0.3], [0.45, 1.1], [0.55, 1.8], [0.7, 1.2]]:
		for spd in [2.0, 8.0, 14.0]:
			for pair in [[0.12, true], [0.24, true], [0.34, true], [0.37, false], [0.40, false], [0.44, false]]:
				var ht: float = pair[0]
				var g := h.make_game({"boxes": [[Vector3(0, ht / 2.0, 19), Vector3(60, ht, 30)]], "markers": {"start": Vector3(0, 0, -6)}})
				await h.settle()
				var b := g.phys.create_character(Vector3(0, 0, 4.0 - rr[0] - 1.0), rr[0], rr[1], Phys.ENEMY, Phys.TERRAIN)
				await h.settle()
				var gnd := true
				for k in 50:
					var res: Dictionary = g.phys.move_character(b, Vector3(0, -0.05 if gnd else -0.2, spd / 60.0), Phys.TERRAIN, gnd)
					gnd = res.grounded
				var up: bool = b.position.y > ht - 0.02
				h.expect(up == pair[1], "体 半径 %.2f m・%.0f m/s で段 %.2f m：上る=%s（y=%.3f）" % [rr[0], spd, ht, pair[1], b.position.y])
				h.free_game(g)


func test_gaps() -> void:
	# 手前の足場は z<0、溝のあと向こう側の足場。床は溝の下に落ちる
	var make := func(gap: float) -> GameSim:
		return h.make_game({
			"boxes": [[Vector3(0, 5, -10), Vector3(6, 10, 20)], [Vector3(0, 5, gap + 10), Vector3(6, 10, 20)]],
			"markers": {"start": Vector3(0, 10, -6)},
		})
	# 通常のジャンプで 4.5m
	var g: GameSim = make.call(4.5)
	await h.settle()
	await h.run(g, 5, {})
	await h.run(g, TestHelpers.seconds(2.5), func(_i): return {"move_y": 1.0, "jump": g.player.pos.z > -0.5})
	h.expect(g.player.pos.y > 9.5 and g.player.pos.z > 4.5, "走りジャンプで 4.5m の溝を越えられる（y=%.2f z=%.2f）" % [g.player.pos.y, g.player.pos.z])
	h.free_game(g)
	# ダッシュジャンプで 7m
	var g2: GameSim = make.call(7.0)
	await h.settle()
	await h.run(g2, 5, {})
	var dashed := [false]
	await h.run(g2, TestHelpers.seconds(2.5), func(_i):
		var z: float = g2.player.pos.z
		var dash: bool = not dashed[0] and z > -3.6
		if dash:
			dashed[0] = true
		return {"move_y": 1.0, "dash": dash, "jump": z > -0.6})
	h.expect(g2.player.pos.y > 9.5 and g2.player.pos.z > 7.0, "ダッシュジャンプで 7m の溝を越えられる（y=%.2f z=%.2f）" % [g2.player.pos.y, g2.player.pos.z])
	h.free_game(g2)


## 走りながら背後のボタン（ロックオンのボタン・C／R3／タッチの「背後」）を押しても、カメラは回り続けずにハルの背後で止まり、
## ハルはそのまま同じ向きへ走り続ける（回している間と、そのあと同じ向きへ倒し続けている間は、左スティックの基準を押す前のカメラのまま）。
## 前は、回るカメラにつられて進む向きが回り、それをカメラが追って、横へ走りながら押すと 1 周近く回って横のまま止まった（2026-10-08）
func test_recenter_while_running() -> void:
	for btn in ["lock_on", "camera_reset"]:
		for stick in [Vector2(1, 0), Vector2(0, -1), Vector2(0.6, 0.8), Vector2(-0.8, -0.6)]:
			var g := h.make_game()
			await h.settle()
			g.cam.follow = "weak"
			g.cam.yaw = 0.0
			var hold := {"move_x": stick.x, "move_y": stick.y}
			await h.run(g, 40, hold)
			var p: Player = g.player
			var heading0 := U.dir_to_yaw(p.vel.x, p.vel.z)
			var gap0 := absf(U.wrap_angle(p.yaw - g.cam.yaw))
			var turned := 0.0
			var prev := g.cam.yaw
			for i in 45:
				var f := hold.duplicate()
				if i == 0:
					f[btn] = true
				await h.run(g, 1, f)
				turned += absf(U.wrap_angle(g.cam.yaw - prev))
				prev = g.cam.yaw
			var what := "%s・左スティック %s" % [btn, stick]
			h.expect(turned < gap0 + 3.0 * U.DEG, "%s：カメラは回り続けない（回った角度 %.0f°、押したときの差 %.0f°）" % [what, turned / U.DEG, gap0 / U.DEG])
			h.near(U.wrap_angle(p.yaw - g.cam.yaw) / U.DEG, 0.0, 2.0, "%s：カメラがハルの背後で止まる" % what)
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0) / U.DEG, 0.0, 2.0, "%s：ハルはそのまま同じ向きへ走る" % what)
			# 倒したままなら、そのあとも同じ向き。前へ倒し直す（大きく変える）と、基準はカメラに戻る：カメラの前＝ハルの背中の向きへ走る
			await h.run(g, 30, hold)
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0) / U.DEG, 0.0, 2.0, "%s：倒したままなら同じ向きへ走り続ける" % what)
			await h.run(g, 20, {"move_y": 1.0})
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - g.cam.yaw) / U.DEG, 0.0, 2.0, "%s：前へ倒し直すと、カメラの前へ走る" % what)
			# 離してから横へ倒すと、今のカメラの右へ
			await h.run(g, 3, {})
			await h.run(g, 20, {"move_x": 1.0})
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - (g.cam.yaw - PI / 2)) / U.DEG, 0.0, 2.0, "%s：離して右へ倒すと、今のカメラの右へ走る" % what)
			h.free_game(g)
	# 止まったまま押して、回している途中で横へ倒しても、カメラは回り続けない
	var g2 := h.make_game()
	await h.settle()
	g2.cam.yaw = PI / 2
	await h.run(g2, 3, {})
	var turned2 := 0.0
	var prev2 := g2.cam.yaw
	for i in 60:
		var f := {"camera_reset": i == 0, "move_x": 1.0 if i >= 5 else 0.0}
		await h.run(g2, 1, f)
		turned2 += absf(U.wrap_angle(g2.cam.yaw - prev2))
		prev2 = g2.cam.yaw
	h.expect(turned2 < 190.0 * U.DEG, "回している途中で横へ倒しても、カメラは回り続けない（%.0f°）" % (turned2 / U.DEG))
	var p2: Player = g2.player
	h.near(U.wrap_angle(U.dir_to_yaw(p2.vel.x, p2.vel.z) - (0.0 - PI / 2)) / U.DEG, 0.0, 2.0, "回している途中で倒した右は、カメラが向かう先（押したときのハルの向き）の右")
	h.free_game(g2)


## 背後へ回している途中でロックオンが敵を捉えたら、回すのはやめる。外れたあとに残りの回転が基準なしで走って回り続けない。
## 止めていた左スティックの基準は、捉えている間にカメラと同じ割合で寄せていき、カメラに追いついたら止めるのをやめる（1 刻みで跳ばない）
func test_recenter_cancelled_by_lock() -> void:
	var t := TestHelpers.default_tuning()
	var dt := 1.0 / 60.0
	var k := U.damp(t.camera.lockOnYawSpeed, dt)
	for lock_ticks in [1, 90]:
		var cam := CameraOrbit.new(t)
		cam.follow = "weak"
		cam.yaw = 0.0
		var f := InputFrame.new()
		f.move_x = 1.0
		cam.apply_look(f)
		cam.request_recenter(PI / 2, Vector2(1, 0))
		cam.update(dt, Vector3.ZERO, PI / 2, 7.0, null)
		var want := U.dir_to_yaw(5.0, 5.0)
		var worst := 0.0
		for i in lock_ticks:
			var b0 := cam.move_yaw()
			cam.apply_look(f)
			cam.update(dt, Vector3.ZERO, PI / 2, 7.0, Vector3(5, 0, 5))
			var moved := absf(U.wrap_angle(cam.move_yaw() - b0))
			worst = maxf(worst, moved - k * absf(U.wrap_angle(want - b0)))
		# 追いついてやめる刻み（差が 0.17° 未満。CameraOrbit.LOCK_HOLD_DONE）にだけ、残りのわずかな差を詰める
		h.expect(worst < 0.2 * U.DEG, "捉えた %d 刻み：基準はカメラと同じ割合でしか動かない（1 刻みで跳ばない。超えた分 %.2f°）" % [lock_ticks, worst / U.DEG])
		var y0 := cam.yaw
		for i in 30:
			cam.apply_look(f)
			cam.update(dt, Vector3.ZERO, PI / 2, 7.0, null)
		h.near(U.wrap_angle(cam.yaw - y0), 0.0, 0.0001, "捉えた %d 刻み：外れても、回していた続きは走らない" % lock_ticks)
		if lock_ticks > 1:
			h.near(U.wrap_angle(cam.move_yaw() - cam.yaw), 0.0, 0.0001, "捉えている間に、左スティックの基準はカメラに追いついた")
		# 離せば基準はカメラに戻る
		cam.apply_look(InputFrame.new())
		h.near(U.wrap_angle(cam.move_yaw() - cam.yaw), 0.0, 0.0001, "捉えた %d 刻み：離せば左スティックの基準はカメラ" % lock_ticks)


## ロックオンのボタンを短く押して（その瞬間は誰もいない）背後へ回している途中に、敵が見えてきても捉えない。
## 回し終えるとカメラはハルの背後、進む向きは変わらない。押し続けていれば、回し終えてから捉える（2026-10-13）
func test_recenter_tap_with_enemy_entering_view() -> void:
	for tap in [4, 6, 8, 12, 40]:
		var g := h.make_game()
		await h.settle()
		g.cam.follow = "weak"
		g.cam.yaw = 0.0
		var hold := {"move_y": -1.0}
		await h.run(g, 40, hold)
		var p: Player = g.player
		var heading0 := U.dir_to_yaw(p.vel.x, p.vel.z)
		# ハルから 15 m、カメラの後ろ側（前方 ±75° の外、8 m より遠い）に、動かない番機
		var at := p.pos + U.yaw_to_dir(heading0 + 30.0 * U.DEG) * 15.0
		var e = g.spawn_enemy_spec({"type": "sentry", "pos": [at.x, 0, at.z], "passive": true, "invulnerable": true})
		await h.run(g, 1, hold)
		var caught_mid := false
		for i in 150:
			var f := hold.duplicate()
			f["lock_on"] = i < tap
			await h.run(g, 1, f)
			if g.cam.swinging() and g.lock_on.target != null:
				caught_mid = true
		var what := "%d 刻み押す" % tap
		h.expect(not caught_mid, "%s：背後へ回している途中では捉えない" % what)
		if tap < 40:
			h.near(U.wrap_angle(p.yaw - g.cam.yaw) / U.DEG, 0.0, 3.0, "%s：離したあと、カメラはハルの背後" % what)
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0) / U.DEG, 0.0, 3.0, "%s：ハルの進む向きは変わらない" % what)
		else:
			h.expect(g.lock_on.target == null or g.lock_on.target == e, "%s：回し終えてから捉えるのは見えている番機" % what)
		h.free_game(g)


## 背後へ回したあと、倒し直しの途中でもう一度押しても、ハルの進む向きは跳ばない
func test_recenter_twice_keeps_heading() -> void:
	var g := h.make_game()
	await h.settle()
	g.cam.follow = "weak"
	g.cam.yaw = 0.0
	await h.run(g, 40, {"move_x": 1.0})
	await h.run(g, 1, {"move_x": 1.0, "camera_reset": true})
	await h.run(g, 30, {"move_x": 1.0})
	# 右から斜め前へ半分ほど倒し直す（基準が少しカメラへ戻る）
	var a := (-PI / 2) * 0.5
	await h.run(g, 10, {"move_x": -sin(a), "move_y": cos(a)})
	var p: Player = g.player
	var before := U.dir_to_yaw(p.vel.x, p.vel.z)
	var worst := 0.0
	for i in 30:
		await h.run(g, 1, {"move_x": -sin(a), "move_y": cos(a), "camera_reset": i == 0})
		worst = maxf(worst, absf(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - before)))
	h.expect(worst < 2.0 * U.DEG, "続けて押しても進む向きは変わらない（最大 %.1f°）" % (worst / U.DEG))
	h.free_game(g)


## 背後へ回している途中、マウスの小さな揺れ（右クリック中など）では止まらない。はっきり回せば止まる
func test_recenter_ignores_small_look() -> void:
	var t := TestHelpers.default_tuning()
	var dt := 1.0 / 60.0
	for big in [false, true]:
		var cam := CameraOrbit.new(t)
		cam.yaw = 0.0
		cam.request_recenter(PI / 2, Vector2.ZERO)
		for i in 30:
			var f := InputFrame.new()
			f.look_x = (0.05 if big else 0.002) if i < 5 else 0.0
			f.look_active = i < 5
			cam.apply_look(f)
			cam.update(dt, Vector3.ZERO, PI / 2, 0.0, null)
		if big:
			h.expect(absf(U.wrap_angle(cam.yaw - PI / 2)) > 30.0 * U.DEG, "はっきり回すと、背後へ回すのをやめる")
		else:
			h.near(U.wrap_angle(cam.yaw - PI / 2) / U.DEG, 0.0, 3.0, "小さな揺れでは止まらず、背後まで回る")


## 背後へ回したあと、左スティックを横から前へゆっくり倒し直しても、ハルはまっすぐ走り続ける（止めた基準が倒し直した分だけカメラへ戻る）。
## 倒したまま指が少し揺れても、進路はずれていかない
func test_recenter_hold_returns_to_camera() -> void:
	for jitter in [false, true]:
		var g := h.make_game()
		await h.settle()
		g.cam.yaw = 0.0
		await h.run(g, 40, {"move_x": 1.0})
		await h.run(g, 1, {"move_x": 1.0, "camera_reset": true})
		await h.run(g, 30, {"move_x": 1.0})
		var p: Player = g.player
		var heading0 := U.dir_to_yaw(p.vel.x, p.vel.z)
		h.near(U.wrap_angle(heading0 - g.cam.yaw) / U.DEG, 0.0, 2.0, "カメラはハルの背後")
		var worst := 0.0
		if jitter:
			# 右に倒したまま ±3° の揺れ（2 秒）
			for i in 120:
				var a := (-PI / 2) + (3.0 * U.DEG if i % 2 == 0 else -3.0 * U.DEG)
				await h.run(g, 1, {"move_x": -sin(a), "move_y": cos(a)})
				worst = maxf(worst, absf(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0)))
			# 揺れの分だけ（基準をカメラへ戻す向きでない揺れは 2 倍）ふらつくが、積もらない
			h.expect(worst < 7.0 * U.DEG, "倒したまま指が揺れても、ふらつきは揺れの 2 倍まで（最大 %.1f°）" % (worst / U.DEG))
			await h.run(g, 10, {"move_x": 1.0})
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0) / U.DEG, 0.0, 1.0, "揺れが止まれば元の向き（進路のずれが積もらない）")
			h.expect(absf(U.wrap_angle(g.cam.move_yaw() - g.cam.yaw)) > 80.0 * U.DEG, "揺れだけでは基準はカメラへ戻らない")
		else:
			# 右から前へ 0.33 秒かけて倒し直す
			for i in 21:
				var a := (-PI / 2) * (1.0 - i / 20.0)
				await h.run(g, 1, {"move_x": -sin(a), "move_y": cos(a)})
				worst = maxf(worst, absf(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0)))
			h.expect(worst < 3.0 * U.DEG, "右から前へ倒し直す間も、ハルはまっすぐ走る（最大 %.1f°）" % (worst / U.DEG))
			h.near(U.wrap_angle(g.cam.move_yaw() - g.cam.yaw), 0.0, 0.0001, "倒し直し終えたら、基準はカメラに戻る")
		h.free_game(g)


## 背後へ回している途中で、部屋が変わったり（出口の手前で押した）台本の teleport が入ったりしても、そのあとカメラは回らない。
## カメラの向きを外から書き換えたら（部屋の読み込み・復活・台本の teleport・セーブの読み込み）、回している続きも、止めていた基準もやめる（CameraOrbit.yaw）。
## 台本の teleport：右へ倒したままなら、新しいカメラの右へ走る。
## 出口を通った部屋の移動：倒したままなら、ハルはそのまま新しい部屋の奥（入口の目印の向き＝新しいカメラの向き）へ進む（CameraOrbit.keep_heading）。
## 離して倒し直せば、新しいカメラから測る。
## 前は基準だけカメラに戻して回転の続きが残り、新しい部屋で、回るカメラにつられて進む向きが回り、ハルが扉へ走り戻った（2026-10-08）
func test_recenter_ends_on_room_change_and_teleport() -> void:
	for how in ["room", "teleport"]:
		for btn in ["camera_reset", "lock_on"]:
			var g := h.make_game()
			await h.settle()
			g.cam.follow = "weak"
			g.cam.yaw = 0.0
			var hold := {"move_x": 1.0}
			await h.run(g, 40, hold)
			var f := hold.duplicate()
			f[btn] = true
			await h.run(g, 1, f)
			await h.run(g, 3, hold)
			if how == "room":
				# 出口と同じ（go_to）：刻みの最後に読み込み、そのあと 2 刻みは読み込み待ち。試しの部屋は 1 つなので同じ部屋を読み直す
				g._pending_room = {"room": g.room_id, "spawn": "start"}
				await h.run(g, 1, hold)
				h.expect(g.drain_events().any(func(e): return e.type == "roomChanged"), "部屋を読み込んだ")
				await h.run(g, 2, hold)
			else:
				g.story._run_step({"teleport": {"pos": [0, 0, 0], "yaw": 180}})
			var y0 := g.cam.yaw
			var turned := 0.0
			var prev := g.cam.yaw
			for i in 60:
				await h.run(g, 1, hold)
				turned += absf(U.wrap_angle(g.cam.yaw - prev))
				prev = g.cam.yaw
			var p: Player = g.player
			var what := "%s の途中の %s" % [btn, "部屋の移動" if how == "room" else "台本の teleport"]
			h.expect(turned < 3.0 * U.DEG, "%s：そのあとカメラは回らない（%.0f°）" % [what, turned / U.DEG])
			if how == "room":
				h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - y0) / U.DEG, 0.0, 3.0, "%s：右へ倒したまま、新しい部屋の奥（入口の目印の向き）へ進み続ける" % what)
			else:
				h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - (y0 - PI / 2)) / U.DEG, 0.0, 3.0, "%s：右へ倒したまま、新しいカメラの右へ走る" % what)
			await h.run(g, 3, {})
			await h.run(g, 20, hold)
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - (g.cam.yaw - PI / 2)) / U.DEG, 0.0, 3.0, "%s：離して右へ倒し直すと、今のカメラの右へ走る" % what)
			h.free_game(g)


## 同じ部屋で復活しても（やられた画面で「再開」・自動の再開）、止めていた左スティックの基準と回している続きは残らない：
## 右へ倒したままなら、復活したカメラの右へ走り、カメラは回らない。
## 前は復活の書き換えに気づかず、やられる前の基準でカメラへ向かって走ったり、やられている間に押した回転の続きが復活のあとに回ったりした（2026-10-08）
func test_recenter_ends_on_respawn() -> void:
	# [再開の仕方, 背後のボタンを押す時]：before＝やられる前に押して倒し続ける、dead＝やられている間にロックオンのボタン
	for c in [["manual", "before"], ["manual", "dead"], ["auto", "before"], ["auto", "dead"]]:
		var g := h.make_game()
		await h.settle()
		var manual: bool = c[0] == "manual"
		g.manual_respawn = manual
		g.cam.follow = "weak"
		g.cam.yaw = 0.0
		g.respawn = {"room": g.room_id, "pos": Vector3.ZERO, "yaw": PI / 2}
		var hold := {"move_x": 1.0}
		await h.run(g, 40, hold)
		if c[1] == "before":
			await h.run(g, 1, {"move_x": 1.0, "camera_reset": true})
			await h.run(g, 40, hold)
		var p: Player = g.player
		p.take_damage(9999, p.pos + Vector3(1, 0, 0), false, true)
		h.expect(p.dead, "やられた")
		# やられた画面は 1.3 秒で出る（そこでゲームは止まる）。自動の再開は 2 秒
		var until := 1.3 if manual else 2.0
		var pressed := false
		while p.dead and p.dead_time < until:
			var f := hold.duplicate()
			if c[1] == "dead" and not pressed and p.dead_time > until - 0.15:
				f["lock_on"] = true
				pressed = true
			await h.run(g, 1, f)
		if manual:
			g.request_respawn()
		h.expect(await h.run_until(g, 30, hold, func(): return not p.dead), "復活した")
		var turned := 0.0
		var prev := g.cam.yaw
		for i in 40:
			await h.run(g, 1, hold)
			turned += absf(U.wrap_angle(g.cam.yaw - prev))
			prev = g.cam.yaw
		var what := "%s の再開（背後のボタン：%s）" % [c[0], c[1]]
		h.expect(turned < 3.0 * U.DEG, "%s：復活のあと、カメラは回らない（%.0f°）" % [what, turned / U.DEG])
		h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - (g.cam.yaw - PI / 2)) / U.DEG, 0.0, 3.0, "%s：右へ倒したまま、復活したカメラの右へ走る" % what)
		h.free_game(g)


## 自動の回り込み（初期の「弱い」・「強い」）で、左スティックを斜め前・横・斜め後ろへ倒し続けても、カメラは回り続けない（左スティックでカメラが回らない）。
## 回り込むのは、ハルの進む向きとの差が不感帯（25°）の端になるまでで、その間は左スティックの基準を止める（ハルはまっすぐ走る）。
## 前は回ったカメラにつられて進む向きが回り、それをまた追って、「弱い」で 30〜48° に倒すと 1 秒に 43° ずつ回り続け、ハルは輪を描いて走った（2026-10-08）
func test_follow_does_not_spin_with_stick() -> void:
	var dead: float = float(TestHelpers.default_tuning().camera.autoRecenterDeadzone)
	for c in [["weak", 30.0], ["weak", 40.0], ["weak", 48.0], ["weak", 90.0], ["normal", 40.0], ["normal", 90.0], ["normal", 150.0]]:
		var g := h.make_game()
		await h.settle()
		g.cam.follow = c[0]
		g.cam.yaw = 0.0
		var ang: float = c[1]
		var a := -ang * U.DEG
		var hold := {"move_x": -sin(a), "move_y": cos(a)}
		var p: Player = g.player
		await h.run(g, 60, hold)
		var heading0 := U.dir_to_yaw(p.vel.x, p.vel.z)
		var turned := 0.0
		var prev := g.cam.yaw
		var worst := 0.0
		for i in 540:
			await h.run(g, 1, hold)
			turned += absf(U.wrap_angle(g.cam.yaw - prev))
			prev = g.cam.yaw
			worst = maxf(worst, absf(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0)))
		var may := maxf(0.0, ang - dead)
		if c[0] == "weak" and ang > CameraOrbit.FORWARD_ONLY:
			may = 0.0
		var what := "%s・左スティック %.0f°" % c
		h.expect(turned <= (may + 1.0) * U.DEG, "%s：カメラは不感帯の端まで回って止まる（10 秒で %.0f°、多くて %.0f°）" % [what, turned / U.DEG, may])
		h.expect(worst < 2.0 * U.DEG, "%s：ハルはまっすぐ走る（最大 %.1f° ずれた）" % [what, worst / U.DEG])
		h.free_game(g)


## 走りながら背後のボタン（ロックオンのボタンも）を押し、回している途中（0.35 秒より前）に左スティックを「前」へ倒し直しても、
## 回し終えてから倒し直したときと同じ：ハルはまっすぐ走り続け、カメラはハルの背後でぴたりと止まる（基準はカメラに戻る）。
## 前は回している途中の倒し直しを押す前のカメラから測ったので、カメラの方へ走りながら押して上へ倒し直すと、ハルが U ターンし、
## カメラは向きを変えたハルを追って戻り、背中から 36〜124° 外れた所で止まったまま（「弱い」は 50° より大きい差を追わない）だった（2026-10-08）
func test_recenter_reaim_during_swing() -> void:
	for btn in ["camera_reset", "lock_on"]:
		for stick0 in [Vector2(1, 0), Vector2(0, -1), Vector2(0.7071, -0.7071)]:
			for reaim_at in [4, 10, 16, 40]:
				var g := h.make_game()
				await h.settle()
				g.cam.follow = "weak"
				g.cam.yaw = 0.0
				await h.run(g, 40, {"move_x": stick0.x, "move_y": stick0.y})
				var p: Player = g.player
				var heading0 := U.dir_to_yaw(p.vel.x, p.vel.z)
				var gap0 := absf(U.wrap_angle(p.yaw - g.cam.yaw))
				var turned := 0.0
				var prev := g.cam.yaw
				var worst := 0.0
				for i in 70:
					var f := {"move_x": stick0.x, "move_y": stick0.y} if i < reaim_at else {"move_y": 1.0}
					if i == 0:
						f[btn] = true
					await h.run(g, 1, f)
					turned += absf(U.wrap_angle(g.cam.yaw - prev))
					prev = g.cam.yaw
					worst = maxf(worst, absf(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0)))
				var what := "%s・左スティック %s・%d 刻み目に前へ倒し直す" % [btn, stick0, reaim_at]
				h.expect(worst < 3.0 * U.DEG, "%s：ハルはまっすぐ走り続ける（最大 %.1f° ずれた）" % [what, worst / U.DEG])
				h.expect(turned < gap0 + 2.0 * U.DEG, "%s：カメラは背後まで回るだけ（%.0f°、押したときの差 %.0f°）" % [what, turned / U.DEG, gap0 / U.DEG])
				h.near(U.wrap_angle(p.yaw - g.cam.yaw) / U.DEG, 0.0, 1.0, "%s：カメラはハルの背後で止まる" % what)
				h.near(U.wrap_angle(g.cam.move_yaw() - g.cam.yaw), 0.0, 0.0001, "%s：基準はカメラに戻っている" % what)
				h.free_game(g)


## 自動の回り込み（初期の「弱い」）で、左スティックを斜め前へ倒したまま指で規則的に揺らしても、カメラは回り続けない
## （回り込みで基準を止めるのは、1 回倒すごとに 1 度だけ。CameraOrbit._follow_used）。
## 前は揺れて基準がカメラに戻るたびに、次の回り込みでまた止め直し、そのたびに 12〜21° ずつ回った分が積もって、
## 30°±10°（1 秒ごと）で 10 秒に 210°、40°±7°（0.5 秒ごと）で 430° 回り、ハルも同じだけ回って輪を描いた（2026-10-08）
func test_follow_wobble_does_not_spin() -> void:
	var dead: float = float(TestHelpers.default_tuning().camera.autoRecenterDeadzone)
	for c in [["weak", 30.0, 10.0, 1.0], ["weak", 30.0, 7.0, 0.5], ["weak", 40.0, 7.0, 0.5], ["weak", 40.0, 10.0, 1.0], ["normal", 60.0, 15.0, 1.0]]:
		var g := h.make_game({"boxes": [[Vector3(0, -0.5, 0), Vector3(3000, 1, 3000)]]})
		await h.settle()
		g.cam.follow = c[0]
		g.cam.yaw = 0.0
		var base: float = c[1]
		var amp: float = c[2]
		var period: float = c[3]
		var p: Player = g.player
		var cam_all := 0.0
		var cam_late := 0.0
		var body_late := 0.0
		var prev_c := g.cam.yaw
		var prev_b := p.yaw
		for i in 1200:
			var a: float = (-base + amp * sin(TAU * (i / 60.0) / period)) * U.DEG
			await h.run(g, 1, {"move_x": -sin(a), "move_y": cos(a)})
			var dc := U.wrap_angle(g.cam.yaw - prev_c)
			cam_all += dc
			if i >= 600:
				cam_late += dc
				body_late += U.wrap_angle(p.yaw - prev_b)
			prev_c = g.cam.yaw
			prev_b = p.yaw
		var what := "%s・左スティック %.0f°±%.0f°（%.1f 秒ごと）" % c
		h.expect(absf(cam_late) < 1.0 * U.DEG, "%s：10〜20 秒目にカメラは回らない（%.0f°）" % [what, cam_late / U.DEG])
		h.expect(absf(body_late) < 1.0 * U.DEG, "%s：10〜20 秒目にハルも回らない（輪を描かない。%.0f°）" % [what, body_late / U.DEG])
		h.expect(absf(cam_all) <= (base + amp - dead + 1.0) * U.DEG, "%s：20 秒で回ったのは不感帯の端まで（%.0f°）" % [what, absf(cam_all) / U.DEG])
		h.free_game(g)


## 左スティックの基準を止めている間（背後へ回している途中・自動の回り込みのあと）にロックオンで捉えても、ハルの進む向きは 1 刻みで跳ばない：
## 基準はカメラと同じ割合でロックオンの向きへ寄っていき、カメラに追いついたら止めるのをやめる（捉えている間は、ふだんどおりカメラから測る横歩き）。
## 前は捉えた刻みに基準をカメラへ戻したので、横へ走りながら押して、回している途中に敵を捉えると 42〜88°、
## 「強い」の回り込みで基準を止めていると 65° 跳んだ（2026-10-08）
func test_lock_catch_turns_basis_smoothly() -> void:
	var k := U.damp(TestHelpers.default_tuning().camera.lockOnYawSpeed, 1.0 / 60.0)
	# [名前, 回り込み, 敵の位置の作り方, 左スティック, 何刻み走ってからボタンを押し続けるか]
	var cases := []
	for bearing in [-100.0, -120.0, -150.0]:
		cases.append(["背後へ回している途中に捉える（%.0f°）" % bearing, "weak", Vector3(-4.3, 0, 0) + Vector3(sin(bearing * U.DEG), 0, cos(bearing * U.DEG)) * 15.0, Vector2(1, 0), 40])
	cases.append(["「強い」の回り込みのあと、カメラの前の敵を捉える", "normal", null, Vector2(1, 0), 240])
	cases.append(["「弱い」の回り込みのあと、カメラの前の敵を捉える", "weak", null, Vector2(0.7071, 0.7071), 240])
	for c in cases:
		var at: Vector3 = c[2] if c[2] != null else Vector3(0, 0, 60)
		var g := h.make_game({"markers": {"e1": at}, "placement": {"enemies": [{"type": "sentry", "at": "e1", "passive": true}]}})
		await h.settle()
		g.cam.follow = c[1]
		g.cam.yaw = 0.0
		var s: Vector2 = c[3]
		var hold := {"move_x": s.x, "move_y": s.y}
		await h.run(g, c[4], hold)
		var p: Player = g.player
		var e = g.enemies[0]
		if c[2] == null:
			# 敵をカメラの前 12m へ
			e.pos = p.pos + U.yaw_to_dir(g.cam.yaw) * 12.0
			g.phys.set_feet(e.body, e.pos)
			await h.run(g, 1, hold)
			h.expect(g.cam._hold != null, "%s：回り込みで基準を止めている" % c[0])
		var caught := -1
		var catch_ratio := 0.0
		var worst := 0.0
		for i in 120:
			var b0 := g.cam.move_yaw()
			var f := hold.duplicate()
			f["lock_on"] = true
			await h.run(g, 1, f)
			var b1 := g.cam.move_yaw()
			if g.lock_on.target != null:
				var want := U.dir_to_yaw(e.pos.x - p.pos.x, e.pos.z - p.pos.z)
				worst = maxf(worst, absf(U.wrap_angle(b1 - b0)) - k * absf(U.wrap_angle(want - b0)))
				if caught < 0:
					caught = i
					var full := absf(U.wrap_angle(g.cam.yaw - b0))
					catch_ratio = absf(U.wrap_angle(b1 - b0)) / maxf(full, 0.0001)
		h.expect(caught >= 0, "%s：捉えた" % c[0])
		h.expect(catch_ratio < 0.5, "%s：捉えた刻みに、基準はカメラとの差の半分も動かない（%.0f%%）" % [c[0], catch_ratio * 100.0])
		h.expect(worst < 0.2 * U.DEG, "%s：基準はカメラと同じ割合でしか寄らない（超えた分 %.2f°）" % [c[0], worst / U.DEG])
		h.near(U.wrap_angle(g.cam.move_yaw() - g.cam.yaw), 0.0, 0.0001, "%s：捉えている間に、基準はカメラに追いついた" % c[0])
		h.free_game(g)


## 台本の注視（camera。止めない演出）でカメラが自分で回っても、左スティックを変えなければ、ハルの進む向きは変わらない：
## 注視の間は左スティックの基準を止める（背後へ回すときと同じ。倒す向きを変えれば、変えた分だけ向きを変える）。
## 注視が終わっても、倒し直すか離すまでは止めたまま（離して倒し直すと、今のカメラから測る）。
## 前は基準がカメラと一緒に回り、r12 の動力の球を撃ったあとの注視（2.2 秒）で、後ろへ下がっていたハルが、98° 回るカメラにつられて
## −90° から 172° へ向きを変え、r11 への出口のそばから下の階へ落ちた（2026-10-08）
func test_camera_focus_keeps_heading() -> void:
	# [回り込み, 左スティック, 注視の途中で左スティックを回す量（度）]
	for c in [["weak", Vector2(0, -1), 0.0], ["normal", Vector2(1, 0), 0.0], ["off", Vector2(0, 1), 0.0], ["weak", Vector2(-0.7071, -0.7071), 0.0], ["weak", Vector2(0, -1), 45.0], ["normal", Vector2(1, 0), -60.0]]:
		var g := h.make_game({"boxes": [[Vector3(0, -0.5, 0), Vector3(3000, 1, 3000)]]})
		await h.settle()
		g.cam.follow = c[0]
		g.cam.yaw = PI / 2
		g.player.yaw = PI / 2
		var s: Vector2 = c[1]
		var p: Player = g.player
		await h.run(g, 40, {"move_x": s.x, "move_y": s.y})
		var heading0 := U.dir_to_yaw(p.vel.x, p.vel.z)
		var cam0 := g.cam.yaw
		# 台本の camera と同じ（Story）：カメラの向きから 100° 横、15m 先の点を 2.2 秒注視する
		g.cam_focus = p.pos + U.yaw_to_dir(cam0 - 100.0 * U.DEG) * 15.0 + Vector3(0, 2, 0)
		g.cam_focus_time = 2.2
		var turn: float = c[2] * U.DEG
		var worst := 0.0
		var cam_far := 0.0
		for i in 200:
			# 注視の途中（0.5〜1 秒目）で、左スティックを turn だけ回す
			var a := atan2(-s.x, s.y) + turn * clampf((i - 30) / 30.0, 0.0, 1.0)
			await h.run(g, 1, {"move_x": -sin(a), "move_y": cos(a)})
			var want := heading0 + turn * clampf((i - 30) / 30.0, 0.0, 1.0)
			worst = maxf(worst, absf(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - want)) if i < 30 or i > 75 else 0.0)
			worst = maxf(worst, absf(U.wrap_angle(g.cam.move_yaw() + a - want)))
			cam_far = maxf(cam_far, absf(U.wrap_angle(g.cam.yaw - cam0)))
		var what := "回り込み %s・左スティック %s・途中で %+.0f° 回す" % c
		h.expect(g.cam_focus == null, "%s：注視は終わった" % what)
		h.expect(cam_far > 60.0 * U.DEG, "%s：カメラは注視する点の方へ回った（%.0f°）" % [what, cam_far / U.DEG])
		h.expect(worst < 2.0 * U.DEG, "%s：ハルの進む向きは、左スティックを回した分だけ変わる（ずれ 最大 %.1f°）" % [what, worst / U.DEG])
		# 離して前へ倒し直すと、今のカメラから測る
		await h.run(g, 3, {})
		await h.run(g, 30, {"move_y": 1.0})
		h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - g.cam.yaw) / U.DEG, 0.0, 3.0, "%s：離して前へ倒し直すと、今のカメラの向きへ進む" % what)
		h.free_game(g)


## 背後へ回すボタンを、ほぼ真後ろ（170° より後ろ）へ倒して走りながら押し、そのあと左スティックを「遠回り」（回す先と逆の向き）へ
## ゆっくり回しても、ハルの進む向きは跳ばない：基準は遠回りのまま先（回す先）まで戻って、そこで止めるのをやめる（CameraOrbit._update_hold）。
## 回した量は刻みごとに足して測る（180° を越えて回しても、差が逆の符号に折り返さない）。
## 前は回した量が近回りの差に届いた刻みに、基準を近回りの先へ置き直したので、進む向きが 1 刻みで 2×(180°−差) 跳んだ
## （172° で 16°、175° で 10°。タッチのスティックは 10° 刻みに寄せないので、そのまま起きる。2026-10-08）
func test_reaim_long_way_no_jump() -> void:
	for a0 in [172.0, 175.0, 178.0, -172.0, -176.0]:
		for rate in [1.0, -1.0, 3.0, -3.0]:
			var g := h.make_game({"boxes": [[Vector3(0, -0.5, 0), Vector3(3000, 1, 3000)]]})
			await h.settle()
			g.cam.follow = "off"
			g.cam.yaw = 0.0
			g.player.yaw = 0.0
			await h.run(g, 3, {})
			var worst := 0.0
			var worst_at := -1
			var prev = null
			for i in 240:
				var a: float = (a0 + (rate * (i - 5) if i > 5 else 0.0)) * U.DEG
				var f := {"move_x": -sin(a), "move_y": cos(a)}
				if i == 0:
					f["camera_reset"] = true
				await h.run(g, 1, f)
				var head := U.wrap_angle(g.cam.move_yaw() + a)
				if prev != null and absf(U.wrap_angle(head - prev)) > worst:
					worst = absf(U.wrap_angle(head - prev))
					worst_at = i
				prev = head
			var what := "左スティック %.0f° で押し、%+.0f°／刻みで回す" % [a0, rate]
			h.expect(worst <= (2.0 * absf(rate) + 0.5) * U.DEG, "%s：進む向きは 1 刻みに、回した分の 2 倍より大きく跳ばない（%d 刻み目に %.1f°）" % [what, worst_at, worst / U.DEG])
			h.near(U.wrap_angle(g.cam.move_yaw() - g.cam.yaw), 0.0, 0.0001, "%s：基準はカメラに戻った" % what)
			h.free_game(g)
