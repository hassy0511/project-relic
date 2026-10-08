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
