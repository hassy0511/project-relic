class_name BackTownView
extends Node3D
## 背の上の遠くの町だけ（オルドの体なし）。部屋の "back_town"：{ "part": "town/ordo_back_up", "pos": [x, y, z] }（pos = 部屋の座標での
## オルドの原点 = 背の歩行面の真ん中、+Z が船首）。RoomView が "BackTown" の名前で作る（docs/design/42_コンテンツの書き方.md 14.5）。
## 上段の部屋（ch1.upper）は、オルドの体を置かない（船首の頭が展望台の地平線と章末のカランの影を隠す。残課題 O1）。その南の胸壁の下に
## 町が無く、台地の上に見えた（残課題 T9）ので、町の部品だけをここで描く。描き方は OrdoView の back_mesh と同じ（帳の部品 1 つ、
## シェーダー town_far.gdshader、描画 1 回、影なし）。窓の灯は OrdoView と同じ名前の set_mood（雰囲気の明るさ：昼 0・夜明け 0.6・夜 1。
## main._apply_mood）と set_back_lights（明るさ・ちらつき・消えた割合。町の電気 TownPower._sync_back_windows：停電の間は消え、再始動の波で戻る）。
## オルドの体ではないので、main._ordo()（足音の時計・場面のカメラの舞台）には出てこない。

@export var part := ""

var mesh_node: MeshInstance3D = null
var _mat: ShaderMaterial = null
var back_power := 0.0
var back_flicker := 0.0
var back_out := 0.0
var _mood_k := 0.0


func _ready() -> void:
	var mesh := OrdoView._far_mesh(part)
	if mesh == null:
		push_warning("背の町の部品が無い: %s" % part)
		return
	mesh_node = MeshInstance3D.new()
	mesh_node.name = "Mesh"
	mesh_node.mesh = mesh
	mesh_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mesh_node.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	_mat = ShaderMaterial.new()
	_mat.shader = load(OrdoView.BACK_SHADER)
	_mat.set_shader_parameter("atlas", load(OrdoView.BACK_ATLAS))
	mesh_node.material_override = _mat
	add_child(mesh_node)
	_apply()


## 雰囲気（day・night・dawn）：窓の灯の明るさの倍率（OrdoView.BACK_MOOD）
func set_mood(mood: String) -> void:
	_mood_k = float(OrdoView.BACK_MOOD.get(mood, 0.0))
	_apply()


## 窓の灯：明るさ power、ちらつき flicker、消えた割合 out（OrdoView.set_back_lights と同じ）
func set_back_lights(power: float, flicker := 0.0, out := 0.0) -> void:
	back_power = maxf(power, 0.0)
	back_flicker = clampf(flicker, 0.0, 1.0)
	back_out = clampf(out, 0.0, 1.0)
	_apply()


func _apply() -> void:
	if _mat == null:
		return
	_mat.set_shader_parameter("power", back_power * _mood_k)
	_mat.set_shader_parameter("flicker", back_flicker)
	_mat.set_shader_parameter("out_amount", back_out)
