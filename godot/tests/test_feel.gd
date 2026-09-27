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
