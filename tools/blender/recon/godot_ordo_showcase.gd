extends SceneTree
## 巡礼機オルド（ordo.glb・OrdoView）を Godot の中で撮って、確認の画像を並べる（レビュー用。ゲームにはまだ出ない：置くのは次の段）。
##   tools/godot.sh shot --resolution 1920x1080 --script /abs/tools/blender/recon/godot_ordo_showcase.gd -- <出力のフォルダ>
## 出力：views.jpg（右舷の真横・正面・右前 3/4・停止の姿勢の夜）、town_edge.jpg（背の上の町の代わりの箱の縁・リフトの踊り場・
## 船首寄りの縁から見下ろす 3 枚。体は止まり、120 m 下の砂の床が流れる見方 body_fixed）、walk.jpg（右舷の脚 2 対の歩き 8 こま、
## 地面は止まり体が進む見方。カメラは体について行く）。
## 座標は OrdoView と同じ：背の面 y = 0、地面 y = -120、+Z が船首、-X が右舷（リフトの側）。

const TILE := Vector2i(960, 540)

var out_dir := ""
var world: Node3D
var sun: DirectionalLight3D
var cam: Camera3D
var ordo: OrdoView
var ground: MeshInstance3D
var town: Node3D
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
	sun.rotation_degrees = Vector3(-38, -125, 0)
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
	await _shot(views, c + Vector3(-1050, 10, 0), c + Vector3(0, -50, 0), 26.0, "right side (starboard, lift side) / walking")
	await _shot(views, c + Vector3(-60, 30, 980), c + Vector3(0, -50, 0), 24.0, "front (bow) / walking")
	await _shot(views, c + Vector3(-620, 90, 560), c + Vector3(0, -55, 10), 28.0, "front-right 3/4 / walking")
	# 停止の姿勢（8 本とも接地）・夜（非常灯の琥珀だけ）
	ordo.set_walking(false, true)
	EnvironmentSetup.apply_mood(sun, "night")
	env.fog_density = 0.0005
	c = _center()
	await _shot(views, c + Vector3(-560, 40, -520), c + Vector3(0, -55, 0), 28.0, "stopped pose (all 8 feet planted) / night")
	_sheet(views, 2, out_dir.path_join("views.jpg"))
	EnvironmentSetup.apply_mood(sun, "day")
	env.fog_density = 0.00035
	sun.rotation_degrees = Vector3(-38, -125, 0)

	# ---- 2. 町の縁から見下ろす（体が止まり、地面が流れる見方。背に町の代わりの箱）
	ordo.free()
	ordo = OrdoView.new()
	ordo.body_fixed = true
	world.add_child(ordo)
	ordo.set_process(false)
	town = _make_town()
	world.add_child(town)
	sun.directional_shadow_max_distance = 450.0   # 近くの所の影を細かく（遠い全体は 1400 m）
	_run_for(20.0)
	_sync_ground()
	var edge: Array[Image] = []
	# 町の部屋の縁（|x| ≤ 49）からは、舷（|x| = 60、背の面の 2.5 m 上）が手前をふさいで真下の脚は見えない。
	# 脚が見えるのは舷の上・舷から外へ出た所（右舷のリフトの踊り場 x = -76 など）。結果の文書の 4 章
	await _shot(edge, Vector3(-66.0, 8.0, -112.0), Vector3(-80.0, -100.0, 20.0), 62.0, "6 m beyond the starboard rim near the stern, 8 m up: flank and legs r3, r2 stepping, desert 120 m below")
	await _shot(edge, Vector3(-77.0, 3.0, -1.0), Vector3(-76.0, -95.0, 72.0), 64.0, "front corner of the lift landing (x=-77): legs r2 and r1 ahead and below")
	await _shot(edge, Vector3(-56.0, 34.0, 176.0), Vector3(-76.0, -95.0, 70.0), 62.0, "beside the raised bow visor looking back-down: leg r1, the flank, the town on the back")
	await _shot(edge, Vector3(-47.0, 10.0, 20.0), Vector3(-200.0, -60.0, 60.0), 60.0, "town edge (x=-47, 10 m above the back): the rim hides the legs, desert far below")
	_sheet(edge, 2, out_dir.path_join("town_edge.jpg"))
	town.visible = false

	# ---- 2b. 近くで見る所（肩・膝・足・リフト・扉・センサースリット）
	var det: Array[Image] = []
	ground.position = ground_rest + ordo.ground_offset()
	await _shot(det, Vector3(-150.0, -40.0, 70.0), Vector3(-64.0, -60.0, 40.0), 40.0, "leg r2: shoulder disc, thigh plates, piston, knee (planted)")
	await _shot(det, Vector3(-120.0, -95.0, -10.0), Vector3(-64.0, -112.0, -48.0), 40.0, "foot r3 (38 x 24 m): ivory pads, brass end brackets, ankle disc")
	await _shot(det, Vector3(-150.0, 0.0, -50.0), Vector3(-70.0, -25.0, -12.0), 42.0, "lift on the starboard flank: landing, awning, guide, cage")
	await _shot(det, Vector3(-70.0, 10.0, -330.0), Vector3(0.0, -5.0, -200.0), 40.0, "stern: forbidden door (22 x 30 m opening) and frame lights")
	await _shot(det, Vector3(-90.0, 30.0, 300.0), Vector3(0.0, 15.0, 200.0), 40.0, "bow: sensor slit wrapping the visor")
	await _shot(det, Vector3(-230.0, -112.0, 40.0), Vector3(-30.0, -48.0, 0.0), 48.0, "underside: graphite truss, hanging knobs, keel and shoulder sockets")
	_sheet(det, 2, out_dir.path_join("details.jpg"))
	town.free()

	# ---- 3. 歩きのこま（地面は止まり体が進む。カメラは体について行き、右舷の脚 2・3 を見る）
	ordo.free()
	ordo = OrdoView.new()
	ordo.body_fixed = false
	world.add_child(ordo)
	ordo.set_process(false)
	ground.position = ground_rest
	sun.directional_shadow_max_distance = 900.0
	var walk: Array[Image] = []
	var t := 0.0
	for k in 8:
		var target := 10.0 * k
		_run_for(target - t)
		t = target
		var z := ordo.travel
		var lab := "t=%2.0fs  phase %.3f  planted:" % [t, ordo.phase]
		for tag in ["r1", "r2", "r3", "r4"]:
			lab += " %s%s" % [tag, "" if ordo.is_planted(tag) else "(swing)"]
		await _shot(walk, Vector3(-420.0, -55.0, z), Vector3(0.0, -70.0, z), 34.0, lab)
	_sheet(walk, 2, out_dir.path_join("walk.jpg"))
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


## 町の代わり（背の面の上、約 180 × 90 m、3 段）：段の床と白い家の箱・布の屋根・黒鉛の塔。体と一緒に動く（OrdoView の子）
func _make_town() -> Node3D:
	var t := Node3D.new()
	var ivory := _mat(Color("#e9dfc9"))
	var ivory2 := _mat(Color("#d3c6ac"))
	var cloth := _mat(Color("#b75b43"))
	var dark := _mat(Color("#444641"))
	var tiers := [[-90.0, -15.0, 1.5], [-15.0, 30.0, 6.5], [30.0, 90.0, 22.5]]
	for tr in tiers:
		var z0: float = tr[0]
		var z1: float = tr[1]
		var y: float = tr[2]
		_box(t, Vector3(0, y / 2.0, (z0 + z1) / 2.0), Vector3(92.0, y, z1 - z0), ivory2)
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	for tr in tiers:
		var z0: float = tr[0]
		var z1: float = tr[1]
		var y: float = tr[2]
		var z := z0 + 4.0
		while z < z1 - 5.0:
			var x := -42.0
			var d := rng.randf_range(6.0, 10.0)
			while x < 40.0:
				var w := rng.randf_range(6.0, 12.0)
				if absf(x + w / 2.0) > 4.0 and rng.randf() < 0.8:
					var hh := rng.randf_range(4.0, 9.0)
					var p := Vector3(x + w / 2.0, y + hh / 2.0, z + d / 2.0)
					_box(t, p, Vector3(w - 1.0, hh, d - 1.0), ivory)
					if rng.randf() < 0.35:
						_box(t, p + Vector3(0, hh / 2.0 + 0.3, 0), Vector3(w - 2.0, 0.6, d - 2.0), cloth)
				x += w + rng.randf_range(1.0, 3.0)
			z += d + rng.randf_range(2.0, 4.0)
	for p in [Vector3(-30, 6.5, 0), Vector3(28, 6.5, 12), Vector3(-10, 22.5, 60), Vector3(16, 22.5, 75), Vector3(0, 1.5, -70)]:
		var hh := rng.randf_range(18.0, 30.0)
		_box(t, p + Vector3(0, hh / 2.0, 0), Vector3(5, hh, 5), dark)
	return t


func _mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 0.85
	return m


func _box(parent: Node3D, pos: Vector3, size: Vector3, mat: Material) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	mi.position = pos
	parent.add_child(mi)


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


func _sheet(imgs: Array[Image], cols: int, path: String) -> void:
	var rows := int(ceil(imgs.size() / float(cols)))
	var sheet := Image.create(TILE.x * cols, TILE.y * rows, false, Image.FORMAT_RGB8)
	for k in imgs.size():
		sheet.blit_rect(imgs[k], Rect2i(Vector2i.ZERO, TILE), Vector2i((k % cols) * TILE.x, (k / cols) * TILE.y))
	var err := sheet.save_jpg(path, 0.88)
	var labels := []
	for im in imgs:
		labels.append(im.get_meta("label", ""))
	var f := FileAccess.open(path.get_basename() + ".txt", FileAccess.WRITE)
	f.store_string("\n".join(labels) + "\n")
	print("書き出し：%s（%s）" % [path, error_string(err)])
