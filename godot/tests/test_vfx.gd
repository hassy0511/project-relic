extends RefCounted
## エフェクト（W2-09、scripts/view/vfx.gd・fx.gd）のテスト：粒の層の上限と片付け、混ぜ方、ゲームの出来事と状態から出ること。
## 見た目だけのもの。ゲームの中身（GameSim）は変えない

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func test_vfx_layers_cap_and_clear() -> void:
	var v := Vfx.new()
	h.tree.root.add_child(v)
	for i in 500:
		v.emit(Vfx.SPARK, Vector3.ZERO, Vector3.UP, 0.2, 0.1, 0.05, Color.WHITE)
	h.expect(v.count() == int(Vfx.LAYERS[Vfx.SPARK].max), "層の粒は上限まで（古い粒から消える）：%d" % v.count())
	v.sprite(Vfx.RING, Vector3.ZERO, 1.0, Color.WHITE)
	v.streak(Vfx.GRAIN, Vector3.ZERO, Vector3(0, 0, 2), 0.2, Color.WHITE)
	v.step(1.0 / 60.0)
	var shown := 0
	for c in v.get_children():
		if c is MultiMeshInstance3D and c.visible:
			shown += 1
			h.expect((c as MultiMeshInstance3D).multimesh.visible_instance_count > 0, "見せている層には粒がある")
	h.expect(shown == 3, "使った層だけを描く（3 層）：%d" % shown)
	v.step(0.5)
	v.step(1.0 / 60.0)
	shown = 0
	for c in v.get_children():
		if c is MultiMeshInstance3D and c.visible:
			shown += 1
	h.expect(v.count() == 0 and shown == 0, "寿命が来た粒と、その刻みだけの板は消え、空の層は描かない")
	v.queue_free()


## 層の中でいちばん明るい粒の明るさ（色のいちばん強い成分 × 濃さ）。Vfx.step のあとに読む
static func _peak(v: Vfx, layer: int) -> float:
	var l = v._layers[layer]
	var best := 0.0
	for i in l.mm.visible_instance_count:
		var o: int = i * 20
		best = maxf(best, maxf(l.buf[o + 12], maxf(l.buf[o + 13], l.buf[o + 14])) * l.buf[o + 15])
	return best


## フラッシュの強さ（設定の PadConfig.flash。main が毎刻み Fx・EnemyView・Hud へ入れる）：
## 大きな光（弱点の命中）は倍率どおり暗く、Vfx は足し合わせの明るい光の頭を抑える（暗い光・半透明の層はそのまま）。
## 番機の被弾の光と、被弾の画面の赤も弱まる
func test_flash_scale() -> void:
	# Fx：弱点の命中の閃き（大きな光）
	var peaks := []
	for fl in [1.0, 0.5, 0.2]:
		var fx := Fx.new()
		h.tree.root.add_child(fx)
		fx.flash_scale = fl
		h.expect(fx.vfx.flash_scale == fl, "Fx のフラッシュの強さが Vfx にも入る（%.1f）" % fl)
		fx.handle({"type": "hit", "at": Vector3(0, 1, 0), "kind": "weak"})
		fx.vfx.step(1.0 / 60.0)
		peaks.append(_peak(fx.vfx, Vfx.GLINT))
		fx.queue_free()
	h.expect(peaks[0] > 0.9 and peaks[1] < peaks[0] * 0.55 and peaks[2] < peaks[0] * 0.25,
		"弱点の閃きは 標準 %.2f → 弱め %.2f → 最小 %.2f と暗くなる" % peaks)
	# Vfx：明るい光の頭だけを縮める
	var v := Vfx.new()
	h.tree.root.add_child(v)
	v.flash_scale = 0.2
	v.sprite(Vfx.GLINT, Vector3.ZERO, 1.0, Color(2.0, 1.2, 0.3, 1.0))
	v.sprite(Vfx.GRAIN, Vector3.ZERO, 1.0, Color(0.5, 0.3, 0.1, 1.0))
	v.sprite(Vfx.SMOKE, Vector3.ZERO, 1.0, Color(0.9, 0.9, 0.9, 1.0))
	var q := v.emit(Vfx.SPARK, Vector3.ZERO, Vector3.UP, 1.0, 0.1, 0.1, Color(1.5, 1.0, 0.5, 1.0))
	q.fin = 0.001
	v.step(1.0 / 60.0)
	h.near(_peak(v, Vfx.GLINT), Vfx.FLASH_KNEE + (2.0 - Vfx.FLASH_KNEE) * 0.2, 0.01, "明るい光（2.0）は上限の所から先を 2 割に")
	h.near(_peak(v, Vfx.GRAIN), 0.5, 0.001, "暗い光（0.5）はそのまま")
	h.near(_peak(v, Vfx.SMOKE), 0.9, 0.001, "半透明の層（煙）はそのまま")
	h.expect(_peak(v, Vfx.SPARK) < 0.85, "寿命のある粒も抑える（1.47 → %.2f）" % _peak(v, Vfx.SPARK))
	v.flash_scale = 1.0
	v.sprite(Vfx.GLINT, Vector3.ZERO, 1.0, Color(2.0, 1.2, 0.3, 1.0))
	v.step(1.0 / 60.0)
	h.near(_peak(v, Vfx.GLINT), 2.0, 0.001, "標準では抑えない")
	v.queue_free()
	# 被弾の画面の赤
	var hud := Hud.new()
	h.tree.root.add_child(hud)
	await h.tree.process_frame
	hud.flash_damage()
	var full := hud.damage_alpha()
	hud.flash_scale = 0.2
	h.expect(full > 0.2 and hud.damage_alpha() < full * 0.25, "被弾の画面の赤も弱まる（%.2f → %.2f）" % [full, hud.damage_alpha()])
	hud.queue_free()
	# 番機の被弾の光（白磁の殻）
	var g := h.make_game({"geometry": Arena.geometry(16.0), "placement": Arena.placement("sentry")})
	await h.settle()
	var ev := EnemyView.new()
	h.tree.root.add_child(ev)
	var e = g.enemies[0]
	e.flash = 1.0
	ev.sync(g.enemies, 1.0 / 60.0)
	var b = ev._built.get(e)
	var lit: float = b.shell.emission.r
	ev.flash_scale = 0.2
	ev.sync(g.enemies, 1.0 / 60.0)
	h.expect(lit > 0.9 and b.shell.emission.r < 0.25, "番機の被弾の光も弱まる（%.2f → %.2f）" % [lit, b.shell.emission.r])
	ev.queue_free()
	h.free_game(g)


func test_vfx_no_multiply_blend() -> void:
	for path in ["res://assets/shaders/vfx_add.gdshader", "res://assets/shaders/vfx_mix.gdshader"]:
		var modes := ""
		for line in FileAccess.get_file_as_string(path).split("\n"):
			if line.strip_edges().begins_with("render_mode"):
				modes += line
		h.expect(modes != "" and not modes.contains("blend_mul"), "%s は掛け算の混ぜ方を使わない（gl_compatibility で黒くなる）" % path.get_file())
	h.expect(FileAccess.get_file_as_string("res://assets/shaders/vfx_add.gdshader").contains("blend_add"), "光の層は足し合わせ")


## ゲームを n 刻み進め、main と同じ順に見た目へ渡す（出来事 → 番機の見た目 → エフェクト）
func _step(g: GameSim, fx: Fx, ev: EnemyView, n: int, input := {}) -> void:
	for i in n:
		await h.tree.physics_frame
		g.step(InputFrame.of(input))
		for e in g.drain_events():
			fx.handle(e)
		ev.sync(g.enemies, 1.0 / 60.0)
		fx.sync(g, 1.0 / 60.0, null, ev)


func test_fx_follows_game() -> void:
	var g := h.make_game({"geometry": Arena.geometry(16.0), "placement": Arena.placement("kannuki")})
	await h.settle()
	g.god_mode = true
	var ev := EnemyView.new()
	h.tree.root.add_child(ev)
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	await _step(g, fx, ev, 150)
	var b = g.boss
	# 撃つ：銃口の光と弾
	await _step(g, fx, ev, 3, {"fire": true})
	h.expect(fx.vfx.count() > 0, "撃つと粒が出る（銃口の光）")
	# 命中の 3 種と撃破
	for k in ["normal", "weak", "armor"]:
		fx.handle({"type": "hit", "at": b.axis_center(), "kind": k})
	fx.handle({"type": "guardBroken", "at": Vector3(0, 1, 3)})
	fx.handle({"type": "enemyDestroyed", "at": Vector3(2, 1, 2)})
	fx.handle({"type": "playerHurt", "amount": 5.0})
	await _step(g, fx, ev, 1)
	h.expect(fx.vfx.count() > 20, "命中・盾・撃破・被弾の粒が出る（%d）" % fx.vfx.count())
	# 叩きつけ：輪の低い壁は輪が広がる間だけ
	b.debug_set_phase(2)
	b.set_state("slam_windup")
	var seen_band := false
	for i in 120:
		await _step(g, fx, ev, 1)
		if b.wave_r > 0.0:
			seen_band = seen_band or fx._band.visible
	h.expect(seen_band, "叩きつけの輪の間、低い光の壁が出る")
	await _step(g, fx, ev, 200)
	h.expect(b.wave_r > 0.0 or not fx._band.visible, "輪が消えると光の壁も消える")
	h.expect(not ev._haz.has("wave"), "古い輪（毎刻み作り直す TorusMesh）は使わない")
	# 撃破：錠前核は光ったまま残る
	b.debug_set_phase(3)
	b.core_open = true
	var guard := 0
	while b.alive and guard < 100:
		g.damage_enemy(b, 60.0, g.player.pos, {"melee": true, "at": b.axis_center()})
		guard += 1
	await _step(g, fx, ev, 60)
	var built = ev._built.get(b)
	h.expect(built != null and built.core.emission_enabled, "閂の錠前核は撃破のあとも光る")
	h.expect(not g.boss.alive, "閂を倒した")
	fx.queue_free()
	ev.queue_free()
	h.free_game(g)
