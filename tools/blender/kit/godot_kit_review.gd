extends SceneTree
## キットの部品を、ゲームと同じ材質（content/kits/<キット>.json）で格子に並べて 1 枚に描く（確認用）。
##   tools/godot.sh shot --resolution 1800x1100 --script $PWD/tools/blender/kit/godot_kit_review.gd -- <出力の PNG> <キット> [部品のフォルダ]
## 部品の一覧は godot/assets/kit/<フォルダ>/*.glb（フォルダの既定：キットの id の _ より前、ruins_b1 → ruins）。

const COLS := 6
const CELL := 5.0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var out := args[0] if args.size() > 0 else "/tmp/kit_review.png"
	var kit_id := args[1] if args.size() > 1 else "ruins_b1"
	var folder := args[2] if args.size() > 2 else kit_id.split("_")[0]
	var names: Array = []
	for f in DirAccess.get_files_at("res://assets/kit/%s" % folder):
		if f.ends_with(".glb"):
			names.append(f.get_basename())
	names.sort()
	var dress := []
	for i in names.size():
		dress.append({"part": "%s/%s" % [folder, names[i]], "pos": [(i % COLS) * CELL, 0, -(i / COLS) * CELL], "yaw": 0})
	var rows := (names.size() + COLS - 1) / COLS
	var w := (COLS - 1) * CELL
	var d := (rows - 1) * CELL
	var room := {"kit": kit_id, "dress": dress, "geometry": [
		{"t": "box", "pos": [w / 2, -0.2, -d / 2], "size": [w + CELL, 0.2, d + CELL], "skin": "floor"}], "markers": {}}
	var world := World.from_dict({"areas": [{"id": "rv", "name": "rv", "rooms": {"a": room}}]})
	var root := Node3D.new()
	get_root().add_child(root)
	root.add_child(RoomView.build(world, "rv.a"))
	for i in names.size():
		var l := Label3D.new()
		l.text = names[i]
		l.font_size = 48
		l.pixel_size = 0.01
		l.modulate = Color.BLACK
		l.outline_size = 0
		l.position = Vector3((i % COLS) * CELL, 0.05, -(i / COLS) * CELL + 2.0)
		l.rotation_degrees = Vector3(-90, 0, 0)
		root.add_child(l)
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color("#808080")
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color("#c8c0b0")
	e.ambient_light_energy = 0.8
	e.tonemap_mode = Environment.TONE_MAPPER_AGX
	e.glow_enabled = true
	env.environment = e
	root.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -35, 0)
	sun.light_energy = 1.6
	sun.shadow_enabled = true
	root.add_child(sun)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = d + CELL * 1.6
	root.add_child(cam)
	var center := Vector3(w / 2, 1.0, -d / 2)
	cam.position = center + Vector3(-0.45, 0.62, 1.0).normalized() * 80.0
	cam.look_at(center)
	cam.current = true
	for i in 8:
		await process_frame
	await RenderingServer.frame_post_draw
	get_root().get_texture().get_image().save_png(out)
	print("書き出し ", out)
	quit()
