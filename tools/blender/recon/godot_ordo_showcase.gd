extends SceneTree
## 巡礼機オルド（ordo.glb・OrdoView）を Godot の中で撮って、紹介の画像を並べる（docs/art_orders/ordo_trial/）。
##   tools/godot.sh shot --resolution 800x450 --script /abs/tools/blender/recon/godot_ordo_showcase.gd -- <出力のフォルダ>
## 出力（どれも長辺 1600 px 以下）：views.jpg（左舷 = リフトの側の真横・正面・左前 3/4・停止の姿勢の夜）、
## town_edge.jpg（体は止まり、120 m 下の砂の床が流れる見方 body_fixed。背の上は町の影絵 ordo_town：リフトの踊り場の手すりから見下ろす・
## 「見下ろす」のカメラ・船首の庇の横から・町の縁からは舷が脚を隠す）、details.jpg（脚 l2・足 l3・リフトの踊り場・リフト・禁足扉・センサースリット）、
## walk.jpg（左舷の脚 4 本の歩き 8 こま、地面は止まり体が進む見方。カメラは体について行く。5 秒から 10 秒ごと）。
## 座標は OrdoView と同じ：背の面 y = 0、地面 y = -120、+Z が船首、+X が左舷（リフトの側。結果の文書 9.3）。
## 2026-10-20：1 回目（右舷のリフト・幅 120 m・町の代わりの箱）から、今の形（左舷のリフトと踊り場・幅 110 m・町の影絵）で撮り直した。

const TILE := Vector2i(800, 450)
const WALK_TILE := Vector2i(700, 394)   ## 歩きの 8 こま（2 列 × 4 段で 1400 × 1576）
## 太陽：リフトの側（左舷 +X）と船首から照らす（1 回目は右舷から）
const SUN_PORT := Vector3(-38, 55, 0)
const SUN_STERN := Vector3(-38, -125, 0)

var out_dir := ""
var world: Node3D
var sun: DirectionalLight3D
var cam: Camera3D
var ordo: OrdoView
var ground: MeshInstance3D
var ground_rest := Vector3(0, OrdoView.GROUND_Y, 0)


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_dir = args[0] if args.size() > 0 else "user://ordo_showcase"
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run.call_deferred()


func _run() -> void:
	root.size = TILE
	world = Node3D.new()
	root.add_child(world)
	sun = EnvironmentSetup.build(world)
	var env: Environment = sun.get_meta("env")
	env.fog_density = 0.00035         # 400 m の機械が霞まない（部屋の既定 0.004 は 400 m 先が 8 割霞む）
	sun.directional_shadow_max_distance = 1400.0
	sun.rotation_degrees = SUN_PORT
	ground = _make_ground()
	world.add_child(ground)
	ordo = OrdoView.new()
	world.add_child(ordo)
	ordo.set_process(false)          # 時間は _run_for で決める（撮影の待ちのこまで進まない）
	cam = Camera3D.new()
	cam.near = 0.5
	cam.far = 6000.0
	world.add_child(cam)
	cam.current = true

	# ---- 1. 全体（地面は止まり体が進む見方。歩きの途中のこま）
	ordo.body_fixed = false
	_run_for(9.0)
	var views: Array[Image] = []
	var c := _center()
	await _shot(views, c + Vector3(960, 0, 0), c + Vector3(0, -45, 0), 27.0, "port side (lift side) / walking")
	await _shot(views, c + Vector3(50, 20, 640), c + Vector3(0, -50, 0), 24.0, "front (bow) / walking")
	await _shot(views, c + Vector3(530, 80, 470), c + Vector3(0, -50, 10), 28.0, "front-left 3/4 (port) / walking")
	# 停止の姿勢（8 本とも接地）・夜（非常灯の琥珀だけ）
	ordo.set_walking(false, true)
	EnvironmentSetup.apply_mood(sun, "night")
	env.fog_density = 0.0005
	c = _center()
	await _shot(views, c + Vector3(480, 30, -440), c + Vector3(0, -50, 0), 28.0, "stopped pose (all 8 feet planted) / night")
	_sheet(views, 2, out_dir.path_join("views.jpg"))
	EnvironmentSetup.apply_mood(sun, "day")
	env.fog_density = 0.00035
	sun.rotation_degrees = SUN_PORT

	# ---- 2. 町の縁・リフトの踊り場から見下ろす（体が止まり、地面が流れる見方。背の上は町の影絵 ordo_town：夜明けの甲羅の部屋と同じ）
	ordo.free()
	ordo = OrdoView.new()
	ordo.body_fixed = true
	ordo.back_part = "town/ordo_town"
	world.add_child(ordo)
	ordo.set_process(false)
	sun.directional_shadow_max_distance = 450.0   # 近くの所の影を細かく（遠い全体は 1400 m）
	_run_for(20.0)
	_sync_ground()
	var edge: Array[Image] = []
	# 町の部屋の縁（|x| ≤ 49）からは、舷（|x| = 55、背の面の 2.5 m 上）が手前をふさいで真下の脚は見えない。
	# 脚が見えるのは舷から外へ出た所：左舷のリフトの踊り場（x 48.5〜71、床は背の面の 1.5 m 上）と、その「見下ろす」のカメラ（結果の文書 3.3・9.4）
	await _shot(edge, Vector3(70.3, 3.1, -6.0), Vector3(84.0, -60.0, 20.0), 64.0, "from the lift landing's outer rail (x=70, eye 1.6 m above the deck): legs l2 and l3 below, desert 120 m down")
	await _shot(edge, Vector3(150.0, -43.5, -12.0), Vector3(62.0, -64.5, -12.0), 60.0, "the lookout camera (event ch1.ordo_legs): legs l2 and l3 from outside the port flank")
	await _shot(edge, Vector3(56.0, 34.0, 176.0), Vector3(76.0, -95.0, 70.0), 62.0, "beside the raised bow visor looking back-down: leg l1, the flank, the landing")
	await _shot(edge, Vector3(47.0, 10.0, 20.0), Vector3(200.0, -60.0, 60.0), 60.0, "town edge (x=47, 10 m above the back): the rim hides the legs, desert far below")
	_sheet(edge, 2, out_dir.path_join("town_edge.jpg"))

	# ---- 2b. 近くで見る所（肩・膝・足・リフト・扉・センサースリット）
	var det: Array[Image] = []
	ground.position = ground_rest + ordo.ground_offset()
	await _shot(det, Vector3(150.0, -40.0, 70.0), Vector3(64.0, -60.0, 40.0), 40.0, "leg l2: shoulder disc, thigh plates, piston, knee (planted)")
	await _shot(det, Vector3(125.0, -95.0, -10.0), Vector3(70.0, -112.0, -48.0), 40.0, "foot l3 (52 x 34 m): ivory pads, brass end brackets, ankle disc")
	await _shot(det, Vector3(96.0, 18.0, -40.0), Vector3(60.0, 1.0, -12.0), 40.0, "lift landing (port): plank deck, lift hatch, brass railing, striped awning, benches, lookout scope")
	await _shot(det, Vector3(150.0, 0.0, -50.0), Vector3(70.0, -25.0, -12.0), 42.0, "lift on the port flank: landing and braces, guide, cage")
	sun.rotation_degrees = SUN_STERN
	await _shot(det, Vector3(-70.0, 10.0, -330.0), Vector3(0.0, -5.0, -200.0), 40.0, "stern: forbidden door (22 x 30 m opening) and frame lights")
	sun.rotation_degrees = SUN_PORT
	await _shot(det, Vector3(90.0, 30.0, 300.0), Vector3(0.0, 15.0, 200.0), 40.0, "bow: sensor slit wrapping the visor")
	_sheet(det, 2, out_dir.path_join("details.jpg"))

	# ---- 3. 歩きのこま（地面は止まり体が進む。カメラは体について行き、左舷の脚 4 本を見る）
	ordo.free()
	ordo = OrdoView.new()
	ordo.body_fixed = false
	world.add_child(ordo)
	ordo.set_process(false)
	ground.position = ground_rest
	sun.directional_shadow_max_distance = 900.0
	var walk: Array[Image] = []
	root.size = WALK_TILE
	var t := 0.0
	for k in 8:
		var target := 5.0 + 10.0 * k      # 振り出しの途中（各脚の振り出しは 19.2 秒）が写るよう、10 秒ごとの 5 秒ずらし
		_run_for(target - t)
		t = target
		var z := ordo.travel
		var lab := "t=%2.0fs  phase %.3f  planted:" % [t, ordo.phase]
		for tag in ["l1", "l2", "l3", "l4"]:
			lab += " %s%s" % [tag, "" if ordo.is_planted(tag) else "(swing)"]
		await _shot(walk, Vector3(420.0, -55.0, z), Vector3(0.0, -70.0, z), 34.0, lab)
	_sheet(walk, 2, out_dir.path_join("walk.jpg"), WALK_TILE)
	print("撮影：%s（views 4・town_edge 4・details 6・walk 8）" % out_dir)
	quit(0)


## 歩きを sec 秒進める（0.25 秒ずつ。足の着く・離れる時刻を飛ばさない）
func _run_for(sec: float) -> void:
	if sec <= 0.0:
		return
	var n := int(ceil(sec / 0.25))
	for _i in n:
		ordo.advance(sec / n)


func _center() -> Vector3:
	return Vector3(0.0, ordo.body_h, ordo.travel)


func _sync_ground() -> void:
	ground.position = ground_rest + ordo.ground_offset()


## 砂の床（6 km 四方。模様は地面の座標で決まるので、地面を動かすと模様が流れる。20 m ごとの薄い線で足の位置が読める）
func _make_ground() -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(6000, 6000)
	mi.mesh = pm
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode cull_disabled;
uniform vec3 sand : source_color = vec3(0.74, 0.43, 0.29);
varying vec3 lp;
void vertex() { lp = VERTEX; }
void fragment() {
	vec2 p = lp.xz;
	float r = sin(p.x * 0.031 + sin(p.y * 0.013) * 2.0) * 0.5 + 0.5;
	float r2 = sin(p.y * 0.071 + p.x * 0.023) * 0.5 + 0.5;
	vec2 f = abs(fract(p / 20.0 + 0.5) - 0.5) * 20.0;
	float line = 1.0 - 0.10 * (1.0 - smoothstep(0.25, 0.6, min(f.x, f.y)));
	ALBEDO = sand * (0.86 + 0.09 * r + 0.05 * r2) * line;
	ROUGHNESS = 1.0;
}
"""
	var m := ShaderMaterial.new()
	m.shader = sh
	mi.material_override = m
	mi.position = ground_rest
	return mi


func _shot(into: Array[Image], from: Vector3, at: Vector3, fov: float, label: String) -> void:
	cam.fov = fov
	cam.position = from
	cam.look_at(at, Vector3.UP)
	for _i in 6:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_texture().get_image()
	img.convert(Image.FORMAT_RGB8)
	img.set_meta("label", label)
	into.append(img)
	print("  ", label)


func _sheet(imgs: Array[Image], cols: int, path: String, tile := TILE) -> void:
	var rows := int(ceil(imgs.size() / float(cols)))
	var sheet := Image.create(tile.x * cols, tile.y * rows, false, Image.FORMAT_RGB8)
	for k in imgs.size():
		sheet.blit_rect(imgs[k], Rect2i(Vector2i.ZERO, tile), Vector2i((k % cols) * tile.x, (k / cols) * tile.y))
	var err := sheet.save_jpg(path, 0.84)
	var labels := []
	for im in imgs:
		labels.append(im.get_meta("label", ""))
	var f := FileAccess.open(path.get_basename() + ".txt", FileAccess.WRITE)
	f.store_string("\n".join(labels) + "\n")
	print("書き出し：%s（%s）" % [path, error_string(err)])
