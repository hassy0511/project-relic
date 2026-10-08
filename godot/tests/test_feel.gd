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


## 背後へ回している途中でロックオンが敵を捉えたら、回すのはやめる。外れたあとに残りの回転が基準なしで走って回り続けない
func test_recenter_cancelled_by_lock() -> void:
	var t := TestHelpers.default_tuning()
	var cam := CameraOrbit.new(t)
	cam.follow = "weak"
	cam.yaw = 0.0
	var dt := 1.0 / 60.0
	cam.request_recenter(PI / 2, Vector2(1, 0))
	cam.update(dt, Vector3.ZERO, PI / 2, 7.0, null)
	cam.update(dt, Vector3.ZERO, PI / 2, 7.0, Vector3(5, 0, 5))
	var y0 := cam.yaw
	for i in 30:
		cam.update(dt, Vector3.ZERO, PI / 2, 7.0, null)
	h.near(U.wrap_angle(cam.yaw - y0), 0.0, 0.0001, "捉えたあと外れても、回していた続きは走らない")
	h.near(U.wrap_angle(cam.move_yaw() - cam.yaw), 0.0, 0.0001, "左スティックの基準はカメラに戻っている")


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


## 背後へ回している途中で、部屋が変わったり（出口の手前で押した）台本の teleport が入ったりしても、そのあとカメラは回らない：
## 右へ倒したままなら、新しいカメラの右へ走る。カメラの向きを外から書き換えたら（部屋の読み込み・復活・台本の teleport・セーブの読み込み）、
## 回している続きも、止めていた左スティックの基準もやめる（CameraOrbit.yaw）。
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
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - (y0 - PI / 2)) / U.DEG, 0.0, 3.0, "%s：右へ倒したまま、新しいカメラの右へ走る" % what)
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
