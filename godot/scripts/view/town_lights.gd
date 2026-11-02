class_name TownLights
extends MultiMeshInstance3D
## 背の上の町の灯：家の窓・街灯・塔の灯の小さな光の点（オープニングの夜明けの遠景、停止の夜の灯が消える場面）。
## 描画は 1 回（MultiMesh。シェーダー assets/shaders/town_lights.gdshader：遠くても数画素の光の点、足し合わせ、霞の代わりに遠いほど暗く、
## 近く（町の面の窓が見分けられる距離）では消える）。町の面の窓の光（OrdoView の back_mesh、town_far.gdshader）は近くで、この点は遠くで町の灯を見せる。
## 灯の位置と灯の順は、町の部品と一緒に作る表 <部品>_lights.json（tools/blender/kit/town_far.py。[x, y, z, 灯の順, 種類（0 窓・1 街灯・2 塔）]）
## から読む。灯の順は町の面の窓と同じ値なので、消える順がそろう。原点 = オルドの原点（背の歩行面の真ん中、+Z が船首）なので、
## OrdoView の骨（体と一緒に動く）の子に置く。
## power（明るさ 0〜1）・flicker（ちらつき 0〜1）・out（消えた割合 0〜1。灯ごとに決まった順に消え、消える直前は強くちらつく）は
## OrdoView.set_back_lights が町の面の窓と一緒に入れる。見た目だけ（ゲームの中身は読まない）。CineDirector が作って動かす

const SEED := 20261020
## 窓の灯の点の数の上限（光る窓の中から決まった種で選ぶ。街灯・塔の灯は全部）
const MAX_WINDOWS := 240

## 灯の表を読む町の部品（OrdoView の back_part）
var part := "town/ordo_town"
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
	var pts: Array = points(part)
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


## 灯の位置と粒ごとの値 [[位置, Color(位相, 大きさ, 消える順, 暖かさ)], …]。表から読み、窓は決まった種の乱数で MAX_WINDOWS まで選ぶ（部品ごとに一度だけ）
static func points(from_part := "town/ordo_town") -> Array:
	if _cache.has(from_part):
		return _cache[from_part]
	var out_pts: Array = []
	var path := "res://assets/kit/%s_lights.json" % from_part
	var data = JSON.parse_string(FileAccess.get_file_as_string(path)) if FileAccess.file_exists(path) else null
	if not (data is Dictionary):
		_cache[from_part] = out_pts
		return out_pts
	var rng := RandomNumberGenerator.new()
	rng.seed = SEED
	var windows: Array = []
	for p in data.get("points", []):
		var pos := Vector3(float(p[0]), float(p[1]), float(p[2]))
		var order := float(p[3])
		var kind := int(p[4])
		match kind:
			0:
				windows.append([pos, order])
			1:
				out_pts.append([pos, Color(rng.randf(), 1.15, order, 0.85)])
			_:
				out_pts.append([pos, Color(rng.randf(), 1.6, order, 0.95)])
	for i in range(windows.size() - 1, 0, -1):
		var j := rng.randi_range(0, i)
		var t = windows[i]
		windows[i] = windows[j]
		windows[j] = t
	for k in mini(MAX_WINDOWS, windows.size()):
		var w: Array = windows[k]
		out_pts.append([w[0], Color(rng.randf(), rng.randf_range(0.7, 1.0), float(w[1]), rng.randf_range(0.55, 1.0))])
	_cache[from_part] = out_pts
	return out_pts
