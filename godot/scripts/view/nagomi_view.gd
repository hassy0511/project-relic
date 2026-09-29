class_name NagomiView
extends Node3D
## ナゴミ（相棒の AI ドローン、直径 25cm）の見た目。ハルの右肩の横に少し遅れてついて行き、ふわふわ上下する。
## 感情（spec.md の 8 種）ごとに、種子光（核）の色・明るさ・明滅の速さと、殻 4 枚の開き具合を変える。
## 感情の決め方（pick_emotion）：ナゴミの会話が出ている間はその行の face → ロックオン中は analyzing →
## HP が少ないときは warning → それ以外は normal。
## モデル：nagomi.glb（tools/blender/recon/nagomi.py、npm run nagomi:build）。殻 shell_ul・ur・ll・lr は
## 原点が回転軸、ローカルの +X まわりに正に回すと開く。GLB がないときは光る小さな球で代わりにする。

const MODEL_PATH := "res://assets/models/nagomi.glb"
const SHELLS := ["shell_ul", "shell_ur", "shell_ll", "shell_lr"]  # 正面から見て左上・右上・左下・右下
const STATES := {"closed": 0.0, "half": 11.0, "open": 22.0}  # 殻の 3 状態（度、nagomi.py の OPEN_DEG。絵の全開の正面に合わせた）
const LOW_HP := 0.3  # HP がこの割合以下なら warning

## 感情：光の色（spec.md の hex）、明滅の周期（秒、0 は明滅なし）、明るさ、殻 4 枚の角度（度、SHELLS の順）
const EMOTIONS := {
	"normal": {"color": "#FFBC52", "period": 1.2, "energy": 1.2, "open": [0, 0, 0, 0]},
	"analyzing": {"color": "#F8D47B", "period": 0.6, "energy": 1.5, "open": [5, 5, 5, 5]},
	"warning": {"color": "#E9783C", "period": 0.4, "energy": 1.8, "open": [11, 11, 11, 11]},
	"happy": {"color": "#FFE18A", "period": 1.0, "energy": 1.8, "open": [20, 20, 20, 20]},
	"confused": {"color": "#E9B28C", "period": 2.0, "energy": 1.0, "open": [9, 3, 8, 2]},
	"sad": {"color": "#B39174", "period": 2.8, "energy": 0.6, "open": [2, 2, 2, 2]},
	"joking": {"color": "#F8C963", "period": 1.1, "energy": 1.3, "open": [12, 12, 4, 4]},
	"dormant": {"color": "#4D443A", "period": 0.0, "energy": 0.0, "open": [0, 0, 0, 0]},
}

## ハルから見た位置（m）：右へ・上へ・前へ（nagomi_with_haru.png：頭の横、肩の少し上）
const OFFSET := Vector3(0.40, 1.32, -0.08)
const FOLLOW := 6.0  # ついて行く速さ（大きいほど遅れが少ない）
const BOB := 0.025  # 上下の揺れ（m）
const LOOK_BACK := 0.85  # ふだんの向き：0 = ハルと同じ向き、1 = カメラを向く

var model: Node3D
var shells: Array[Node3D] = []
var shell_rest: Array[Transform3D] = []
var core_mat: StandardMaterial3D
var glow: OmniLight3D
var emotion := "normal"
var _angles := [0.0, 0.0, 0.0, 0.0]
var _color := Color("#FFBC52")
var _energy := 1.2
var _time := 0.0
var _yaw := 0.0


func _ready() -> void:
	if ResourceLoader.exists(MODEL_PATH):
		model = (load(MODEL_PATH) as PackedScene).instantiate()
		add_child(model)
		for n in SHELLS:
			var s := model.find_child(n, true, false) as Node3D
			if s:
				shells.append(s)
				shell_rest.append(s.transform)
		var core := model.find_child("core", true, false) as MeshInstance3D
		if core and core.mesh.get_surface_count() > 0:
			core_mat = _emissive(core.mesh.surface_get_material(0))
			core.set_surface_override_material(0, core_mat)
		for mi in model.find_children("*", "MeshInstance3D", true, false):
			(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	else:
		# GLB がないとき（テストの環境など）：光る小さな球
		var mi := MeshInstance3D.new()
		var sph := SphereMesh.new()
		sph.radius = 0.1
		sph.height = 0.2
		mi.mesh = sph
		core_mat = _emissive(null)
		mi.material_override = core_mat
		add_child(mi)
		model = mi
	glow = OmniLight3D.new()
	glow.omni_range = 0.5
	glow.light_energy = 0.0
	glow.shadow_enabled = false
	glow.position = Vector3(0, 0, 0.2)  # 殻の前（内側を照らしすぎないように）
	add_child(glow)
	_apply(0.0)


## 核の材質（複製して感情ごとに書き換える）
func _emissive(src: Material) -> StandardMaterial3D:
	var m: StandardMaterial3D
	if src is StandardMaterial3D:
		m = src.duplicate()
	else:
		m = StandardMaterial3D.new()
		m.albedo_color = Color("#FFBC52")
	m.emission_enabled = true
	return m


## 感情を決める（データの優先順：ナゴミの会話の face → ロックオン → HP が少ない → 通常）
static func pick_emotion(game) -> String:
	var d: Dictionary = game.story.dialogue
	if not d.is_empty() and d.get("who", "") == "ナゴミ":
		var f: String = d.get("face", "normal")
		return f if EMOTIONS.has(f) else "normal"
	if game.lock_on.target != null:
		return "analyzing"
	if game.player.hp <= game.player.max_hp * LOW_HP:
		return "warning"
	return "normal"


## 1 刻みごと：位置・向き・感情を進める
func sync(game, cam_pos: Vector3, dt: float) -> void:
	_time += dt
	emotion = pick_emotion(game)
	var p = game.player
	global_position = global_position.lerp(_target(p), 1.0 - exp(-FOLLOW * dt))
	# 向き：ふだんはハルの向きとカメラの間（後ろのカメラから種子光が見えるように、少し振り返る）、
	# ナゴミが話している間はカメラへ、解析中は相手へ（少しだけカメラ寄り）
	var cv: Vector3 = cam_pos - global_position
	var cam_yaw := atan2(cv.x, cv.z)
	# カメラが真後ろのとき向きが左右に跳ねないよう、回る向きはハルの右（ナゴミのいる外側）回りに決める
	var want: float = p.yaw + wrapf(cam_yaw - p.yaw, -1.5 * PI, 0.5 * PI) * LOOK_BACK
	var d: Dictionary = game.story.dialogue
	if not d.is_empty() and d.get("who", "") == "ナゴミ":
		want = cam_yaw
	elif game.lock_on.target != null:
		var v: Vector3 = game.lock_on.target.center() - global_position
		want = lerp_angle(atan2(v.x, v.z), cam_yaw, 0.3)
	_yaw += wrapf(want - _yaw, -PI, PI) * (1.0 - exp(-5.0 * dt))
	rotation.y = _yaw
	# 首をかしげる程度の傾き（困惑）と、上下の揺れに合わせた小さな傾き
	rotation.z = (0.25 if emotion == "confused" else 0.0) * sin(_time * 1.3) + 0.04 * sin(_time * 1.7)
	_apply(dt)


## 瞬間移動のあと：遅れずにその場へ置く
func snap(p) -> void:
	global_position = _target(p)
	_yaw = p.yaw
	rotation.y = _yaw
	reset_physics_interpolation()


func _target(p) -> Vector3:
	var yaw: float = p.yaw
	var right := Vector3(-cos(yaw), 0.0, sin(yaw))
	var fwd := Vector3(sin(yaw), 0.0, cos(yaw))
	var bob := BOB * sin(_time * 2.2) if emotion != "dormant" else 0.0
	return p.pos + right * OFFSET.x + Vector3(0, OFFSET.y + bob, 0) + fwd * OFFSET.z


## 感情の値へ、色・明るさ・殻の角度をなめらかに寄せる（dt = 0 ならすぐに合わせる）
func _apply(dt: float) -> void:
	var e: Dictionary = EMOTIONS.get(emotion, EMOTIONS.normal)
	var k := 1.0 if dt <= 0.0 else 1.0 - exp(-8.0 * dt)
	_color = _color.lerp(Color(e.color), k)
	_energy = lerpf(_energy, e.energy, k)
	var blink := 1.0
	if e.period > 0.0:
		blink = 0.7 + 0.3 * (0.5 + 0.5 * sin(TAU * _time / e.period))
	if core_mat:
		core_mat.albedo_color = _color
		core_mat.emission = _color
		core_mat.emission_energy_multiplier = _energy * blink
	glow.light_color = _color
	glow.light_energy = 0.08 * _energy * blink
	var ka := 1.0 if dt <= 0.0 else 1.0 - exp(-6.0 * dt)
	for i in shells.size():
		_angles[i] = lerpf(_angles[i], float(e.open[i]), ka)
		shells[i].transform = shell_rest[i] * Transform3D(Basis(Vector3.RIGHT, deg_to_rad(_angles[i])), Vector3.ZERO)


## 殻をすぐに決まった角度にする（確認の画像用。STATES の名前か、4 枚の角度）
func set_shells(angles: Array) -> void:
	for i in shells.size():
		_angles[i] = float(angles[i])
		shells[i].transform = shell_rest[i] * Transform3D(Basis(Vector3.RIGHT, deg_to_rad(_angles[i])), Vector3.ZERO)
