class_name TestHelpers
extends RefCounted
## テストの道具：箱の地形でゲームを作り、入力を与えて刻みを進める。

var tree: SceneTree
var failures: Array = []
var current := ""
var checks := 0


func _init(t: SceneTree) -> void:
	tree = t


func expect(cond: bool, msg: String) -> void:
	checks += 1
	if not cond:
		failures.append("%s: %s" % [current, msg])
		printerr("  失敗: ", msg)


func near(a: float, b: float, tol: float, msg: String) -> void:
	expect(absf(a - b) <= tol, "%s（%.3f、期待 %.3f±%.3f）" % [msg, a, b, tol])


func between(v: float, lo: float, hi: float, msg: String) -> void:
	expect(v > lo and v < hi, "%s（%.3f、期待 %.3f〜%.3f）" % [msg, v, lo, hi])


static func seconds(s: float) -> int:
	return int(round(s * 60.0))


## 箱（中心と大きさ）を三角形の面にする
static func box_faces(center: Vector3, size: Vector3) -> PackedVector3Array:
	var h := size * 0.5
	var c := []
	for i in 8:
		c.append(center + Vector3(h.x if i & 1 else -h.x, h.y if i & 2 else -h.y, h.z if i & 4 else -h.z))
	var quads := [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
	var out := PackedVector3Array()
	for q in quads:
		out.append_array([c[q[0]], c[q[1]], c[q[2]], c[q[0]], c[q[2]], c[q[3]]])
	return out


static func default_tuning() -> Dictionary:
	return U.load_json("res://content/tuning.json")


## opts：{ boxes: [[center, size]...], markers: { 名前: Vector3 }, placement: {...}, tuning: {...} }
func make_game(opts: Dictionary = {}) -> GameSim:
	var faces := [box_faces(Vector3(0, -0.5, 0), Vector3(200, 1, 200))]
	for b in opts.get("boxes", []):
		faces.append(box_faces(b[0], b[1]))
	var markers := {"start": {"pos": Vector3.ZERO, "yaw": 0.0}}
	if opts.has("geometry"):
		# 地形ごと渡す（試しの部屋など）：{ faces, markers: { 名前: { pos, yaw } } }
		faces = opts.geometry.faces
		markers = opts.geometry.markers.duplicate()
	var mk: Dictionary = opts.get("markers", {})
	for k in mk:
		markers[k] = {"pos": mk[k], "yaw": 0.0}
	var placement := {
		"id": "test", "name": "test", "playerStart": "start", "objective": "",
		"enemies": [], "props": [], "triggers": [], "checkpoints": [],
	}
	placement.merge(opts.get("placement", {}), true)
	var g := GameSim.new()
	# ゲームごとに別の物理の世界を持たせる（同時に作った 2 つのゲームがぶつからないように）
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({
		"geometry": {"faces": faces, "markers": markers},
		"placement": placement,
		"tuning": opts.get("tuning", default_tuning()),
		"dialogues": {"hello": {"lines": [{"who": "a", "face": "normal", "text": "やあ"}, {"action": "give_item", "item": "special.drill"}]}},
		"events": {"ev": {"steps": [{"flag": "x"}, {"say": "hello"}]}},
		"seed": 1,
		"save": opts.get("save"),
	})
	return g


## 物理の世界に反映させるため、1 刻み待つ（作った直後に呼ぶ）
func settle() -> void:
	await tree.physics_frame


## 入力を与えて n 刻み進める。input は辞書か、刻みの番号から辞書を返す関数
func run(g: GameSim, ticks: int, input) -> void:
	for i in ticks:
		await tree.physics_frame
		var d: Dictionary = input.call(i) if input is Callable else input
		g.step(InputFrame.of(d))


func free_game(g: GameSim) -> void:
	g.get_parent().queue_free()
