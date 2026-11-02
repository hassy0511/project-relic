class_name StepsShots
## オルドの足音（OrdoSteps。30 章 4.2.1）の確かめ：足が着く前と後のコマ（吊り灯・布の揺れ、日よけの砂ぼこり、天井からこぼれる砂）と、
## 設定の画面の「画面の揺れ」の行。Demo（--demo=<フォルダ>）から使う：
##   --steps_shots            全部の向き（steps_<名前>_<コマ>.png）と設定の画面（steps_settings.png）
##   --steps_shots=lamp,dust  名前で選ぶ（lamp・dust・home・oil・settings）
## oil は再始動のあと・歓声の前の夜の中段（町の電気はまだ戻っていない：停電の間だけの灯油ランプが置かれ、足音は戻っている）
## 足が着く時刻は、時計（と部屋のオルド）を「次の足が 1 秒後に着く」位置に合わせて決める。コマは足が着く刻みから FRAMES 刻み目。
## カメラは自分の Camera3D で固定（足音の画面の揺れは遊びのカメラにだけ掛かるので、ここでは世界の揺れだけが写る）。
## ゲームの刻みは止めない（--fixed-fps 60 で 1 こま = 1 刻み）。描くのは撮るこまの前の数こまだけ。見た目だけ：ゲームの中身には手を加えない

## [名前, 部屋, 目印, ハルの立つ所, ハルの向く所, 狙う部品, その部品の置き場所（近いものを探す）, 部品の中の狙う点, 目（狙う点から）, 画角（度）,
##  （あれば）"restarted_dark"：再始動のあと・電気が戻る前の夜にして部屋を作り直す]
## 狙う点は部屋の飾り（Dress の MultiMesh）から実際の位置を読む（部品の向き・台の高さに合わせる）
const VIEWS := [
	["lamp", "ch1.mid", "start", [-8.0, 0, -11.5], [-12.0, 0, -7.5], "town/lamp_post", [-12.5, 0, -7.5], [0.55, 1.45, 0.0], [2.2, 0.45, -3.0], 30.0],
	["dust", "ch1.mid", "start", [21.0, 0, -7.0], [24.0, 0, 4.0], "town/stall", [24.0, 0, 6.3], [0.0, 2.7, 2.7], [2.8, -0.9, -6.6], 50.0],
	["home", "ch1.home", "", [-1.2, 0, -0.6], [0.0, 0, 1.5], "town/home_set", [0.0, 0, 0.0], [0.0, 3.3, 0.0], [2.4, -1.0, -3.2], 40.0],
	["oil", "ch1.mid", "start", [-1.0, 0, 5.0], [-3.3, 0, 8.0], "town/hand_lantern", [-3.3, 0.8, 8.0], [0.0, 0.36, 0.0], [1.0, 0.3, -1.25], 40.0, "restarted_dark"],
]
## 足が着く刻みからのコマ（負は着く前。揺れの山と谷：0.3・0.6・0.95・1.6 秒）。撮るこまの前の PREROLL こまだけ描く（ほかの刻みは描かずに進める：ソフトウェアの描画でも速い）
const FRAMES := [-12, 19, 38, 57, 94]
const PREROLL := 3
const LEAD_S := 1.0

static func steps(d) -> Array:
	var m = d.main
	var want := String(m.args.get("steps_shots", "1"))
	var s := []
	for v in VIEWS:
		if want != "1" and not want.split(",").has(String(v[0])):
			continue
		s.append({"ticks": 2, "setup": func():
			var g: GameSim = m.game
			g.god_mode = true
			var dark: bool = v.size() > 10 and v[10] == "restarted_dark"
			if dark:
				for f in ["ch1.night", "ch1.ordo_stopped", "ch1.ordo_restarted"]:
					g.set_flag(f)
				m.power.pending["town"] = true
			if g.room_id != v[1] or dark:
				g.load_room(v[1], v[2])
			for t in g.triggers:
				t.fired = true
			d._stand(RoomGeo.v3(v[3]), RoomGeo.v3(v[4]))})
		s.append({"ticks": 2, "setup": func():
			var aim := aim_point(m, String(v[5]), RoomGeo.v3(v[6]), RoomGeo.v3(v[7]))
			print("狙う点（%s）：%s" % [v[0], aim])
			MotionShots._fix_camera(d, aim + RoomGeo.v3(v[8]), aim, float(v[9]))})
		# 部屋が落ち着くまで待つ（この間は描かない）
		s.append({"ticks": 150, "input": {}})
		s.append({"ticks": int(LEAD_S * 60.0) + FRAMES[-1] + PREROLL + 12, "input": {}, "setup": func(): _strip(d, String(v[0]))})
	s.append({"ticks": 2, "setup": func(): MotionShots._release(d)})
	if want == "1" or want.split(",").has("settings"):
		# ポーズの間はゲームの刻みが進まないので、開く・撮る・閉じるを 1 つの手順で（Demo の _pad_steps と同じ）
		s.append({"ticks": 1, "shot": "steps_settings", "setup": func():
			m.pause()
			m.menu.show_controls(func(): m.resume(), PadConfig.ACTIONS.size() + 5),
			"after": func(): m.resume()})
	return s


## 次の足（左 2・右 1 の組）が LEAD_S 秒後に着くよう、時計と部屋のオルドを合わせる
static func arm(m, lead_s: float) -> void:
	var st: OrdoSteps = m.steps
	var target := fposmod(OrdoSteps.plant_phase("l2") - lead_s / OrdoSteps.CYCLE_S, 1.0)
	var o: OrdoView = m._ordo()
	if o != null and o.model != null:
		o.set_phase(target)
	st.phase = target


## 部屋の飾りの部品 part の、pos にいちばん近い置き場所の中の点 local（ワールド）
static func aim_point(m, part: String, pos: Vector3, local: Vector3) -> Vector3:
	var dress: Node = m.level.get_node_or_null("Dress") if m.level != null else null
	var best := Transform3D(Basis.IDENTITY, pos)
	var bd := INF
	if dress != null:
		for c in dress.get_children():
			if not String(c.name).begins_with(part.replace("/", "_")):
				continue
			var xfs := []
			if c is MultiMeshInstance3D:
				var mm: MultiMesh = (c as MultiMeshInstance3D).multimesh
				for i in mm.instance_count:
					xfs.append((c as Node3D).global_transform * mm.get_instance_transform(i))
			elif c is MeshInstance3D:
				xfs.append((c as Node3D).global_transform)
			for xf in xfs:
				var dd: float = (xf as Transform3D).origin.distance_to(pos)
				if dd < bd:
					bd = dd
					best = xf
	return best * local


static func _strip(d, name: String) -> void:
	var tree: SceneTree = d.get_tree()
	arm(d.main, LEAD_S)
	var lead := int(LEAD_S * 60.0)
	var n0: int = d.main.steps.steps_heard
	var at := 0
	for k in FRAMES.size():
		var want: int = lead + int(FRAMES[k])
		# 描かずに進める（撮るこまの PREROLL こま前まで）
		RenderingServer.render_loop_enabled = false
		while at < want - PREROLL:
			await tree.process_frame
			at += 1
		RenderingServer.render_loop_enabled = true
		while at < want:
			await RenderingServer.frame_post_draw
			at += 1
		var img: Image = d.get_viewport().get_texture().get_image()
		var path := "%s/steps_%s_%d.png" % [d.out_dir, name, k]
		img.save_png(path)
		print("コマ：%s（足が着いてから %d 刻み）　足音 %d　描画 %d 回・物 %d" % [path, int(FRAMES[k]), d.main.steps.steps_heard - n0,
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)])
	RenderingServer.render_loop_enabled = false
