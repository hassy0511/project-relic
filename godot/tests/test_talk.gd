extends RefCounted
## 会話のカメラ（view/talk_camera.gd・CameraRig._update_talk）のテスト：住人に話しかけると話し相手の頭と上半身が見える構図へ寄せ、
## 会話のあとは話しかける前のカメラ（yaw・pitch）へ戻る。台本のカメラ・ナゴミの行・地の文・トリガーで始まった会話は今までどおり。
## 構図は地形・物の中に入らない（第 1 章の全部の住人のまわりで確かめる）

var h: TestHelpers

const DT := 1.0 / 60.0


func _init(helpers: TestHelpers) -> void:
	h = helpers


# ---------------------------------------------------------------- 道具

## 試しの部屋（40m 四方の床）：アオ（会話 t.a：ハル→アオ→ナゴミ→アオ）、台の奥のクロ（t.c）、台本のカメラで話すエミ（t.cam_talk）、
## ナゴミと地の文だけの会話のノノ（t.nagomi）、アオの会話を始めるトリガー（t.scene）。extra：足す形（RoomGeo の書き方）
func _game(extra: Array = [], props: Array = []) -> GameSim:
	var geo := [{"t": "box", "pos": [0, -1, 0], "size": [60, 1, 60]},
		# クロの台（上の面 1.1m）と、その上をふさぐ体だけを止める箱（町の露店と同じ。カメラは通す）
		{"t": "box", "pos": [10, 0, 3.8], "size": [4, 1.1, 0.8]},
		{"t": "box", "pos": [10, 1.1, 3.8], "size": [4, 3.0, 0.8], "cam": false}]
	geo.append_array(extra)
	# クロは雑貨屋の店主と同じ背丈（id で顔の高さが決まる：1.48m。台の上の品の高さ 1.55m より低い）
	var npcs := [{"type": "npc", "id": "npc_a", "name": "アオ", "pos": [0, 0, 4], "yaw": 180, "talk": "t.a"},
		{"type": "npc", "id": "npc_shopkeeper", "name": "クロ", "pos": [10, 0, 5], "yaw": 180, "talk": "t.c"},
		{"type": "npc", "id": "npc_e", "name": "エミ", "pos": [-10, 0, 4], "yaw": 180, "event": "t.cam_talk"},
		{"type": "npc", "id": "npc_n", "name": "ノノ", "pos": [-20, 0, 4], "yaw": 180, "talk": "t.nagomi"}]
	npcs.append_array(props)
	var room := {"name": "t", "playerStart": "start", "geometry": geo,
		"markers": {"start": {"pos": [0, 0, 0], "yaw": 0}},
		"props": npcs, "enemies": [], "checkpoints": [],
		"triggers": [{"id": "t.scene", "pos": [20, 0, 0], "size": [2, 3, 2], "event": "t.scene"}]}
	var line := func(who: String, text: String) -> Dictionary: return {"who": who, "face": "normal", "text": text}
	return h.make_world_game({"start": {"room": "t.r", "spawn": "start"}, "areas": [{"id": "t", "name": "t", "rooms": {"r": room}}],
		"dialogues": {
			"t.a": {"lines": [line.call("ハル", "こんにちは"), line.call("アオ", "やあ"), line.call("ナゴミ", "ナゴミです"), line.call("アオ", "またね")]},
			"t.c": {"lines": [line.call("クロ", "いらっしゃい"), line.call("ハル", "見るだけ")]},
			"t.e": {"lines": [line.call("エミ", "あれを見て")]},
			"t.nagomi": {"lines": [line.call("ナゴミ", "眠っているみたい"), line.call("", "ノノは寝息を立てている")]},
			"t.t": {"lines": [line.call("トト", "せまいね")]},
			"t.b": {"lines": [line.call("ブン", "壁の前だよ")]},
		},
		"events": {
			"t.cam_talk": {"steps": [{"camera": {"pos": [-10, 0, 14], "height": 1.5, "eye": [-13, 2.5, 8], "time": 4.0, "wait": false}},
				{"say": "t.e"}, {"camera": {}}]},
			"t.scene": {"steps": [{"say": "t.a"}]},
		}})


func _npc(g: GameSim, id: String):
	for n in g.npcs:
		if n.id == id:
			return n
	return null


func _rig(talk := true) -> CameraRig:
	var cam := CameraRig.new()
	cam.talk_enabled = talk
	h.tree.root.add_child(cam)
	return cam


## ハルを at に立たせて、住人の方を向かせる（カメラもその向き）
func _face(g: GameSim, at: Vector3, npc_id: String) -> void:
	var n = _npc(g, npc_id)
	var yaw := U.dir_to_yaw(n.pos.x - at.x, n.pos.z - at.z)
	g.player.teleport(at, yaw)
	g.cam.yaw = yaw


## 1 刻み進めて、カメラ（いくつでも）を合わせる
func _tick(g: GameSim, rigs: Array, input := {}) -> void:
	await h.tree.physics_frame
	g.step(InputFrame.of(input))
	for r in rigs:
		r.sync(g, g.player.pos, DT, 0.0)


func _ticks(g: GameSim, rigs: Array, n: int, input := {}) -> void:
	for i in n:
		await _tick(g, rigs, input)


## 会話を送り終える（押す・離すをくり返す）。input_key：送るボタン（jump：キーボード・パッド、confirm：スマホの窓のタップ）
func _finish_dialogue(g: GameSim, rigs: Array, input_key := "jump", extra := {}) -> void:
	for i in 600:
		if not g.story.blocking():
			return
		var f := extra.duplicate()
		if i % 6 < 3:
			f[input_key] = true
		await _tick(g, rigs, f)


## 話し相手の顔（中心）の、カメラ cam の画面の位置（TalkCamera._screen と同じ。x・y は中心 0、端 ±1）
func _on_screen(cam: CameraRig, x: Vector3, aspect := 16.0 / 9.0) -> Vector3:
	return TalkCamera._screen(cam.global_transform, x, tan(deg_to_rad(cam.fov) * 0.5), aspect)


func _face_point(n) -> Vector3:
	return n.pos + Vector3(0, TalkCamera.face_height(n.id), 0)


## 点 p が部屋の形（箱・床と壁の殻）の中に入っているか（当たり判定を使わずに、形のデータから確かめる）。
## terrain_only：体だけを止める形（"cam": false。ふだんのカメラは通り抜ける）は見ない
static func _inside_shapes(room: Dictionary, p: Vector3, pad := 0.0, terrain_only := false) -> String:
	for s in room.get("geometry", []):
		if terrain_only and not s.get("cam", true):
			continue
		var t := String(s.get("t", "box"))
		if t == "box":
			var pos := RoomGeo.v3(s.pos)
			var size := RoomGeo.v3(s.size)
			var l := Basis(Vector3.UP, -float(s.get("yaw", 0.0)) * U.DEG) * (p - (pos + Vector3(0, size.y * 0.5, 0)))
			if absf(l.x) < size.x * 0.5 + pad and absf(l.y) < size.y * 0.5 + pad and absf(l.z) < size.z * 0.5 + pad:
				return "box %s" % str(s.pos)
		elif t == "shell":
			# 殻の内側（床の上・壁の内側・天井の下）から出ていないか
			var pos := RoomGeo.v3(s.pos)
			var size := RoomGeo.v3(s.size)
			var d := p - pos
			var inside_xz := absf(d.x) < size.x * 0.5 + 1.0 and absf(d.z) < size.z * 0.5 + 1.0
			if inside_xz and (absf(d.x) > size.x * 0.5 - pad or absf(d.z) > size.z * 0.5 - pad or d.y < pad
					or (s.get("ceiling", false) and d.y > size.y - pad)):
				# 出入口の開口の中は通れる
				if not _in_opening(s, pos, size, d):
					return "shell %s" % str(s.pos)
	return ""


static func _in_opening(s: Dictionary, pos: Vector3, size: Vector3, d: Vector3) -> bool:
	for o in s.get("openings", []):
		var along := d.x if o.side in ["n", "s"] else d.z
		var at := float(o.get("at", 0.0))
		var w := float(o.get("w", 2.5))
		var y0 := float(o.get("y", 0.0))
		if absf(along - at) < w * 0.5 and d.y > y0 and d.y < y0 + float(o.get("h", 3.5)):
			return true
	return false


# ---------------------------------------------------------------- 寄せる・戻す

func test_talk_camera_frames_speaker() -> void:
	# アオの正面 1.8m に立って話しかける：0.4〜0.6 秒で会話の構図へ寄り、アオの顔が画面の上の方（会話の窓より上）に、
	# ハルが画面の横に入る。アオの顔までの線は、ハルの体・ナゴミ・地形に隠れない
	var g := _game()
	await h.settle()
	var cam := _rig()
	_face(g, Vector3(0, 0, 2.2), "npc_a")
	await _ticks(g, [cam], 20)
	h.expect(cam.talk_weight() == 0.0 and cam.fov == float(g.tuning.camera.fov), "話す前はふだんのカメラ")
	await _tick(g, [cam], {"jump": true})
	h.expect(g.talk_npc == "npc_a" and not g.story.dialogue.is_empty(), "話しかけると会話が始まり、話し相手を覚える（%s）" % g.talk_npc)
	var w_at := {}
	for i in 45:
		await _tick(g, [cam])
		w_at[i + 1] = cam.talk_weight()
	h.between(w_at[18], 0.3, 0.99, "0.3 秒では寄せている途中")
	h.expect(w_at[24] < 1.0 and w_at[36] == 1.0, "0.4〜0.6 秒で寄せきる（0.4 秒 %.2f・0.6 秒 %.2f）" % [w_at[24], w_at[36]])
	var n = _npc(g, "npc_a")
	var face := _face_point(n)
	var fs := _on_screen(cam, face)
	h.between(fs.y, 0.25, 0.62, "話し相手の顔は画面の上の方（中心から上へ）")
	h.expect(absf(fs.x) < 0.5, "話し相手の顔は画面の中ほど（%.2f）" % fs.x)
	# スマホ（844×390）でも同じ高さ（縦の視野角で決まる）。会話の窓（下の 45%、中心から下 0.08 より下）より上に肩まで入る
	var ss := _on_screen(cam, face - Vector3(0, TalkCamera.SHOULDER, 0), 844.0 / 390.0)
	h.expect(ss.y > -0.08 and absf(_on_screen(cam, face, 844.0 / 390.0).x) < 0.5, "スマホの画面でも、肩まで会話の窓より上（%.2f）" % ss.y)
	var hs := _on_screen(cam, g.player.pos + Vector3(0, TalkCamera.HEAD.x, 0))
	h.expect(hs.z > 0.0 and absf(hs.x) > 0.15 and absf(hs.x) < 1.0, "ハルは画面の横に入る（%s）" % hs)
	var nag = null
	if g.nagomi_present():
		var py := g.player.yaw
		nag = g.player.pos + Vector3(-cos(py), 0, sin(py)) * NagomiView.OFFSET.x + Vector3(0, NagomiView.OFFSET.y, 0) + U.yaw_to_dir(py) * NagomiView.OFFSET.z
	h.expect(not TalkCamera._hidden(cam.global_position, face, g.player.pos, nag), "顔までの線はハルの体・ナゴミに隠れない")
	var v := TalkCamera._front(face, cam.global_position) - cam.global_position
	h.expect(g.phys.raycast(cam.global_position, v.normalized(), v.length(), Phys.TERRAIN | Phys.BREAKABLE, [n.body.get_rid()]).is_empty(),
		"顔までの線は地形に当たらない")
	h.near(cam.fov, TalkCamera.FOV, 0.01, "会話のカメラの視野角")
	h.expect(cam.forward_dir().dot((face - cam.global_position).normalized()) > 0.9, "カメラは話し相手の方を向く")
	cam.queue_free()
	h.free_game(g)


func test_talk_camera_returns_to_player_camera() -> void:
	# プレイヤーがカメラを横へ回して見下ろした（yaw・pitch を変えた）まま話しかけ、会話中に右スティック・マウスを動かしても、
	# 会話を送り終えて 0.6 秒たつと、カメラは話しかける前と同じ場所・向きに戻る（ゲームの中身の yaw・pitch は少しも変わらない）。
	# 送るのはキーボード・パッドの決定（jump）と、スマホの窓のタップ（confirm）の両方で確かめる
	for key in ["jump", "confirm"]:
		var g := _game()
		await h.settle()
		var cam := _rig()
		_face(g, Vector3(0, 0, 2.2), "npc_a")
		g.cam.yaw = 0.7
		g.cam.pitch = 26.0 * U.DEG
		await _ticks(g, [cam], 40)
		var yaw0 := g.cam.yaw
		var pitch0 := g.cam.pitch
		var t0 := cam.global_transform
		var fov0 := cam.fov
		await _tick(g, [cam], {"jump": true})
		await _ticks(g, [cam], 40, {"look_x": 0.04, "look_y": -0.03, "look_active": true})
		h.expect(cam.talk_weight() == 1.0, "%s：会話の構図へ寄った" % key)
		await _finish_dialogue(g, [cam], key, {"look_x": 0.04, "look_y": 0.03, "look_active": true})
		await _ticks(g, [cam], 36)
		h.expect(g.story.dialogue.is_empty() and g.talk_npc == "", "%s：会話が終わり、話し相手を忘れる" % key)
		h.expect(cam.talk_weight() == 0.0, "%s：0.6 秒でふだんのカメラへ戻る" % key)
		h.expect(g.cam.yaw == yaw0 and g.cam.pitch == pitch0, "%s：ゲームの中身のカメラの向きは変わらない（yaw %.4f→%.4f、pitch %.4f→%.4f）" % [key, yaw0, g.cam.yaw, pitch0, g.cam.pitch])
		h.expect(cam.global_position.distance_to(t0.origin) < 0.002 and cam.global_transform.basis.z.distance_to(t0.basis.z) < 0.002,
			"%s：カメラは話しかける前の場所・向きに戻る（ずれ %.4f m）" % [key, cam.global_position.distance_to(t0.origin)])
		h.near(cam.fov, fov0, 0.001, "%s：視野角も戻る" % key)
		cam.queue_free()
		h.free_game(g)


func test_talk_camera_over_counter() -> void:
	# 台（上の面 1.1m）の奥の住人：台の上の品に隠れないよう、顔までの線が台の上 GOODS_H より高くなるカメラ（少し上げた）を選ぶ。
	# カメラは台の中にも、台の上をふさぐ体だけを止める箱の中にも入らない
	var g := _game()
	await h.settle()
	var cam := _rig()
	_face(g, Vector3(10, 0, 3.0), "npc_shopkeeper")
	await _ticks(g, [cam], 20)
	await _tick(g, [cam], {"jump": true})
	await _ticks(g, [cam], 40)
	h.expect(cam.talk_weight() == 1.0, "台の奥の住人にも会話の構図が見つかる")
	var n = _npc(g, "npc_shopkeeper")
	var face := _face_point(n)
	var c := cam.global_position
	h.expect(c.y > face.y + 0.2, "カメラは顔より上から見下ろす（カメラ %.2f m、顔 %.2f m）" % [c.y, face.y])
	# 顔までの線の、台の奥の端（z 4.2）での高さ
	var k := (4.2 - c.z) / (face.z - c.z)
	var y_back := lerpf(c.y, face.y, k)
	h.expect(y_back >= 1.1 + TalkCamera.GOODS_H - 0.05, "顔までの線は台の上の品より上を通る（台の奥の端で %.2f m）" % y_back)
	h.expect(_inside_shapes(g.room, c, 0.2) == "" and not g.phys.sphere_hits(c, 0.2, TalkCamera.PLACE_MASK), "カメラは台・台の上の箱の中に入らない")
	h.between(_on_screen(cam, face).y, 0.25, 0.62, "顔は画面の上の方")
	cam.queue_free()
	h.free_game(g)


# ---------------------------------------------------------------- 使わない会話

func test_talk_camera_leaves_event_cameras_and_other_lines() -> void:
	# 会話のカメラを入れたカメラと切ったカメラを同じゲームで動かし、どちらも同じ所に写す（今までどおり）ことを確かめる：
	# ・台本のカメラ（camera の手順）を使うイベントで話しかけた：台本のカメラのまま（会話のカメラは使わない）
	# ・ナゴミと地の文だけの会話：使わない
	# ・トリガーで始まった会話（住人が話し手でも）：使わない
	# ・戦闘中のひと言（会話ではない）：使わない
	var g := _game()
	await h.settle()
	var on := _rig(true)
	var off := _rig(false)
	var rigs := [on, off]
	var same := func(what: String) -> void:
		h.expect(on.global_transform.is_equal_approx(off.global_transform) and on.fov == off.fov and on.talk_weight() == 0.0,
			"%s：会話のカメラを入れても今までと同じ画面（ずれ %.4f m）" % [what, on.global_position.distance_to(off.global_position)])
	# 台本のカメラで話すエミ
	_face(g, Vector3(-10, 0, 2.2), "npc_e")
	await _ticks(g, rigs, 20)
	await _tick(g, rigs, {"jump": true})
	h.expect(g.talk_npc == "", "台本のカメラを使うイベントでは、話し相手を覚えない（%s）" % g.talk_npc)
	var worst := 0.0
	var eye_used := false
	for i in 90:
		await _tick(g, rigs)
		worst = maxf(worst, on.global_position.distance_to(off.global_position))
		eye_used = eye_used or g.cam_eye != null
	h.expect(eye_used and not g.story.dialogue.is_empty(), "台本のカメラ（置き場所）が会話の間も動いている")
	h.expect(worst < 0.0001, "台本のカメラはそのまま（ずれ 最大 %.5f m）" % worst)
	same.call("台本のカメラのイベント")
	await _finish_dialogue(g, rigs)
	await _ticks(g, rigs, 60)
	# ナゴミと地の文だけ
	_face(g, Vector3(-20, 0, 2.2), "npc_n")
	await _ticks(g, rigs, 20)
	await _tick(g, rigs, {"jump": true})
	h.expect(g.talk_npc == "npc_n" and String(g.story.dialogue.get("who", "")) == "ナゴミ", "ナゴミの会話が始まる")
	await _ticks(g, rigs, 40)
	same.call("ナゴミの行")
	await _tick(g, rigs, {"jump": true})
	await _ticks(g, rigs, 4)
	await _tick(g, rigs, {"jump": true})
	await _ticks(g, rigs, 40)
	h.expect(String(g.story.dialogue.get("who", "x")) == "", "地の文の行になる")
	same.call("地の文の行")
	await _finish_dialogue(g, rigs)
	await _ticks(g, rigs, 30)
	# トリガーで始まったアオの会話（アオは同じ部屋にいて話し手だが、話しかけてはいない）
	_face(g, Vector3(20, 0, 0), "npc_a")
	await _ticks(g, rigs, 40)
	h.expect(not g.story.dialogue.is_empty() and g.talk_npc == "", "トリガーで会話が始まる（話し相手は覚えない）")
	same.call("トリガーで始まった会話")
	await _finish_dialogue(g, rigs)
	# 戦闘中のひと言（ボスのセリフ）：会話の窓ではなく字幕。カメラは動かない
	g.emit_event({"type": "bossLine", "who": "閂", "text": "……"})
	await _ticks(g, rigs, 30)
	same.call("戦闘中のひと言")
	on.queue_free()
	off.queue_free()
	h.free_game(g)


func test_talk_camera_keeps_framing_and_yields_to_event_camera() -> void:
	# アオとの会話（ハル→アオ→ナゴミ→アオ）：構図は会話の始めに 1 度だけ選び、ハル・ナゴミの行でも動かさない。
	# 会話の途中で台本の注視（cam_focus）が入ったら、会話のカメラは 0.5 秒で外れて台本のカメラと同じ画面になり、終わると戻る
	var g := _game()
	await h.settle()
	var on := _rig(true)
	var off := _rig(false)
	var rigs := [on, off]
	_face(g, Vector3(0, 0, 2.2), "npc_a")
	await _ticks(g, rigs, 20)
	await _tick(g, rigs, {"jump": true})
	await _ticks(g, rigs, 40)
	var frame0: Dictionary = on.talk_frame().duplicate()
	var pos0 := on.global_position
	h.expect(String(g.story.dialogue.get("who", "")) == "ハル" and on.talk_weight() == 1.0, "ハルの行から会話の構図（話し相手のアオを映す）")
	var whos := []
	for k in 3:
		await _tick(g, rigs, {"jump": true})
		await _ticks(g, rigs, 30)
		whos.append(String(g.story.dialogue.get("who", "")))
		var fr := on.talk_frame()
		h.expect(on.talk_weight() == 1.0 and fr.get("pos") == frame0.pos and fr.get("look") == frame0.look and on.global_position.distance_to(pos0) < 0.0001,
			"%s の行でも構図は変わらない" % whos[-1])
	h.expect(whos == ["アオ", "ナゴミ", "アオ"], "ハル→アオ→ナゴミ→アオと送った（%s）" % [whos])
	# 台本の注視が入る（会話の途中で、イベントが camera の手順を走らせた）
	g.cam_focus = Vector3(5, 1.5, 10)
	g.cam_focus_time = 3.0
	await _ticks(g, rigs, 36)
	h.expect(on.talk_weight() == 0.0 and on.global_transform.is_equal_approx(off.global_transform), "台本の注視が入ると会話のカメラは外れ、台本のカメラと同じ画面")
	g.cam_focus = null
	g.cam_focus_time = 0.0
	await _ticks(g, rigs, 36)
	h.expect(on.talk_weight() == 1.0 and on.global_position.distance_to(pos0) < 0.001, "台本の注視が終わると、同じ会話の構図へ戻る")
	on.queue_free()
	off.queue_free()
	h.free_game(g)


func test_talk_camera_no_framing_keeps_normal_camera() -> void:
	# 天井の低い細い通路（幅 1.4m・高さ 2.2m）で、ハルのすぐ後ろが壁：肩越しにも横にも置けないので、ふだんのカメラのまま
	var walls := [{"t": "box", "pos": [30.95, 0, 3], "size": [0.5, 2.2, 8]}, {"t": "box", "pos": [29.05, 0, 3], "size": [0.5, 2.2, 8]},
		{"t": "box", "pos": [30, 2.2, 3], "size": [3, 0.5, 8]}, {"t": "box", "pos": [30, 0, 1.0], "size": [3, 2.2, 0.4]}]
	var g := _game(walls, [{"type": "npc", "id": "npc_t", "name": "トト", "pos": [30, 0, 3.6], "yaw": 180, "talk": "t.t"}])
	await h.settle()
	var on := _rig(true)
	var off := _rig(false)
	_face(g, Vector3(30, 0, 1.75), "npc_t")
	await _ticks(g, [on, off], 20)
	await _tick(g, [on, off], {"jump": true})
	h.expect(g.talk_npc == "npc_t" and not g.story.dialogue.is_empty(), "細い通路でも話しかけられる")
	await _ticks(g, [on, off], 40)
	h.expect(on.talk_frame().is_empty() and on.talk_weight() == 0.0, "置ける構図が無ければ会話のカメラは使わない")
	h.expect(on.global_transform.is_equal_approx(off.global_transform), "ふだんのカメラのまま")
	on.queue_free()
	off.queue_free()
	h.free_game(g)


# ---------------------------------------------------------------- 地形・物の中に入らない

func test_talk_camera_blend_stays_out_of_walls() -> void:
	# 壁の角・壁ぎわ・台の前で話しかける。寄せる途中（毎刻み）も、寄せたあとも、戻る途中も、カメラはハルの頭から壁を越えた所に
	# 出ない・形の中に入らない
	var walls := [{"t": "box", "pos": [0, 0, -1.2], "size": [12, 4, 0.4]}, {"t": "box", "pos": [-1.6, 0, 3], "size": [0.4, 4, 9]}]
	var g := _game(walls, [{"type": "npc", "id": "npc_b", "name": "ブン", "pos": [3, 0, 1.0], "yaw": 180, "talk": "t.b"}])
	await h.settle()
	var cam := _rig()
	# 壁から離れて・横の壁ぎわ（0.5m）・後ろの壁ぎわ（0.6m）・台の前・台の前の端
	for cs in [[Vector3(0, 0, 2.2), "npc_a"], [Vector3(-0.9, 0, 2.3), "npc_a"], [Vector3(3, 0, -0.4), "npc_b"], [Vector3(10, 0, 3.0), "npc_shopkeeper"],
			[Vector3(10.8, 0, 3.0), "npc_shopkeeper"]]:
		_face(g, cs[0], cs[1])
		# ふだんのカメラは横から（壁の方から）
		g.cam.yaw += 1.2
		await _ticks(g, [cam], 30)
		await _tick(g, [cam], {"jump": true})
		var bad := ""
		var used := 0.0
		for i in 160:
			var input := {"jump": i > 50 and i % 6 < 3 and g.story.blocking()}
			await _tick(g, [cam], input)
			var c := cam.global_position
			var pivot := g.player.pos + Vector3(0, float(g.tuning.camera.pivotHeight), 0)
			var v := c - pivot
			var why := _inside_shapes(g.room, c, 0.05, true)
			if why == "" and v.length() > 0.05 and not g.phys.raycast(pivot, v.normalized(), v.length(), Phys.TERRAIN | Phys.BREAKABLE).is_empty():
				why = "ハルの頭から壁を越えた所"
			if why != "" and bad == "":
				bad = "%d 刻み目 %s（%s、寄せた割合 %.2f）" % [i, why, c, cam.talk_weight()]
			used = maxf(used, cam.talk_weight())
		h.expect(bad == "", "%s %s：カメラは壁・物の中に入らない %s" % [cs[1], cs[0], bad])
		h.expect(used == 1.0 and cam.talk_weight() == 0.0, "%s %s：会話の構図へ寄って、戻った（%.2f）" % [cs[1], cs[0], used])
		await _ticks(g, [cam], 40)
	cam.queue_free()
	h.free_game(g)


## 第 1 章の部屋の、すべての住人のまわり（話せる距離の 12 方向×3 つの距離、ハルが立てる所）で構図を選び、
## 選んだ構図のカメラが地形・物の中に入らず、ハルの頭から通り、顔が見えることを確かめる。ナゴミがいるときといないときの両方
func test_talk_framings_stay_out_of_geometry() -> void:
	var stats := {"pos": 0, "found": 0}
	var missing := []
	for setup in [["ch1.opening_done", "ch1.chores_started", "ch1.t_move"],
			["ch1.opening_done", "ch1.chores_started", "ch1.t_move", "ch1.ordo_stopped", "ch1.frame_fitted"],
			["ch1.opening_done", "ch1.chores_started", "ch1.nico_rescued", "ch1.plaza_done", "ch1.ordo_stopped", "ch1.frame_fitted", "ch1.morning"]]:
		var g := GameSim.new()
		var vp := SubViewport.new()
		vp.own_world_3d = true
		vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
		vp.size = Vector2i(2, 2)
		h.tree.root.add_child(vp)
		vp.add_child(g)
		g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
		for f in setup:
			g.set_flag(f)
		for room in ["ch1.training", "ch1.lower", "ch1.mid", "ch1.upper", "ch1.workshop", "ch1.guild", "ch1.mayor"]:
			g.load_room(room, "")
			await h.settle()
			await h.settle()
			for n in g.npcs:
				var found := 0
				var tried := 0
				for a in 12:
					for d in [1.2, 1.7, 2.1]:
						var at: Vector3 = n.pos + Vector3(sin(a * PI / 6.0), 0, cos(a * PI / 6.0)) * d
						if not _standable(g, at):
							continue
						tried += 1
						g.player.teleport(at, U.dir_to_yaw(n.pos.x - at.x, n.pos.z - at.z))
						var from := at + U.yaw_to_dir(g.player.yaw) * -5.0 + Vector3(0, 2.5, 0)
						var fr := TalkCamera.find(g, n, from, 16.0 / 9.0)
						if fr.is_empty():
							continue
						found += 1
						var why := _check_frame(g, n, fr)
						h.expect(why == "", "%s %s のまわり %s：構図が %s（%s）" % [room, n.id, at, why, fr.pos])
				stats.pos += tried
				stats.found += found
				if tried > 0 and found * 2 < tried:
					missing.append("%s %s %d/%d" % [room, n.id, found, tried])
				h.expect(tried == 0 or found > 0, "%s %s：話せる所のどこかで構図が見つかる（%d/%d）" % [room, n.id, found, tried])
		h.free_game(g)
	print("    会話の構図：ハルの立つ所 %d か所のうち %d か所で見つかる（%.0f%%）。半分に届かない住人：%s" % [stats.pos, stats.found,
		100.0 * stats.found / maxf(1.0, stats.pos), missing])
	h.expect(stats.found > stats.pos * 0.75, "ほとんどの立つ所で構図が見つかる（%d/%d）" % [stats.found, stats.pos])


## ハルが立てる所か：体（足元から 0.4・1.2m の球）が物に重ならず、形（箱・殻の壁）の中でもなく、足元に床がある
## （物の中に丸ごと入った球は面に触れないので、形のデータでも確かめる：下段のマーサは家の角に立っている）
func _standable(g: GameSim, at: Vector3) -> bool:
	var m := Phys.TERRAIN | Phys.BREAKABLE | Phys.PROP
	if g.phys.sphere_hits(at + Vector3(0, 0.45, 0), Player.RADIUS, m) or g.phys.sphere_hits(at + Vector3(0, 1.2, 0), Player.RADIUS, m):
		return false
	if _inside_shapes(g.room, at + Vector3(0, 0.45, 0), Player.RADIUS) != "" or _inside_shapes(g.room, at + Vector3(0, 1.2, 0), Player.RADIUS) != "":
		return false
	var hit: Dictionary = g.phys.raycast(at + Vector3(0, 0.3, 0), Vector3.DOWN, 0.6, Phys.TERRAIN)
	return not hit.is_empty()


## 選んだ構図の確かめ（いけないわけ。よければ ""）
func _check_frame(g: GameSim, n, fr: Dictionary) -> String:
	var c: Vector3 = fr.pos
	var pivot := g.player.pos + Vector3(0, float(g.tuning.camera.pivotHeight), 0)
	var v := c - pivot
	if not g.phys.raycast(pivot, v.normalized(), v.length(), TalkCamera.PLACE_MASK).is_empty():
		return "ハルの頭から壁・物を越えた所"
	if g.phys.sphere_hits(c, TalkCamera.CLEAR - 0.02, TalkCamera.PLACE_MASK):
		return "壁・物に近すぎる"
	var inside := _inside_shapes(g.room, c, 0.1)
	if inside != "":
		return "形の中（%s）" % inside
	var face := _face_point(n)
	var f := TalkCamera._front(face, c) - c
	if not g.phys.raycast(c, f.normalized(), f.length(), TalkCamera.SIGHT_MASK, [n.body.get_rid()]).is_empty():
		return "顔が見えない"
	return ""
