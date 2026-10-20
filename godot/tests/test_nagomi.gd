extends RefCounted
## ナゴミの背中のユニットへの着地（view/nagomi_view.gd・Fx の光と煙）のテスト。見た目だけ（ゲームの中身は変えない）。
## 走る・ダッシュ・跳ぶ・斬るで背中へ、立つ・歩くと 0.6 秒で肩の横へ、話す・解析の間は肩の横、適合の前は出ない・胴のフレームが
## 隠れていれば付かない、行き来の弧は体の当たりの外（肩の上を回る）、会話のカメラ・部屋の移動・ポーズ・確かめ用の強制・台本の合図

var h: TestHelpers

const DT := 1.0 / 60.0
const HARU := "res://assets/models/haru_r.glb"


func _init(helpers: TestHelpers) -> void:
	h = helpers


# ---------------------------------------------------------------- 道具

## 平らな床のゲーム（opts は TestHelpers.make_game と同じ）と、ハルの見た目（haru_r）・ナゴミ・エフェクト。{g, pv, nv, fx}
func _setup(opts := {}) -> Dictionary:
	var g := h.make_game(opts)
	await h.settle()
	g.god_mode = true
	return _views(g)


func _views(g: GameSim) -> Dictionary:
	var pv := PlayerView.new()
	h.tree.root.add_child(pv)
	pv.load_model(HARU)
	var nv := NagomiView.new()
	h.tree.root.add_child(nv)
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	return {"g": g, "pv": pv, "nv": nv, "fx": fx, "talking": false}


func _free(r: Dictionary) -> void:
	for k in ["pv", "nv", "fx", "rig"]:
		if r.has(k):
			(r[k] as Node).queue_free()
	h.free_game(r.g)


## ふだんのカメラの場所（ハルの後ろ 5.5 m・上 2.5 m）
static func _cam(g: GameSim) -> Vector3:
	return g.player.pos - U.yaw_to_dir(g.cam.yaw) * 5.5 + Vector3(0, 2.5, 0)


## main と同じ順に 1 刻み：ゲーム → 出来事（Fx・ナゴミ）→ ハルの見た目 → ナゴミ → エフェクト
func _tick(r: Dictionary, input := {}) -> void:
	await h.tree.physics_frame
	var g: GameSim = r.g
	g.step(InputFrame.of(input))
	for e in g.drain_events():
		r.fx.handle(e)
		r.nv.handle(e)
	r.pv.set_frame_parts(g.has_ability("lock_on"), g.has_ability("sword"), g.has_ability("dash"))
	r.pv.sync(g.player, g, DT, U.yaw_to_dir(g.player.yaw))
	# 会話のカメラ（CameraRig）を使うときは main と同じく、前の刻みのカメラが寄っているかを渡してから、カメラを進める
	var rig: CameraRig = r.get("rig")
	r.nv.sync(g, rig.global_position if rig != null else _cam(g), DT, r.pv, rig.talk_weight() > 0.0 if rig != null else r.talking)
	r.fx.sync(g, DT, r.pv, null, r.nv)
	if rig != null:
		rig.sync(g, g.player.pos, DT, 0.0)


func _ticks(r: Dictionary, n: int, input = {}) -> void:
	for i in n:
		await _tick(r, input.call(i) if input is Callable else input)


## ハルの足元の座標（見た目の向き。+Z が正面、-X がハルの右）でのナゴミの中心
static func _local(r: Dictionary) -> Vector3:
	var pv: PlayerView = r.pv
	return Transform3D(Basis(Vector3.UP, pv.rotation.y), pv.global_position).affine_inverse() * (r.nv as NagomiView).global_position


## ナゴミと体の当たりのすき間（m。負ならめり込み）
static func _gap(r: Dictionary) -> float:
	var pv: PlayerView = r.pv
	var nv: NagomiView = r.nv
	var fr := Transform3D(Basis(Vector3.UP, pv.rotation.y), pv.global_position)
	return NagomiView.body_gap(fr.affine_inverse() * nv.global_position, nv.body_caps(fr))


## until が真になるまで（max 刻みまで）進める。返り値：かかった刻み（ならなければ -1）
func _until(r: Dictionary, max_ticks: int, input, until: Callable) -> int:
	for i in max_ticks:
		await _tick(r, input.call(i) if input is Callable else input)
		if until.call():
			return i + 1
	return -1


func _state(r: Dictionary) -> int:
	return (r.nv as NagomiView).dock_state


## 走って背中に付ける（付くまで）
func _dock_by_running(r: Dictionary) -> int:
	return await _until(r, 90, {"move_y": 1.0}, func(): return _state(r) == NagomiView.Dock.DOCKED)


## 止まって肩の横に出す（出るまで）
func _out_by_standing(r: Dictionary) -> int:
	return await _until(r, 150, {}, func(): return _state(r) == NagomiView.Dock.OUT)


## 会話を足して始める（話し手 who の 1 行）
static func _say(g: GameSim, id: String, who: String) -> void:
	g.story._dialogues[id] = {"lines": [{"who": who, "face": "happy", "text": "テスト"}]}
	g.story.start_dialogue(id)


## 会話を送り終える（全文を出して次へ）
static func _close(g: GameSim) -> void:
	for i in 6:
		if g.story.dialogue.is_empty():
			return
		g.story.confirm()


# ---------------------------------------------------------------- 受け口

func test_nagomi_seat_matches_model() -> void:
	# 受け口の定数（SOCKET_POS・SOCKET_OUT）が haru_r の胴のフレームの背中の板の外の面に合い、付いたナゴミの殻が体・フレームに
	# めり込まない（基準の姿勢）。骨の姿勢から求めた受け口も同じ所
	var pv := PlayerView.new()
	h.tree.root.add_child(pv)
	pv.load_model(HARU)
	pv.skeleton.reset_bone_poses()
	var core := pv.frame_nodes.get("core") as MeshInstance3D
	h.expect(core != null and pv.frame_shown("core"), "haru_r に胴のフレーム（Frame_core）があり、既定は見えている")
	var to_model := pv.model.global_transform.affine_inverse()
	var zmin := INF
	var ys: Array[float] = []
	var m := to_model * core.global_transform
	for s in core.mesh.get_surface_count():
		for v in core.mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]:
			var p: Vector3 = m * v
			if absf(p.x) < 0.04 and p.y > 1.03 and p.y < 1.12:
				zmin = minf(zmin, p.z)
	h.near(zmin, NagomiView.SOCKET_POS.z, 0.006, "背中の板の外の面（いちばん後ろ）の前後の位置")
	var seat := NagomiView.SOCKET_POS + NagomiView.socket_basis(NagomiView.SOCKET_OUT).z * NagomiView.SEAT
	var dmin := INF
	for mi in pv.meshes:
		var mm := to_model * mi.global_transform
		for s in mi.mesh.get_surface_count():
			for v in mi.mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]:
				dmin = minf(dmin, seat.distance_to(mm * v))
	h.expect(dmin > 0.12, "付いたナゴミ（殻の球 0.1245 m・背面 0.1195 m）は体・フレームから離れている（いちばん近い頂点 %.4f m）" % dmin)
	var nv := NagomiView.new()
	h.tree.root.add_child(nv)
	var sock = nv.back_socket(pv)
	h.expect(sock is Transform3D, "胴のフレームが見えていれば受け口がある")
	if sock is Transform3D:
		var o: Vector3 = to_model * sock.origin
		h.expect(o.distance_to(NagomiView.SOCKET_POS) < 0.002 and (to_model.basis * sock.basis.z).dot(NagomiView.SOCKET_OUT) > 0.999,
			"骨の基準の姿勢の受け口は定数と同じ（%s）" % o)
	pv.set_frame_parts(false, true, true)
	h.expect(nv.back_socket(pv) == null, "胴のフレームを隠すと受け口は無い")
	pv.set_frame_parts(true, true, true)
	pv.reveal_later("core", 1.0)
	h.expect(nv.back_socket(pv) == null, "装着の演出で隠している間も受け口は無い")
	nv.free()
	pv.free()
	# 骨・群の無いモデル（MVP の仮）には付かない
	var px := PlayerView.new()
	h.tree.root.add_child(px)
	px.load_model("res://assets/models/haru_proxy.glb")
	var nv2 := NagomiView.new()
	h.tree.root.add_child(nv2)
	h.expect(nv2.back_socket(px) == null, "胴のフレームの群の無いモデルには受け口が無い")
	nv2.free()
	px.free()


# ---------------------------------------------------------------- 背中へ

func test_nagomi_docks_when_running_or_dashing() -> void:
	var r := await _setup()
	var g: GameSim = r.g
	var nv: NagomiView = r.nv
	await _ticks(r, 60)
	h.expect(nv.visible and _state(r) == NagomiView.Dock.OUT, "立っている間は肩の横")
	h.expect(_local(r).distance_to(Vector3(-0.40, 1.32, -0.08)) < 0.06, "ハルの右肩の横（%s）" % _local(r))
	# 走る：0.1 秒走ったら背中へ向かい、0.3〜0.45 秒の弧で付く
	var start := -1
	var done := -1
	var prev_pos := nv.global_position
	var step_min := INF
	var step_max := 0.0
	for i in 60:
		await _tick(r, {"move_y": 1.0})
		if start < 0 and _state(r) == NagomiView.Dock.DOCKING:
			start = i + 1
		if done < 0 and _state(r) == NagomiView.Dock.DOCKED:
			done = i + 1
		var step := nv.global_position.distance_to(prev_pos)
		prev_pos = nv.global_position
		if i >= 12:
			step_min = minf(step_min, step)
			step_max = maxf(step_max, step)
	h.expect(start > 0 and start <= 16, "走り出して約 0.2 秒で背中へ向かう（%d 刻み）" % start)
	h.between((done - start) * DT, 0.3, 0.45, "背中へ入る弧の秒数")
	h.expect(step_min > 0.06 and step_max < 0.2, "走る間（7 m/s、1 刻み 0.117 m）、ナゴミは止まらず跳ばずに動く（1 刻み %.3f〜%.3f m）" % [step_min, step_max])
	var sock = nv.back_socket(r.pv)
	h.expect(sock is Transform3D and nv.global_position.distance_to(NagomiView.seat_of(sock)) < 0.003,
		"走っている間は背中の板の受け口に付いている（%.4f m）" % (nv.global_position.distance_to(NagomiView.seat_of(sock)) if sock is Transform3D else -1.0))
	h.expect(nv.dock_k == 1.0, "付いている（殻を閉じる・光を背中へ）")
	var closed := true
	for i in nv.shells.size():
		closed = closed and nv.shells[i].transform.is_equal_approx(nv.shell_rest[i])
	h.expect(closed, "殻 4 枚が閉じている")
	h.expect(nv.global_basis.z.dot(-U.yaw_to_dir(g.player.yaw)) > 0.9, "種子光（正面）はハルの後ろを向く")
	h.expect(nv.glow.position.z < 0.0 and nv.glow.light_energy > 0.15 and nv.core_mat.emission_energy_multiplier > 0.5,
		"核は灯ったまま、小さな光が背中の側から背中の板を照らす（%.2f）" % nv.glow.light_energy)
	# 立つ → 肩の横 → ダッシュ・跳ぶ・斬るはすぐ背中へ
	for act in [{"dash": true}, {"jump": true}, {"sword": true}]:
		await _out_by_standing(r)
		await _ticks(r, 30)
		h.expect(_state(r) == NagomiView.Dock.OUT, "%s の前は肩の横" % act.keys()[0])
		var n := await _until(r, 6, func(i): return act if i < 2 else {}, func(): return _state(r) == NagomiView.Dock.DOCKING)
		h.expect(n > 0 and n <= 2, "%s ですぐ背中へ向かう（%d 刻み）" % [act.keys()[0], n])
		await _ticks(r, 30)
	# 3 段斬りの間は背中のまま（連打）
	await _out_by_standing(r)
	await _ticks(r, 20)
	var kept := true
	var seen := 0
	for i in 70:
		await _tick(r, {"sword": i % 8 < 2})
		if g.player.attack != null and i > 30:
			seen += 1
			kept = kept and (_state(r) == NagomiView.Dock.DOCKED or _state(r) == NagomiView.Dock.DOCKING)
	h.expect(seen > 10 and kept, "3 段斬りの間は背中（%d 刻み見た）" % seen)
	# 溜め斬り：押し続ける（1 段目のあと、光刃を溜めている間も背中）→ 離すと溜め斬り
	await _out_by_standing(r)
	await _ticks(r, 30)
	var held_ok := true
	var held_seen := 0
	for i in 50:
		await _tick(r, {"sword": true})
		if g.player.attack == null and g.player.sword_hold > 0.25:
			held_seen += 1
			held_ok = held_ok and (_state(r) == NagomiView.Dock.DOCKED or _state(r) == NagomiView.Dock.DOCKING)
	h.expect(held_seen > 10 and held_ok, "光刃を溜めている間は背中（%d 刻み）" % held_seen)
	await _tick(r, {})
	h.expect(g.player.attack != null and g.player.attack.move == "charge" and _state(r) == NagomiView.Dock.DOCKED, "溜め斬りの間は背中")
	# ゆっくり歩く（2.1 m/s）間は肩の横のまま
	await _out_by_standing(r)
	var stayed := true
	for i in 90:
		await _tick(r, {"move_y": 0.3})
		stayed = stayed and _state(r) == NagomiView.Dock.OUT
	h.expect(stayed and g.player.speed() > 1.0, "歩いている間は肩の横のまま（%.1f m/s）" % g.player.speed())
	# スティックを一瞬（7 刻み。走る速さを超えるのは 3 刻み）倒しただけでは入らない
	await _ticks(r, 30)
	var blip := true
	var fast_ticks := 0
	for i in 30:
		await _tick(r, {"move_y": 1.0} if i < 7 else {})
		if g.player.speed() > NagomiView.FAST_SPEED:
			fast_ticks += 1
		blip = blip and _state(r) == NagomiView.Dock.OUT
	h.expect(blip and fast_ticks > 0, "一瞬だけ倒したくらいでは背中へ入らない（走る速さ %d 刻み）" % fast_ticks)
	_free(r)


# ---------------------------------------------------------------- 肩の横へ

func test_nagomi_out_after_standing() -> void:
	var r := await _setup()
	var g: GameSim = r.g
	var nv: NagomiView = r.nv
	await _ticks(r, 30)
	h.expect(await _dock_by_running(r) > 0, "走って背中に付く")
	await _ticks(r, 20, {"move_y": 1.0})
	# 止まる：減速して 0.6 秒たつまでは背中、そこから 0.3〜0.45 秒の弧で肩の横へ
	var calm_at := -1
	var start := -1
	var done := -1
	var cues := 0
	for i in 120:
		await _tick(r, {})
		if calm_at < 0 and NagomiView.motion_kind(g.player) == 0:
			calm_at = i + 1
		if start < 0 and _state(r) == NagomiView.Dock.UNDOCKING:
			start = i + 1
			cues = r.fx.vfx._layers[Vfx.SMOKE].parts.size()
		if done < 0 and _state(r) == NagomiView.Dock.OUT:
			done = i + 1
	h.between((start - calm_at) * DT, 0.55, 0.65, "止まってから約 0.6 秒で背中を離れる")
	h.between((done - start) * DT, 0.28, 0.4, "肩の横へ出る弧の秒数")
	h.expect(cues >= 4, "離れるとき背中に小さな煙（%d 粒）" % cues)
	await _ticks(r, 30)
	h.expect(_local(r).distance_to(Vector3(-0.40, 1.32, -0.08)) < 0.05, "出たあとは右肩の横（%s）" % _local(r))
	h.expect(nv.dock_k == 0.0 and nv.glow.position.z > 0.1, "殻と光はふだんどおり")
	_free(r)


func test_nagomi_out_while_speaking() -> void:
	var r := await _setup()
	var g: GameSim = r.g
	await _ticks(r, 30)
	await _dock_by_running(r)
	await _ticks(r, 10, {"move_y": 1.0})
	# ほかの人の会話の行の間（世界が止まる）：背中のまま
	_say(g, "t.h", "ハル")
	await _ticks(r, 60)
	h.expect(_state(r) == NagomiView.Dock.DOCKED, "ハルが話している間は背中のまま")
	_close(g)
	# ナゴミが話す：すぐ肩の横へ出る（会話の間、世界は止まっていてハルは走る速さのまま）
	_say(g, "t.n", "ナゴミ")
	var n := await _until(r, 40, {}, func(): return _state(r) == NagomiView.Dock.OUT)
	h.expect(n > 0 and n <= 30 and not g.story.dialogue.is_empty(), "ナゴミが話すと肩の横へ出る（%d 刻み）" % n)
	h.expect((r.nv as NagomiView).emotion == "happy", "話す行の顔（happy）")
	_close(g)
	await _ticks(r, 4, {"move_y": 1.0})
	h.expect(await _dock_by_running(r) > 0, "話し終えて走ると背中へ")
	# 会話のカメラが寄っている間は、ナゴミが話しても背中のまま（構図を崩さない）
	r.talking = true
	_say(g, "t.n2", "ナゴミ")
	await _ticks(r, 60)
	h.expect(_state(r) == NagomiView.Dock.DOCKED, "会話のカメラの間は、ナゴミが話しても背中のまま")
	_close(g)
	await _ticks(r, 60)
	h.expect(_state(r) == NagomiView.Dock.DOCKED, "会話のカメラが戻りきるまでは背中のまま")
	r.talking = false
	h.expect(await _out_by_standing(r) > 0, "会話のカメラが戻ると、立っていれば肩の横へ")
	_free(r)


func test_nagomi_keeps_dock_through_npc_talk() -> void:
	# 住人に話しかけた会話（TalkCamera.partner・会話のカメラ）：背中に付いたまま話しかけると、会話の間（ナゴミの行も）背中のまま。
	# 付いたナゴミは、会話のカメラから話し相手の顔までの線に掛からない
	var line := func(who: String, text: String) -> Dictionary: return {"who": who, "face": "normal", "text": text}
	var room := {"name": "t", "playerStart": "start", "geometry": [{"t": "box", "pos": [0, -1, 0], "size": [60, 1, 60]}],
		"markers": {"start": {"pos": [0, 0, 0], "yaw": 0}},
		"props": [{"type": "npc", "id": "npc_a", "name": "アオ", "pos": [0, 0, 4], "yaw": 180, "talk": "t.a"}],
		"enemies": [], "checkpoints": [], "triggers": []}
	var g := h.make_world_game({"start": {"room": "t.r", "spawn": "start"}, "areas": [{"id": "t", "name": "t", "rooms": {"r": room}}],
		"dialogues": {"t.a": {"lines": [line.call("アオ", "やあ"), line.call("ナゴミ", "ナゴミです"), line.call("アオ", "またね")]}},
		"events": {}})
	await h.settle()
	g.god_mode = true
	var r := _views(g)
	var rig := CameraRig.new()
	h.tree.root.add_child(rig)
	r["rig"] = rig
	await _ticks(r, 10)
	g.player.teleport(Vector3(0, 0, -6), 0.0)
	await _dock_by_running(r)
	# アオの前（1.6 m）へ置き直して、すぐ話しかける
	g.player.teleport(Vector3(0, 0, 2.4), 0.0)
	r.pv.position = g.player.pos
	r.nv.snap(g.player, r.pv)
	h.expect(_state(r) == NagomiView.Dock.DOCKED, "置き直しても背中のまま")
	await _tick(r, {"jump": true})
	h.expect(g.talk_npc == "npc_a" and TalkCamera.partner(g) != null, "話しかけた会話（会話のカメラを使う）")
	var kept := true
	var heard := false
	var clear := INF
	var npc = g.npcs[0]
	var face: Vector3 = npc.pos + Vector3(0, TalkCamera.face_height(npc.id), 0)
	for i in 400:
		if g.story.dialogue.is_empty():
			break
		heard = heard or g.story.dialogue.get("who", "") == "ナゴミ"
		kept = kept and _state(r) == NagomiView.Dock.DOCKED
		if rig.talk_weight() >= 1.0:
			var nvp: Vector3 = r.nv.global_position
			clear = minf(clear, Geometry3D.get_closest_point_to_segment(nvp, rig.global_position, face).distance_to(nvp))
		await _tick(r, {"jump": i % 30 == 29})
	h.expect(heard and kept, "会話の間はナゴミの行でも背中のまま")
	h.expect(clear < INF and clear > NagomiView.RADIUS + 0.05, "会話のカメラから顔までの線は、付いたナゴミに掛からない（いちばん近い %.2f m）" % clear)
	# 会話が終わってカメラが戻りきるまでは背中のまま、そのあと立っていれば肩の横へ
	var back_at := await _until(r, 120, {}, func(): return _state(r) == NagomiView.Dock.UNDOCKING)
	h.expect(back_at > 0 and rig.talk_weight() == 0.0, "会話のカメラが戻ってから肩の横へ出る（%d 刻み）" % back_at)
	_free(r)


func test_nagomi_out_while_analysing() -> void:
	# ロックオンの解析の間は、走っていても肩の横に出て相手の方へ少し寄る（解析の光の帯はナゴミから出る）。終わって少しすると背中へ
	var r := await _setup({"geometry": Arena.geometry(16.0), "placement": Arena.placement("sentry")})
	var g: GameSim = r.g
	var nv: NagomiView = r.nv
	var e = g.enemies[0]
	for o in g.enemies:
		o.passive = true
	g.player.teleport(e.pos + Vector3(0, 0, -7), 0.0)
	g.cam.yaw = 0.0
	await _ticks(r, 20)
	# 横へ走る（ロックオンの前）：背中
	h.expect(await _until(r, 60, {"move_x": 1.0}, func(): return _state(r) == NagomiView.Dock.DOCKED) > 0, "横へ走って背中に付く")
	var min_gap := INF
	var out_at := -1
	var lean := 0.0
	for i in 70:
		await _tick(r, {"move_x": 1.0, "lock_on": true})
		min_gap = minf(min_gap, _gap(r))
		if out_at < 0 and _state(r) == NagomiView.Dock.OUT:
			out_at = i + 1
		if i == 60:
			var shoulder := Transform3D(Basis(Vector3.UP, r.pv.rotation.y), r.pv.global_position) * Vector3(-0.40, 1.32, -0.08)
			lean = shoulder.distance_to(e.center()) - nv.global_position.distance_to(e.center())
	var pr: float = g.lock_on.scan_progress()
	h.expect(g.lock_on.target == e and pr > 0.3 and pr < 1.0 and g.player.speed() > NagomiView.FAST_SPEED,
		"周回しながら解析の途中（%.2f、%.1f m/s）" % [pr, g.player.speed()])
	h.expect(out_at > 0 and out_at <= 30 and _state(r) == NagomiView.Dock.OUT, "解析が始まると肩の横へ出る（%d 刻み）" % out_at)
	h.between(lean, 0.15, 0.4, "解析の間は相手の方へ寄る（m）")
	var eye: Vector3 = r.fx._nagomi_eye(g, e.center())
	h.expect(eye.distance_to(nv.global_position) < 0.15, "解析の光の帯はナゴミの目から出る")
	h.expect(min_gap > -0.006, "出る弧は体の当たりの外（いちばん近い %.3f m）" % min_gap)
	var docked := await _until(r, 120, {"move_x": 1.0, "lock_on": true}, func(): return _state(r) == NagomiView.Dock.DOCKING)
	h.expect(docked > 0 and g.lock_on.scan_progress() >= 1.0, "解析が終わって少しすると、走っていれば背中へ（%d 刻み）" % docked)
	_free(r)


# ---------------------------------------------------------------- 付かない

func test_nagomi_never_docked_before_fit() -> void:
	# 第 1 章の適合の前はいない（走っても跳んでも出ない・付かない）。胴のフレームが隠れていれば付かず、付いていれば離れる
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	g.god_mode = true
	g.set_flag("trigger.ch1.training.start")
	g.load_room("ch1.training")
	for t in g.triggers:
		t.fired = true
	await h.settle()
	var r := _views(g)
	var never := true
	for i in 120:
		await _tick(r, {"move_y": 1.0, "jump": i % 40 < 3})
		never = never and not r.nv.visible and _state(r) == NagomiView.Dock.OUT
	h.expect(never and not g.nagomi_present(), "適合の前は走っても跳んでも、ナゴミはいない・背中にも付かない")
	h.expect(r.nv.back_socket(r.pv) == null, "適合の前は胴のフレームが無く、受け口も無い")
	g.set_flag(GameSim.NAGOMI_JOIN_FLAG)
	await _ticks(r, 30)
	h.expect(r.nv.visible and _state(r) == NagomiView.Dock.OUT, "適合のあとは肩の横に出てくる")
	h.expect(await _dock_by_running(r) > 0, "適合のあとは走ると背中へ")
	_free(r)
	# 胴のフレームを隠す（装着の演出の間など）：付いていれば離れ、走っても付かない
	var r2 := await _setup()
	await _ticks(r2, 20)
	await _dock_by_running(r2)
	r2.pv.reveal_later("core", 10.0)
	var n := await _until(r2, 10, {"move_y": 1.0}, func(): return _state(r2) == NagomiView.Dock.UNDOCKING)
	h.expect(n > 0 and n <= 2, "胴のフレームを隠すと背中を離れる")
	var stay := true
	for i in 90:
		await _tick(r2, {"move_y": 1.0, "jump": i % 30 == 0})
		if i > 30:
			stay = stay and _state(r2) == NagomiView.Dock.OUT
	h.expect(stay, "胴のフレームが隠れている間は、走っても跳んでも付かない")
	_free(r2)


# ---------------------------------------------------------------- 弧

func test_nagomi_path_stays_outside_body() -> void:
	# 行き来の弧（と肩の横でついて行く動き）は、ナゴミの殻（半径 0.125 m）が体の当たり（骨の今の姿勢の胴・肩・上腕・頭と髪）に
	# めり込まない。背中へは肩の上を回って上の後ろから下りる
	var r := await _setup()
	var g: GameSim = r.g
	await _ticks(r, 40)
	var worst := INF
	var worst_at := ""
	var rise := 0.0
	var behind := false
	var from_y := 0.0
	var cycles := 0
	# 走る → 止まる をくり返す（向きを変えながら。行きと帰りの弧）
	var dirs := [[0.0, 1.0], [1.0, 0.0], [-0.7, -0.7], [0.0, -1.0]]
	for d in dirs:
		var was := _state(r)
		for i in 150:
			var inp := {"move_x": d[0], "move_y": d[1]} if i < 60 else {}
			await _tick(r, inp)
			var s := _state(r)
			if s == NagomiView.Dock.DOCKING and was == NagomiView.Dock.OUT:
				from_y = _local(r).y
				cycles += 1
			if s == NagomiView.Dock.DOCKING:
				rise = maxf(rise, _local(r).y - from_y)
				behind = behind or (_local(r).z < -0.3 and absf(_local(r).x) < 0.35)
			var gp := _gap(r)
			if gp < worst:
				worst = gp
				worst_at = "%s %d：%s" % [str(d), i, NagomiView.Dock.keys()[s]]
			was = s
	h.expect(cycles == 4, "4 回付いて離れた（%d）" % cycles)
	h.expect(worst > -0.006, "弧と肩の横の動きは体の当たりの外（いちばん近い %.4f m、%s）" % [worst, worst_at])
	h.expect(rise > 0.06 and behind, "背中へは肩の上を回る（上がる %.2f m、後ろを通る %s）" % [rise, behind])
	# 肩の横で、その場で向きを変える（ゆっくり歩く向きを逆へ）：体を突き抜けずに後ろを回る
	var turn_worst := INF
	for k in 6:
		for i in 25:
			await _tick(r, {"move_y": 0.25 if k % 2 == 0 else -0.25, "move_x": 0.05})
			turn_worst = minf(turn_worst, _gap(r))
	h.expect(turn_worst > -0.006 and _state(r) == NagomiView.Dock.OUT, "向きを変えても肩の横のまま、体を通らない（%.4f m）" % turn_worst)
	# 歩いて遅れた所（ハルの後ろ）から背中へ
	await _ticks(r, 40, {"move_y": 0.48})
	var lag_worst := INF
	for i in 50:
		await _tick(r, {"move_y": 1.0})
		lag_worst = minf(lag_worst, _gap(r))
	h.expect(lag_worst > -0.006 and _state(r) == NagomiView.Dock.DOCKED, "遅れた所からでも体を通らずに背中へ（%.4f m）" % lag_worst)
	_free(r)


func test_nagomi_low_ceiling_and_wall() -> void:
	# 天井が低い所（1.62 m。ハルの背丈 1.55 m）・右肩の横が壁に埋まる所では、立っていても背中（肩の横に出る余地が無い）。
	# 余地のある所へ出れば 0.6 秒で肩の横へ。低い天井の下で話して出るときも、弧と肩の横は天井の下に収まる
	var ceil_y := 1.62
	var r := await _setup({"boxes": [[Vector3(0, ceil_y + 0.5, 8.0), Vector3(6, 1.0, 6)], [Vector3(-0.62, 1.0, -8.0), Vector3(0.3, 2.0, 4.0)]]})
	var g: GameSim = r.g
	var nv: NagomiView = r.nv
	await _ticks(r, 20)
	for spot in [[Vector3(0, 0, 8), "天井の低い所"], [Vector3(0, 0, -8), "右肩の横が壁の所"]]:
		# 開けた所で肩の横に出してから、その場所へ置き直す（置き直しても肩の横のまま）
		g.player.teleport(Vector3(6, 0, 0), 0.0)
		r.pv.position = g.player.pos
		nv.snap(g.player, r.pv)
		await _out_by_standing(r)
		g.player.teleport(spot[0], 0.0)
		g.cam.yaw = 0.0
		r.pv.position = g.player.pos
		nv.snap(g.player, r.pv)
		h.expect(_state(r) == NagomiView.Dock.OUT, "%s：置き直した刻みは肩の横" % spot[1])
		var n := await _until(r, 60, {}, func(): return _state(r) == NagomiView.Dock.DOCKED)
		h.expect(n > 0 and n <= 45, "%s：立っていても背中へ（%d 刻み）" % [spot[1], n])
		await _ticks(r, 90)
		h.expect(_state(r) == NagomiView.Dock.DOCKED, "%s：立ち続けても背中のまま" % spot[1])
	# 向きを変えて壁を左にすると、余地があるので肩の横へ
	g.player.teleport(Vector3(0, 0, -8), PI)
	r.pv.position = g.player.pos
	nv.snap(g.player, r.pv)
	h.expect(await _until(r, 90, {}, func(): return _state(r) == NagomiView.Dock.OUT) > 0, "壁を左にすると肩の横へ出る")
	# 低い天井の下でナゴミが話す：肩の横へ出る弧と、出たあとの位置は天井の下
	g.player.teleport(Vector3(0, 0, 8), 0.0)
	r.pv.position = g.player.pos
	nv.snap(g.player, r.pv)
	await _until(r, 60, {}, func(): return _state(r) == NagomiView.Dock.DOCKED)
	await _ticks(r, 10)
	_say(g, "t.low", "ナゴミ")
	var top := -INF
	for i in 50:
		await _tick(r, {})
		top = maxf(top, nv.global_position.y + NagomiView.RADIUS)
	h.expect(_state(r) == NagomiView.Dock.OUT and top < ceil_y, "低い天井の下でも、話すと出て、殻は天井の下（いちばん高い所 %.3f m）" % top)
	_close(g)
	_free(r)


# ---------------------------------------------------------------- そのまま・強制・台本

func test_nagomi_keeps_state_on_snap_and_pause() -> void:
	var r := await _setup()
	var g: GameSim = r.g
	var nv: NagomiView = r.nv
	await _ticks(r, 30)
	await _dock_by_running(r)
	# 部屋を移る・置き直す（main.snap_views と同じ）：背中のまま、受け口の所へ
	g.player.teleport(Vector3(20, 0, -15), 2.0)
	r.pv.position = g.player.pos
	nv.snap(g.player, r.pv)
	var sock = nv.back_socket(r.pv)
	h.expect(_state(r) == NagomiView.Dock.DOCKED and nv.global_position.distance_to(NagomiView.seat_of(sock)) < 0.003,
		"置き直しても背中に付いたまま")
	await _out_by_standing(r)
	await _ticks(r, 20)
	g.player.teleport(Vector3(-20, 0, 15), -1.0)
	r.pv.position = g.player.pos
	nv.snap(g.player, r.pv)
	h.expect(_state(r) == NagomiView.Dock.OUT and _local(r).distance_to(Vector3(-0.40, 1.32, -0.08)) < 0.03, "置き直しても肩の横のまま")
	# 弧の途中で置き直す：終わりの姿に
	await _until(r, 30, {"move_y": 1.0}, func(): return _state(r) == NagomiView.Dock.DOCKING)
	nv.snap(g.player, r.pv)
	h.expect(_state(r) == NagomiView.Dock.DOCKED, "背中へ向かう途中で置き直すと、付いた姿に")
	# ポーズ（main が刻みを止める）：弧の途中で止まり、戻ると続きから
	await _out_by_standing(r)
	await _ticks(r, 20)
	await _until(r, 30, {"move_y": 1.0}, func(): return _state(r) == NagomiView.Dock.DOCKING)
	await _ticks(r, 6, {"move_y": 1.0})
	var t0 := nv._t
	var p0 := nv.global_position
	for i in 60:
		await h.tree.physics_frame
	h.expect(nv._t == t0 and nv.global_position == p0, "ポーズの間は弧が止まる")
	await _tick(r, {"move_y": 1.0})
	h.between(nv._t - t0, 0.0, 0.1, "ポーズのあとは続きから")
	_free(r)


func test_nagomi_debug_force_and_script_cues() -> void:
	var r := await _setup()
	var g: GameSim = r.g
	var nv: NagomiView = r.nv
	await _ticks(r, 30)
	# 確かめ用の強制（-- --nagomi=dock|out）
	nv.force = "dock"
	h.expect(await _until(r, 60, {}, func(): return _state(r) == NagomiView.Dock.DOCKED) > 0, "force=dock：立っていても背中")
	await _ticks(r, 60)
	h.expect(_state(r) == NagomiView.Dock.DOCKED, "force=dock：立ち続けても背中のまま")
	nv.force = "out"
	await _ticks(r, 40)
	var out := true
	for i in 60:
		await _tick(r, {"move_y": 1.0, "dash": i == 20})
		out = out and _state(r) == NagomiView.Dock.OUT
	h.expect(out, "force=out：走ってもダッシュしても肩の横のまま")
	nv.force = ""
	await _dock_by_running(r)
	# 台本の合図（fx の手順）：nagomi_out → 走っていても肩の横、nagomi_dock → 立っていても背中、nagomi_at → その位置、
	# nagomi_auto・台本の終わり → ふだんの決め方
	g.player.teleport(Vector3.ZERO, 0.0)
	r.pv.position = g.player.pos
	nv.snap(g.player, r.pv)
	g.story._events["t.cue"] = {"steps": [{"fx": "nagomi_out"}, {"wait": 1.0}, {"fx": "nagomi_dock"}, {"wait": 1.0},
		{"fx": "nagomi_at", "pos": [1.2, 0, 0.6], "height": 1.4}, {"wait": 2.5}, {"fx": "nagomi_auto"}, {"wait": 1.5}]}
	g.story.start_event("t.cue")
	var n := await _until(r, 40, {"move_x": 0.6}, func(): return _state(r) == NagomiView.Dock.OUT)
	h.expect(n > 0 and g.player.speed() > NagomiView.FAST_SPEED, "nagomi_out：走っていても肩の横（%d 刻み）" % n)
	n = await _until(r, 120, {}, func(): return _state(r) == NagomiView.Dock.DOCKED)
	h.expect(n > 0, "nagomi_dock：立っていても背中（%d 刻み）" % n)
	n = await _until(r, 150, {}, func(): return _state(r) == NagomiView.Dock.OUT and nv.global_position.distance_to(Vector3(1.2, 1.4, 0.6)) < 0.08)
	h.expect(n > 0, "nagomi_at：台本の位置へ（%s）" % nv.global_position)
	await _ticks(r, 60)
	h.expect(nv.global_position.distance_to(Vector3(1.2, 1.4, 0.6)) < 0.08, "台本の位置にとどまる")
	n = await _until(r, 150, {"move_y": 1.0}, func(): return _state(r) == NagomiView.Dock.DOCKING)
	h.expect(n > 0 and g.story.running_event(), "nagomi_auto：ふだんの決め方（走ると背中へ。%d 刻み）" % n)
	await _ticks(r, 100)
	# 台本が戻さずに終わっても、終わればふだんの決め方
	g.story._events["t.cue2"] = {"steps": [{"fx": "nagomi_out"}, {"wait": 0.5}]}
	g.story.start_event("t.cue2")
	await _ticks(r, 20, {"move_y": 1.0})
	h.expect(_state(r) != NagomiView.Dock.DOCKED, "合図の間は出ている")
	await _ticks(r, 60, {"move_y": 1.0})
	h.expect(_state(r) == NagomiView.Dock.DOCKED and not g.story.running_event(), "台本が終われば、走っていれば背中へ")
	_free(r)


func test_nagomi_dock_click_glow() -> void:
	# 着いたとき琥珀の小さな光（click：核が明るくなり、Fx が閃きと背中の板の面の輪を描く。0.25 秒）
	var r := await _setup()
	var nv: NagomiView = r.nv
	var fx: Fx = r.fx
	await _ticks(r, 30)
	await _dock_by_running(r)
	h.expect(nv.click > 0.9, "着いた刻みに光る（%.2f）" % nv.click)
	var glint: int = fx.vfx._layers[Vfx.GLINT].mm.visible_instance_count
	var ring: int = fx.vfx._layers[Vfx.RING].mm.visible_instance_count
	h.expect(glint >= 1 and ring >= 1, "閃きと輪を描く（%d・%d）" % [glint, ring])
	var e0 := nv.core_mat.emission_energy_multiplier
	await _ticks(r, 20, {"move_y": 1.0})
	h.expect(nv.click == 0.0 and nv.core_mat.emission_energy_multiplier < e0, "0.25 秒で消える")
	_free(r)
