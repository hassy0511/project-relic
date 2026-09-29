extends SceneTree
## ナゴミ（nagomi.glb）を Godot の中で描いて、確認の画像を 1 枚にまとめる（レビュー用）。
##   tools/godot.sh shot --resolution 400x400 --script /abs/tools/blender/recon/godot_nagomi_showcase.gd -- <出力の PNG>
## ゲームと同じ NagomiView（材質・殻の開き・感情）と同じ光（EnvironmentSetup）で描く。
## 1 段目：ハルと並んだ姿（右前・右後ろ、ゲームの位置と大きさ）、ナゴミの正面・右真横（閉）。
## 2 段目：殻の 3 状態（閉・半開・全開）の正面と、全開の右真横。3・4 段目：感情 8 種の正面。
## 座標は glTF（Godot）：正面 +Z、上 +Y。

const TILE := Vector2i(400, 400)
const COLS := 4
const EMOTION_ORDER := ["normal", "analyzing", "warning", "happy", "confused", "sad", "joking", "dormant"]

var out_path := ""
var cam: Camera3D
var nv: NagomiView
var tiles: Array[Image] = []


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_path = args[0] if args.size() > 0 else "user://nagomi_showcase.png"
	_run.call_deferred()


func _run() -> void:
	root.size = TILE
	var world := Node3D.new()
	root.add_child(world)
	EnvironmentSetup.build(world)
	var floor_mesh := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(6, 6)
	floor_mesh.mesh = pm
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.42, 0.42, 0.44)
	floor_mesh.material_override = fm
	world.add_child(floor_mesh)
	var haru: Node3D = null
	if ResourceLoader.exists("res://assets/models/haru_r.glb"):
		haru = (load("res://assets/models/haru_r.glb") as PackedScene).instantiate()
		world.add_child(haru)
		var anim := haru.find_child("AnimationPlayer", true, false) as AnimationPlayer
		if anim and anim.has_animation("idle"):
			anim.play("idle", 0.0)
			anim.seek(0.0, true)
			anim.pause()
	nv = NagomiView.new()
	world.add_child(nv)
	nv.snap({"pos": Vector3.ZERO, "yaw": 0.0})
	cam = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(cam)
	cam.current = true
	var c := nv.global_position

	await _shot(30.0, Vector3(-0.2, 0.95, 0), 2.0, 10.0)
	await _shot(150.0, Vector3(-0.2, 0.95, 0), 2.0, 10.0)
	if haru:
		haru.visible = false  # 近写ではハルを隠す（真横の視線をさえぎるため）
	await _shot(0.0, c, 0.36, 0.0)
	await _shot(-90.0, c, 0.36, 0.0)
	for st in ["closed", "half", "open"]:
		var a: float = NagomiView.STATES[st]
		nv.set_shells([a, a, a, a])
		await _shot(0.0, c, 0.36, 0.0)
	await _shot(-90.0, c, 0.36, 0.0)
	for e in EMOTION_ORDER:
		nv.emotion = e
		nv._apply(0.0)
		await _shot(0.0, c, 0.36, 0.0)

	var rows := int(ceil(tiles.size() / float(COLS)))
	var sheet := Image.create(TILE.x * COLS, TILE.y * rows, false, Image.FORMAT_RGBA8)
	for k in tiles.size():
		var t: Image = tiles[k]
		t.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(t, Rect2i(Vector2i.ZERO, TILE), Vector2i((k % COLS) * TILE.x, (k / COLS) * TILE.y))
	var err := sheet.save_png(out_path)
	print("撮影：%s（%d 枚、%s）" % [out_path, tiles.size(), error_string(err)])
	quit(0 if err == OK else 1)


## 方位角 az 度（0 = 正面、-90 = 右真横で正面が画像の左）・仰角 el 度から正投影で描いて 1 枚に加える
func _shot(az: float, target: Vector3, size: float, el: float) -> void:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	var d := Vector3(-sin(a) * cos(e), sin(e), cos(a) * cos(e))
	cam.size = size
	cam.position = target + d * 4.0
	cam.look_at(target, Vector3.UP)
	for _i in 4:
		await process_frame
	await RenderingServer.frame_post_draw
	tiles.append(root.get_texture().get_image())
