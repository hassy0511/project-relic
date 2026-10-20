class_name TownLights
extends MultiMeshInstance3D
## 背の上の町の灯：家の壁の窓・大通りの街灯・段の縁・塔の灯の小さな光の点（オープニングの夜明けの遠景、停止の夜の灯が消える場面）。
## 描画は 1 回（MultiMesh。シェーダー assets/shaders/town_lights.gdshader：遠くても数画素の光の点、足し合わせ、霞の代わりに遠いほど暗く）。
## 灯の位置は背の上の町の影絵（キットの部品 town/ordo_town）の壁の面から選ぶ（壁の真ん中の高さ、面の 0.2 m 手前）。原点 = オルドの原点
## （背の歩行面の真ん中、+Z が船首）なので、OrdoView の骨（体と一緒に動く）の子に置く。
## power（明るさ 0〜1）・flicker（ちらつき 0〜1）・out（消えた灯の割合 0〜1。灯ごとに決まった順に消え、消える直前は強くちらつく）を毎刻み入れる。
## 見た目だけ（ゲームの中身は読まない）。CineDirector が作って動かす

const PART := "res://assets/kit/town/ordo_town.glb"
const SEED := 20261020
## 窓の灯にする壁の面の数の上限・大通りの街灯の間隔（m）
const MAX_WINDOWS := 150
const LAMP_STEP := 11.0

var power := 1.0
var flicker := 0.0
var out := 0.0
## 遠くの灯の最小の大きさ（画面の画素。夜は大きめ）
var px := 5.5
var _mat: ShaderMaterial
static var _cache := {}


func _ready() -> void:
	name = "TownLights"
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	var pts: Array = points()
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	mm.mesh = q
	mm.instance_count = pts.size()
	for i in pts.size():
		var p: Array = pts[i]
		mm.set_instance_transform(i, Transform3D(Basis.IDENTITY, p[0]))
		mm.set_instance_custom_data(i, p[1])
	multimesh = mm
	_mat = ShaderMaterial.new()
	_mat.shader = load("res://assets/shaders/town_lights.gdshader")
	material_override = _mat
	# 光の点はカメラの方へ大きさを変えて描くので、広がりは町の全体＋余白
	custom_aabb = AABB(Vector3(-70, -10, -130), Vector3(140, 70, 240))
	apply()


## power・flicker・out をシェーダーへ渡す（変えたら呼ぶ）
func apply() -> void:
	if _mat == null:
		return
	_mat.set_shader_parameter("power", power)
	_mat.set_shader_parameter("flicker", flicker)
	_mat.set_shader_parameter("out_amount", out)
	_mat.set_shader_parameter("px_size", px)


## 灯の数（確認用）
func count() -> int:
	return multimesh.instance_count if multimesh != null else 0


## 灯の位置と粒ごとの値 [[位置, Color(位相, 大きさ, 消える順, 暖かさ)], …]。決まった種の乱数で毎回同じ（一度だけ作る）
static func points() -> Array:
	if _cache.has("pts"):
		return _cache.pts
	var rng := RandomNumberGenerator.new()
	rng.seed = SEED
	var out_pts: Array = []
	var add := func(p: Vector3, size: float, warm: float) -> void:
		out_pts.append([p, Color(rng.randf(), size, rng.randf(), warm)])
	# 壁の面（横向きの三角形で、床から 1〜7 m の高さ）から窓の灯を選ぶ
	var walls := _wall_faces()
	var picked := 0
	var order: Array = range(walls.size())
	for i in range(order.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var t = order[i]
		order[i] = order[j]
		order[j] = t
	for k in order:
		if picked >= MAX_WINDOWS:
			break
		var w: Array = walls[k]
		add.call(w[0] + w[1] * 0.2, rng.randf_range(0.7, 1.0), rng.randf_range(0.55, 1.0))
		picked += 1
	# 大通りの街灯（真ん中の通りの両側、段の床の 3.4 m 上）
	var z := 90.0
	while z > -112.0:
		for sx in [-1.0, 1.0]:
			add.call(Vector3(sx * 2.6, _base(z) + 3.4, z), 1.15, 0.85)
		z -= LAMP_STEP
	# 段の縁（擁壁の上）の灯
	for zr in [-15.0, 34.0]:
		var x := 8.0
		while x < 47.0:
			for sx in [-1.0, 1.0]:
				add.call(Vector3(sx * x, _base(zr + 0.5) + 0.9, zr - 0.6), 0.9, 0.7)
			x += 9.5
	# 塔の灯（town_backdrop.py の BACK_TOWERS と足した 4 つ。琥珀の帯の高さ、正面）
	var towers := [[-1, 9.0, -112.0, 26.0], [-1, 30.0, -106.0, 19.0], [1, 12.0, -110.0, 23.0], [1, 34.0, -104.0, 17.0],
		[-1, 44.0, -92.0, 14.0], [1, 42.0, -84.0, 15.0], [-1, 20.0, 10.0, 24.0], [1, 22.0, 18.0, 20.0], [-1, 8.0, 60.0, 30.0], [1, 30.0, 72.0, 18.0]]
	for tw in towers:
		var tz: float = tw[2]
		add.call(Vector3(float(tw[0]) * float(tw[1]), _base(tz) + float(tw[3]) - 2.7, tz + 2.9), 1.6, 0.95)
	_cache["pts"] = out_pts
	return out_pts


## 背の上の町の床の高さ（town_backdrop.py の ordo_town の base と同じ）
static func _base(z: float) -> float:
	return 11.5 if z > 34.0 else (6.5 if z > -15.0 else 1.5)


## 町の影絵の壁の面：[真ん中の位置, 外向きの法線]（横向きで、床から 1.2〜7 m・大きさ 1.5 m² 以上の三角形。同じ所に重ならないよう 3 m ごとに 1 つ）
static func _wall_faces() -> Array:
	var out_faces: Array = []
	if not ResourceLoader.exists(PART):
		return out_faces
	var root := (load(PART) as PackedScene).instantiate()
	var seen := {}
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m: Mesh = (mi as MeshInstance3D).mesh
		if m == null:
			continue
		var xf := Transform3D.IDENTITY
		var cur: Node = mi
		while cur != null and cur != root:
			xf = (cur as Node3D).transform * xf
			cur = cur.get_parent()
		var nb := xf.basis.inverse().transposed()
		for s in m.get_surface_count():
			var arr := m.surface_get_arrays(s)
			var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
			var nr = arr[Mesh.ARRAY_NORMAL]
			var has_n: bool = nr is PackedVector3Array and (nr as PackedVector3Array).size() == v.size()
			var ix = arr[Mesh.ARRAY_INDEX]
			var idx: PackedInt32Array = ix if ix is PackedInt32Array and not (ix as PackedInt32Array).is_empty() else PackedInt32Array(range(v.size()))
			for i in range(0, idx.size() - 2, 3):
				var a: Vector3 = xf * v[idx[i]]
				var b: Vector3 = xf * v[idx[i + 1]]
				var c: Vector3 = xf * v[idx[i + 2]]
				var area := (b - a).cross(c - a).length() * 0.5
				if area < 1.5:
					continue
				# 外向きの法線：頂点の法線（無ければ Godot の表の向き＝時計回りから）
				var n: Vector3 = (nb * (nr as PackedVector3Array)[idx[i]]) if has_n else (c - a).cross(b - a)
				n = n.normalized()
				if absf(n.y) > 0.2:
					continue
				var ctr := (a + b + c) / 3.0
				var h := ctr.y - _base(ctr.z)
				if h < 1.2 or h > 7.0:
					continue
				var key := Vector3i(roundi(ctr.x / 3.0), roundi(ctr.y / 3.0), roundi(ctr.z / 3.0))
				if seen.has(key):
					continue
				seen[key] = true
				out_faces.append([ctr, n])
	root.free()
	return out_faces
