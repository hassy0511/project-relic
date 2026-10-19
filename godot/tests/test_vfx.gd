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


## 層に今描いている板・粒の数（描いていない層は 0）
static func _layer_n(v: Vfx, layer: int) -> int:
	var l = v._layers[layer]
	return l.mm.visible_instance_count if l.mi.visible else 0


## 第 1 章の世界（world.json の部屋）のゲーム
func _world_game() -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	g.god_mode = true
	return g


## main と同じ順に 1 刻み：ゲーム → 出来事 → ハルの部品と見た目 → エフェクト。会話は決定で送る
func _tick(g: GameSim, fx: Fx, pv: PlayerView, i: int, input := {}) -> void:
	await h.tree.physics_frame
	var d := input.duplicate()
	if g.story.blocking():
		d["jump"] = (i % 6) < 3
	g.step(InputFrame.of(d))
	for e in g.drain_events():
		fx.handle(e)
	pv.set_frame_parts(g.has_ability("lock_on"), g.has_ability("sword"), g.has_ability("dash"))
	pv.sync(g.player, g, 1.0 / 60.0, U.yaw_to_dir(g.player.yaw))
	fx.sync(g, 1.0 / 60.0, pv, null)


## 台本の見た目の合図（fx の手順）：出来事 {type: "fx", id, part?, at?} を出すだけ（遊びは変えない）
func test_story_fx_cue() -> void:
	var g := h.make_game()
	await h.settle()
	var st := Story.new({}, {"cue": {"steps": [{"fx": "frame_fit", "part": "arm"}, {"fx": "node_memory", "pos": [1, 0, 2], "height": 3.0}]}}, g)
	st.start_event("cue")
	st.update(1.0 / 60.0)
	var fx_events := g.drain_events().filter(func(e): return e.type == "fx")
	h.expect(fx_events.size() == 2 and fx_events[0].id == "frame_fit" and fx_events[0].part == "arm" and not fx_events[0].has("at"),
		"フレームの装着の合図（部位つき）：%s" % str(fx_events))
	h.expect(fx_events.size() == 2 and fx_events[1].id == "node_memory" and fx_events[1].at.is_equal_approx(Vector3(1, 3, 2)),
		"ノードの記憶の合図（位置＋高さ）")
	h.expect(not st.running_event(), "合図の手順は待たない")
	h.free_game(g)


## フレームの装着は台本の合図で出す。駆動回廊は動力のフラグ（ピストン）が先に立つが、脚の部品は
## ナゴミの「動力の伝達を確認」の間は隠れていて、合図（そのあと）で光の粒が集まって現れ、「スラスターが起動」の会話の前に付いている
func test_frame_fit_waits_for_script_cue() -> void:
	var g := _world_game()
	await h.settle()
	for f in ["ch1.got_spark", "ch1.fell_to_b2", "ch1.frame_fitted", "ch1.blade_online", "ch1.first_beacon"]:
		g.set_flag(f)
	g.load_room("ch1.r12", "from_r11")
	for t in g.triggers:
		if t.id == "ch1.r12.enter":
			t.fired = true
	var pv := PlayerView.new()
	h.tree.root.add_child(pv)
	pv.load_model("res://assets/models/haru_r.glb")
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	for i in 8:
		await _tick(g, fx, pv, i)
	var legs: Node3D = pv.frame_nodes.get("legs")
	h.expect(legs != null and not legs.visible and not g.has_ability("dash"), "動力の前：脚の部品は無い")
	g.set_flag("switch.ch1.r12.s1")
	g.set_flag("switch.ch1.r12.s2")
	var hidden_while_powered := true
	var seen_powered := false
	var fit_particles := 0
	var shown_at_thrusters := false
	for i in 1500:
		await _tick(g, fx, pv, i)
		var did := String(g.story.dialogue.get("id", ""))
		if g.flag("ch1.drive_powered") and (did == "ch1.r12.powered" or not seen_powered):
			hidden_while_powered = hidden_while_powered and not legs.visible
		if did == "ch1.r12.powered":
			seen_powered = true
		if seen_powered and did == "" and fit_particles == 0 and fx._fit_wait.is_empty():
			fit_particles = fx.vfx.count()
		if did == "ch1.r12.thrusters":
			shown_at_thrusters = legs.visible
			break
	h.expect(seen_powered and hidden_while_powered, "動力が通ってから「動力の伝達を確認」が終わるまで、脚の部品は隠れている")
	h.expect(fit_particles > 15, "合図で脚に光の粒とかけらが集まる（%d 粒）" % fit_particles)
	h.expect(shown_at_thrusters, "「スラスターが起動」の会話の前に脚の部品が付いている")
	fx.queue_free()
	pv.queue_free()
	h.free_game(g)


## ノードの記憶は台本のノードの位置（炉心の下の段の窓の前）から流れ込む。ナゴミが「ch1.node」を話す間、カメラは横から炉心とハルを見る
func test_node_memory_from_script_position() -> void:
	var g := _world_game()
	await h.settle()
	for f in ["ch1.got_spark", "ch1.fell_to_b2", "ch1.frame_fitted", "ch1.blade_online", "ch1.first_beacon", "ch1.drive_powered",
			"ch1.shortcut_open", "ch1.diagnosis", "ch1.boss_defeated", "ch1.night"]:
		g.set_flag(f)
	g.load_room("ch1.r20", "from_r19")
	var pv := PlayerView.new()
	h.tree.root.add_child(pv)
	pv.load_model("res://assets/models/haru_r.glb")
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	for i in 4:
		await _tick(g, fx, pv, i)
	g.player.teleport(Vector3(0.9, 0, -6.3), 0.0)
	var started := false
	for i in 4000:
		await _tick(g, fx, pv, i)
		if String(g.story.dialogue.get("id", "")) == "ch1.node":
			started = true
			break
	h.expect(started, "炉心で再始動のイベントが進み、ナゴミが「ch1.node」を話し始める")
	h.expect(fx._node_t > 1.0 and fx._node_from.distance_to(Vector3(0, 3.05, 0.5)) < 0.01,
		"記憶の光は台本のノードの位置から出る（%s）" % str(fx._node_from))
	h.expect(g.cam_eye is Vector3 and g.cam_focus is Vector3, "話す間、カメラは台本の置き場所（横）から見る")
	for i in 30:
		await _tick(g, fx, pv, i)
	h.expect(fx.vfx.count() > 5, "ノードからナゴミへ光の点が流れる（%d 粒）" % fx.vfx.count())
	fx.queue_free()
	pv.queue_free()
	h.free_game(g)


## 解析：ナゴミの目から輪へ光の帯（扇）、終わると弱点へ光の線と照準の十字
func test_scan_beam() -> void:
	var g := h.make_game({"geometry": Arena.geometry(16.0), "placement": Arena.placement("sentry")})
	await h.settle()
	g.god_mode = true
	var e = g.enemies[0]
	for o in g.enemies:
		o.passive = true
	var ev := EnemyView.new()
	h.tree.root.add_child(ev)
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	g.player.teleport(e.pos + Vector3(0, 0, 6), PI)
	await _step(g, fx, ev, 20)
	h.expect(_layer_n(fx.vfx, Vfx.SOFT) == 0, "解析の前：光の帯は無い")
	await _step(g, fx, ev, 30, {"lock_on": true})
	var pr: float = g.lock_on.scan_progress()
	h.expect(g.lock_on.target != null and pr > 0.1 and pr < 1.0, "ロックオンして解析の途中（%.2f）" % pr)
	h.expect(_layer_n(fx.vfx, Vfx.SOFT) >= 2 and _layer_n(fx.vfx, Vfx.GRAIN) >= 3, "解析の間、扇と光の線が出る（扇 %d、線と光 %d）" % [_layer_n(fx.vfx, Vfx.SOFT), _layer_n(fx.vfx, Vfx.GRAIN)])
	await _step(g, fx, ev, 70, {"lock_on": true})
	var lines := 0
	for p in fx.vfx._layers[Vfx.GRAIN].parts:
		if p.mode == Vfx.STREAK and p.aspect > 15.0:
			lines += 1
	h.expect(fx._scan_done and lines >= 3, "解析が終わると、弱点へ光の線と十字（%d 本）" % lines)
	fx.queue_free()
	ev.queue_free()
	h.free_game(g)


## 盾の亀裂：守りを削るほど割れ目（芯の線）が増え、崩れると消える
func test_shield_crack() -> void:
	var g := h.make_game({"geometry": Arena.geometry(16.0), "placement": Arena.placement("shield")})
	await h.settle()
	g.god_mode = true
	var e = null
	for o in g.enemies:
		o.passive = true
		if o.kind == "shield":
			e = o
	var ev := EnemyView.new()
	h.tree.root.add_child(ev)
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	g.player.teleport(e.pos + e.forward() * 2.5, e.yaw + PI)
	await _step(g, fx, ev, 6)
	var none := _layer_n(fx.vfx, Vfx.DOT)
	g.damage_enemy(e, 10.0, g.player.pos, {"melee": true})
	await _step(g, fx, ev, 2)
	var few := _layer_n(fx.vfx, Vfx.DOT)
	g.damage_enemy(e, 20.0, g.player.pos, {"melee": true})
	await _step(g, fx, ev, 2)
	var many := _layer_n(fx.vfx, Vfx.DOT)
	h.expect(none == 0 and few >= 2 and many > few, "守りが減るほど割れ目が増える（%d → %d → %d）" % [none, few, many])
	g.damage_enemy(e, 20.0, g.player.pos, {"melee": true})
	await _step(g, fx, ev, 2)
	h.expect(e.state == "stunned" and _layer_n(fx.vfx, Vfx.DOT) == 0, "盾が崩れたら割れ目は消える（崩れのエフェクトに替わる）")
	fx.queue_free()
	ev.queue_free()
	h.free_game(g)


## 宝箱と遺物：開ける前の宝箱は縁と錠前が光り、開けて遺物を拾うと宝箱の所で光る（拾ったのは宝箱の中身）。
## ビーコンの定常の光は光柱の素材の筋
func test_chest_relic_and_beacon_glow() -> void:
	var g := _world_game()
	await h.settle()
	g.load_room("sample.vault", "from_hub")
	var pv := PlayerView.new()
	h.tree.root.add_child(pv)
	pv.load_model("res://assets/models/haru_r.glb")
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	for i in 6:
		await _tick(g, fx, pv, i)
	var chest = g.chests[0]
	h.expect(not chest.opened and _layer_n(fx.vfx, Vfx.DOT) >= 5, "開ける前の宝箱：合わせ目の線 4 本と錠前（%d）" % _layer_n(fx.vfx, Vfx.DOT))
	h.expect(_layer_n(fx.vfx, Vfx.PILLAR) >= 2, "ビーコンの定常の光（光柱の筋 %d）" % _layer_n(fx.vfx, Vfx.PILLAR))
	var front: Vector3 = chest.pos + U.yaw_to_dir(chest.yaw) * 1.2
	g.player.teleport(front, U.dir_to_yaw(chest.pos.x - front.x, chest.pos.z - front.z))
	var n0: int = g.relics.size()
	for i in 20:
		await _tick(g, fx, pv, i, {"jump": i == 10})
		if chest.opened:
			break
	await _tick(g, fx, pv, 0)
	h.expect(chest.opened and g.relics.size() == n0 + 1, "宝箱を開けて遺物を拾う")
	var near := 0
	for p in fx.vfx._layers[Vfx.GLINT].parts:
		if p.pos.distance_to(chest.pos + Vector3(0, 0.75, 0)) < 1.2:
			near += 1
	h.expect(near >= 6, "遺物の光は宝箱の所で出る（%d 粒）" % near)
	h.expect(_layer_n(fx.vfx, Vfx.DOT) == 0, "開けたあとは縁の光は消える")
	fx.queue_free()
	pv.queue_free()
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
