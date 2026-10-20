class_name NagomiView
extends Node3D
## ナゴミ（相棒の AI ドローン、直径 25cm）の見た目。ハルの右肩の横に少し遅れてついて行き、ふわふわ上下する。
## 仲間になる前（GameSim.nagomi_present() が偽：第 1 章の適合の前）は隠す。
## 感情（spec.md の 8 種）ごとに、種子光（核）の色・明るさ・明滅の速さと、殻 4 枚の開き具合を変える。
## 感情の決め方（pick_emotion）：ナゴミの会話が出ている間はその行の face → ロックオン中は analyzing →
## HP が少ないときは warning → それ以外は normal。
## モデル：nagomi.glb（tools/blender/recon/nagomi.py、npm run nagomi:build）。殻 shell_ul・ur・ll・lr は
## 原点が回転軸、ローカルの +X まわりに正に回すと開く。GLB がないときは光る小さな球で代わりにする。
##
## 背中のユニットへの着地（docs/design/20_ゲームシステム設計.md 5.1）。見た目だけで、ゲームの中身は変えない（ハルの状態から決める）。
## ・背中に付く：ハルが速く動く間（走る・ダッシュ・跳ぶ／落ちる・3 段斬り・溜め斬りと光刃の溜め）。胴のフレームの背中の板（動力部）に
##   背面の支持輪で付き、殻を閉じ、種子光を後ろへ向けて灯す（核の小さな光が背中の板と肩ひもを琥珀に照らす）。
## ・肩の横へ出る：立つ・歩くが CALM_OUT 秒続く、ナゴミが会話の行を話す、ロックオンの解析（相手の方へ少し寄る。解析の光の帯は
##   ナゴミから出る）、ノードの記憶の取り込み、台本の合図（fx の手順の nagomi_out・nagomi_at）。
## ・行き来：肩の上を回る弧（背中へ DOCK_TIME、肩へ UNDOCK_TIME 秒。終わりに小さな弾み）。体・頭を通らない（body_caps の外）。
##   着いたときは琥珀の小さな光（click。Fx が描く）、離れるときは小さな煙（take_cues → Fx）。
## ・そのままにする：会話のカメラの間（構図を崩さない。ナゴミが話しても背中のまま）、会話の行の間（世界が止まっている）。
##   部屋を移る・置き直す（snap）でも、付いている・出ているは変えない。
## ・付かない：胴のフレームが見えていない（付く前・装着の演出で隠している）、骨・群の無いモデル（以前の試作）、やられている間。
## ・確かめ用：force（"dock"・"out"。main の -- --nagomi=dock|out）。

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

# ---------------------------------------------------------------- 背中のユニット（着地）

enum Dock { OUT, DOCKING, DOCKED, UNDOCKING }
## 背中の板（haru_r の胴のフレーム Frame_core の back_plate。tools/blender/recon/chars/haru_parts.py）の外の面の中心と、外向き（後ろ）の法線。
## モデルの座標（+Z が正面なので背中は -Z）、骨の基準の姿勢で測った値。板は胸の骨（chest）に剛体で付いているので、胸の骨の姿勢で動かす。
## test_nagomi_seat_matches_model が GLB の頂点と比べる
const SOCKET_POS := Vector3(0.0, 1.074, -0.125)
const SOCKET_OUT := Vector3(0.0, 0.035, -0.999)
const SOCKET_BONE := "chest"
## 付いたときの、板の外の面からナゴミの中心まで（背面の支持輪の後ろの端 0.1195 m ＋すき間 6 mm）
const SEAT := 0.126
## 体の当たりの確かめに使うナゴミの半径（殻の球 0.1245 m）
const RADIUS := 0.125
## 立つ・歩くがこの秒数続いたら肩の横へ出る
const CALM_OUT := 0.6
## これより速く地面を走ると背中へ（m/s。歩きは 1.5〜、走る 7、ロックオン中の周回 6）
const FAST_SPEED := 3.5
## 走り出してからこの秒数で背中へ（スティックを一瞬倒した程度では入らない。ダッシュ・跳ぶ・斬るはすぐ）
const FAST_DELAY := 0.1
## 弧の秒数（背中へ・肩へ）と、着いたあとの弾み（秒・m。背中では外へ、肩では上へ 1 回）
const DOCK_TIME := 0.36
const UNDOCK_TIME := 0.32
const SETTLE_TIME := 0.14
const DOCK_HOP := 0.012
const UNDOCK_HOP := 0.025
## 弧のふくらみ（m）：胴の縦の軸から外へ・上へ。弧の真ん中でいちばん大きい（肩の上を回る）
const ARC_OUT := 0.11
const ARC_UP := 0.17
## 胴の縦の軸の前後の位置（ハルの足元の座標の z。弧と、近くでついて行くときの回り方の中心）
const AXIS_Z := -0.015
## 解析の間、肩の横から相手の方へ寄る距離（m）と、解析が終わってから出ている秒数（弱点への光の線）
const ANALYSE_LEAN := 0.3
const SCAN_HOLD := 0.4
## ノードの記憶の取り込み（Fx の node_memory と同じ 1.4 秒）の間は出ている
const NODE_HOLD := 1.4
## 着いたときの琥珀の光（Fx が click を読んで描く）の秒数
const CLICK_TIME := 0.25
## 背中に付いている間の、核の小さな光（背中の板・肩ひも・えりを照らす）：強さ（感情の明るさに掛ける）・届く距離・置き場所（ナゴミの中心から背中の側へ）
const DOCK_LIGHT := 0.3
const DOCK_LIGHT_RANGE := 0.42
const DOCK_LIGHT_Z := -0.03
## 体の当たり（body_caps。ナゴミの中心が RADIUS ＋この半径より近づかない）：胴（腰 → 首の骨。背中の板の面まで 0.108 m）・
## 肩（左右の上腕の付け根を結ぶ）・上腕（付け根 → 肘）・頭と髪（頭の骨の付け根から HEAD_C の球。髪の先まで）
const BODY_R := 0.10
const SHOULDER_R := 0.075
const ARM_R := 0.065
const HEAD_C := Vector3(0.0, 0.20, 0.0)
const HEAD_R := 0.20
const CAP_BONES := ["hips", "neck", "head", "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R"]
## 骨が無いとき（以前の試作・PlayerView の無いテスト）の体の当たり：haru_r の待機の姿勢に近い値（ハルの足元の座標）
const CAP_REST := {
	"hips": Vector3(0.0, 0.728, -0.008), "neck": Vector3(0.0, 1.128, -0.018), "head": Vector3(0.0, 1.18, -0.034),
	"upper_arm.L": Vector3(0.137, 1.105, -0.031), "upper_arm.R": Vector3(-0.137, 1.105, -0.031),
	"forearm.L": Vector3(0.19, 0.86, -0.03), "forearm.R": Vector3(-0.19, 0.86, -0.03),
}

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

## 背中のユニット：今の状態（Dock）と、確かめ用の強制（"dock"・"out"・""）
var dock_state := Dock.OUT
var force := ""
## 背中へ寄った割合（0 = 肩の横、1 = 付いている）：殻を閉じる・光を背中へ向ける・向きを受け口へ合わせる
var dock_k := 0.0
## 着いたときの光（1 → 0。Fx が描く）と、背中の板の外の面の中心・外向き（ワールド。光と煙の出る所）
var click := 0.0
var dock_point := Vector3.ZERO
var dock_normal := Vector3.BACK
var _cues: Array = []
var _pv: Node3D = null
var _base := Vector3.ZERO
var _t := 0.0
var _from := Vector3.ZERO
var _calm := 0.0
var _fast := 0.0
var _settle := -1.0
var _scan_hold := 0.0
var _node_t := 0.0
var _script := ""
var _script_at := Vector3.ZERO
var _sock := {}
var _bones := {}


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


## 1 刻みごと：背中か肩か・位置・向き・感情を進める。pv：ハルの見た目（PlayerView。背中の板の受け口と体の当たりを読む）、
## talking：会話のカメラが寄っている（main が CameraRig.talk_weight() > 0 を渡す。その間は背中・肩を変えない）
func sync(game, cam_pos: Vector3, dt: float, pv: Node3D = null, talking := false) -> void:
	_time += dt
	if pv != _pv:
		_pv = pv
		_sock = {}
		_bones = {}
	# 仲間になる前は出さない（第 1 章の適合の前）。出てきた刻みはハルの横へすぐに置く
	var present: bool = game.nagomi_present()
	if present != visible:
		visible = present
		if present:
			dock_state = Dock.OUT
			_calm = 0.0
			_fast = 0.0
			snap(game.player)
	if not present:
		return
	emotion = pick_emotion(game)
	# ヒットストップの間は、ハルの動作と同じく弧・ついて行くのも止める
	var mdt := 0.0 if float(game.hitstop) > 0.0 else dt
	var fr := _frame(game.player)
	var want := _want_dock(game, mdt, talking)
	if want and (dock_state == Dock.OUT or dock_state == Dock.UNDOCKING):
		_start(Dock.DOCKING, fr)
	elif not want and (dock_state == Dock.DOCKING or dock_state == Dock.DOCKED):
		_start(Dock.UNDOCKING, fr)
	_move(game, fr, cam_pos, mdt, dt)
	_apply(dt)


## 出来事（main が渡す）：台本の見た目の合図（fx の手順）。nagomi_out：肩の横へ出す、nagomi_dock：背中へ、nagomi_at：その位置へ
## （"pos"・"at"＋"height"）、nagomi_auto：ふだんの決め方へ戻す。台本（イベント・会話）が終わると自然に戻る。
## node_memory（ノードの記憶の取り込み）の間は出ている（ノードからナゴミへ光が流れ込む）
func handle(e: Dictionary) -> void:
	if String(e.get("type", "")) != "fx":
		return
	match String(e.get("id", "")):
		"nagomi_out":
			_script = "out"
		"nagomi_dock":
			_script = "dock"
		"nagomi_auto":
			_script = ""
		"nagomi_at":
			if e.get("at") is Vector3:
				_script = "at"
				_script_at = e.at
		"node_memory":
			if not e.get("skipped", false):
				_node_t = NODE_HOLD


## ハルの動き：0 = 立つ・歩く、1 = 走る（FAST_DELAY 秒続いたら背中へ）、2 = すぐ背中へ（ダッシュ・跳ぶ／落ちる・光刃の攻撃
## （3 段斬り・溜め斬り・ダッシュ斬り・踏み込み斬り・空中斬り）・光刃を溜めている・登る）。やられている間は 0
static func motion_kind(p) -> int:
	if p.dead:
		return 0
	# 登る動作は今は無い（足したら Player に climbing を持たせる）
	if p.dash_time > 0.0 or not p.grounded or p.attack != null or p.sword_hold > 0.25 or p.get("climbing") == true:
		return 2
	return 1 if p.speed() > FAST_SPEED else 0


## 背中へ入る（true）か、肩の横へ出る（false）か
func _want_dock(game, dt: float, talking: bool) -> bool:
	var p = game.player
	var docked := dock_state == Dock.DOCKING or dock_state == Dock.DOCKED
	var d: Dictionary = game.story.dialogue
	# 台本の合図は、その台本（イベント・会話）が終わるまで
	if _script != "" and d.is_empty() and not game.story.running_event():
		_script = ""
	# 解析の間と、終わってから SCAN_HOLD 秒は出ている
	var t = game.lock_on.target
	if t != null and t.alive and game.lock_on.scan_progress() < 1.0:
		_scan_hold = SCAN_HOLD
	else:
		_scan_hold = maxf(0.0, _scan_hold - dt)
	_node_t = maxf(0.0, _node_t - dt)
	if force == "out" or p.dead or back_socket(_pv) == null:
		return false
	if force == "dock":
		return true
	# 会話のカメラの間は、今のまま（背中にいれば、ナゴミが話しても背中のまま。構図はナゴミの肩の横の位置を避けて選んである）
	if talking or TalkCamera.partner(game) != null:
		return docked
	var speaking: bool = not d.is_empty() and d.get("who", "") == "ナゴミ"
	if speaking or _scan_hold > 0.0 or _node_t > 0.0 or _script == "out" or _script == "at":
		return false
	if _script == "dock":
		return true
	# ほかの人の会話の行の間は世界が止まっている（ハルの速さも止まったまま）：今のまま
	if not d.is_empty():
		return docked
	var kind := motion_kind(p)
	if kind > 0:
		_fast += dt
		_calm = 0.0
		return true if kind == 2 or _fast >= FAST_DELAY else docked
	_fast = 0.0
	_calm += dt
	return false if _calm >= CALM_OUT else docked


## 弧を始める（今の位置から）。背中から離れるときは煙の合図を Fx へ
func _start(state: int, fr: Transform3D) -> void:
	if state == Dock.UNDOCKING and dock_state == Dock.DOCKED:
		_cues.append({"type": "undock", "at": dock_point, "n": dock_normal})
	dock_state = state
	_t = 0.0
	_from = fr.affine_inverse() * _base
	_settle = -1.0


## 位置と向き。mdt：弧・ついて行くの刻み（ヒットストップの間は 0）
func _move(game, fr: Transform3D, cam_pos: Vector3, mdt: float, dt: float) -> void:
	var inv := fr.affine_inverse()
	var sock = back_socket(_pv)
	if sock != null:
		dock_point = sock.origin
		dock_normal = sock.basis.z
	var caps := body_caps(fr)
	var hop := Vector3.ZERO
	var k := 0.0
	if _settle >= 0.0:
		_settle += mdt
		if _settle >= SETTLE_TIME:
			_settle = -1.0
	var bounce := sin(PI * _settle / SETTLE_TIME) if _settle >= 0.0 else 0.0
	if (dock_state == Dock.DOCKING or dock_state == Dock.DOCKED) and sock == null:
		dock_state = Dock.OUT
	match dock_state:
		Dock.OUT:
			var c := follow_step(inv * _base, inv * _out_target(game, fr), 1.0 - exp(-FOLLOW * mdt))
			_base = fr * clear_of_body(c, caps)
			hop = Vector3.UP * UNDOCK_HOP * bounce
		Dock.DOCKING:
			_t = minf(1.0, _t + mdt / DOCK_TIME)
			var c := arc_point(_from, inv * seat_of(sock), _t)
			# 体から押し出す（終わりの着地は受け口へそのまま：受け口は背中の板に触れる所）
			c = clear_of_body(c, caps).lerp(c, smoothstep(0.75, 1.0, _t))
			_base = fr * c
			k = smoothstep(0.0, 1.0, _t)
			if _t >= 1.0:
				dock_state = Dock.DOCKED
				_settle = 0.0
				click = 1.0 + dt / CLICK_TIME
		Dock.DOCKED:
			_base = seat_of(sock)
			k = 1.0
			hop = dock_normal * DOCK_HOP * bounce
		Dock.UNDOCKING:
			_t = minf(1.0, _t + mdt / UNDOCK_TIME)
			var c := arc_point(_from, inv * _out_target(game, fr), _t)
			# 始めは受け口（背中の板に触れている）から外へ出るので、押し出しは少しずつ
			c = c.lerp(clear_of_body(c, caps), smoothstep(0.0, 0.25, _t))
			_base = fr * c
			k = 1.0 - smoothstep(0.0, 0.7, _t)
			if _t >= 1.0:
				dock_state = Dock.OUT
				_settle = 0.0
	click = maxf(0.0, click - dt / CLICK_TIME)
	dock_k = k
	var b := _out_basis(game, cam_pos, dt)
	if sock != null and k > 0.0:
		b = b.slerp(sock.basis, k)
	global_transform = Transform3D(b, _base + hop)


## 肩の横にいるときの向き：ふだんはハルの向きとカメラの間（後ろのカメラから種子光が見えるように、少し振り返る）、
## ナゴミが話している間はカメラへ、解析中は相手へ（少しだけカメラ寄り）。困惑で首をかしげ、上下の揺れに合わせて小さく傾く
func _out_basis(game, cam_pos: Vector3, dt: float) -> Basis:
	var p = game.player
	var cv: Vector3 = cam_pos - _base
	var cam_yaw := atan2(cv.x, cv.z)
	# カメラが真後ろのとき向きが左右に跳ねないよう、回る向きはハルの右（ナゴミのいる外側）回りに決める
	var want: float = p.yaw + wrapf(cam_yaw - p.yaw, -1.5 * PI, 0.5 * PI) * LOOK_BACK
	var d: Dictionary = game.story.dialogue
	if not d.is_empty() and d.get("who", "") == "ナゴミ":
		want = cam_yaw
	elif game.lock_on.target != null:
		var v: Vector3 = game.lock_on.target.center() - _base
		want = lerp_angle(atan2(v.x, v.z), cam_yaw, 0.3)
	_yaw += wrapf(want - _yaw, -PI, PI) * (1.0 - exp(-5.0 * dt))
	var roll := (0.25 if emotion == "confused" else 0.0) * sin(_time * 1.3) + 0.04 * sin(_time * 1.7)
	return Basis.from_euler(Vector3(0.0, _yaw, roll))


## 瞬間移動・部屋の移動・スキップのあと：遅れずにその場へ置く。背中に付いている・肩の横にいるはそのまま（弧の途中なら終わりの姿に）。
## pv：ハルの見た目（作り直したとき）
func snap(p, pv: Node3D = null) -> void:
	if pv != null and pv != _pv:
		_pv = pv
		_sock = {}
		_bones = {}
	if dock_state == Dock.DOCKING:
		dock_state = Dock.DOCKED
	elif dock_state == Dock.UNDOCKING:
		dock_state = Dock.OUT
	_settle = -1.0
	click = 0.0
	_yaw = p.yaw
	var sock = back_socket(_pv) if dock_state == Dock.DOCKED else null
	if sock != null:
		_base = seat_of(sock)
		dock_k = 1.0
		global_transform = Transform3D(sock.basis, _base)
	else:
		dock_state = Dock.OUT
		dock_k = 0.0
		_base = _frame(p) * Vector3(-OFFSET.x, OFFSET.y, OFFSET.z)
		global_transform = Transform3D(Basis(Vector3.UP, _yaw), _base)
	reset_physics_interpolation()


## 肩の横（OFFSET、上下の揺れつき）。解析の間は相手の方へ ANALYSE_LEAN 寄る（解析の光の帯がナゴミから出る）。台本が決めた位置ならそこ
func _out_target(game, fr: Transform3D) -> Vector3:
	if _script == "at":
		return _script_at
	var bob := BOB * sin(_time * 2.2) if emotion != "dormant" else 0.0
	var w := fr * Vector3(-OFFSET.x, OFFSET.y + bob, OFFSET.z)
	var t = game.lock_on.target
	if _scan_hold > 0.0 and t != null:
		var v: Vector3 = t.center() - w
		v.y = 0.0
		if v.length() > 0.5:
			w += v.normalized() * ANALYSE_LEAN + Vector3(0, 0.04, 0)
	return w


## ハルの足元の座標（+Z が正面、-X がハルの右）：見た目（PlayerView）があればその位置と向き、無ければゲームの中身の位置と向き
func _frame(p) -> Transform3D:
	if _pv != null and is_instance_valid(_pv):
		return Transform3D(Basis(Vector3.UP, _pv.rotation.y), _pv.global_position)
	return Transform3D(Basis(Vector3.UP, p.yaw), p.pos)


## 背中のユニットの受け口（ワールド）：原点は背中の板の外の面の中心、+Z が外向き（後ろ）、+Y が上。胸の骨の今の姿勢について行く。
## 胴のフレームが見えていない（まだ付いていない・装着の演出で隠している）か、骨・群の無いモデル（以前の試作など）なら null
func back_socket(pv) -> Variant:
	if pv == null or not is_instance_valid(pv) or not pv.has_method("frame_shown") or not pv.frame_shown("core"):
		return null
	var sk: Skeleton3D = pv.get("skeleton")
	var mdl: Node3D = pv.get("model")
	if sk == null or mdl == null:
		return null
	if _sock.get("id", 0) != sk.get_instance_id():
		var bone := sk.find_bone(SOCKET_BONE)
		if bone < 0:
			return null
		# モデルの座標の受け口を、胸の骨の基準の姿勢から見た置き場所にする（あとは骨の今の姿勢を掛けるだけ）
		var skel_in_model := mdl.global_transform.affine_inverse() * sk.global_transform
		var rest := Transform3D(socket_basis(SOCKET_OUT), SOCKET_POS)
		_sock = {"id": sk.get_instance_id(), "bone": bone,
			"local": sk.get_bone_global_rest(bone).affine_inverse() * skel_in_model.affine_inverse() * rest}
	var t: Transform3D = sk.global_transform * sk.get_bone_global_pose(_sock.bone) * _sock.local
	return t.orthonormalized()


## 受け口に付いたときのナゴミの中心（ワールド）
static func seat_of(sock: Transform3D) -> Vector3:
	return sock.origin + sock.basis.z * SEAT


## 外向き out を +Z、上を +Y にした向き
static func socket_basis(out: Vector3) -> Basis:
	var z := out.normalized()
	var x := Vector3.UP.cross(z).normalized()
	return Basis(x, z.cross(x), z)


## ハルの体の当たり：[端 a, 端 b, 半径] の並び（ハルの足元の座標 fr で）。骨の今の姿勢から作る（走る・斬るの姿勢にもついて行く）：
## 胴（腰 → 首）、肩（左右の上腕の付け根）、上腕（付け根 → 肘）×2、頭と髪（頭の骨の付け根から HEAD_C の球）。
## 骨の無いモデル・見た目の無いときは CAP_REST
func body_caps(fr: Transform3D) -> Array:
	var pts := CAP_REST.duplicate()
	var sk: Skeleton3D = _pv.get("skeleton") if _pv != null and is_instance_valid(_pv) else null
	if sk != null:
		if _bones.get("id", 0) != sk.get_instance_id():
			_bones = {"id": sk.get_instance_id()}
			for nm in CAP_BONES:
				_bones[nm] = sk.find_bone(nm)
		var to := fr.affine_inverse() * sk.global_transform
		for nm in CAP_BONES:
			if int(_bones[nm]) >= 0:
				pts[nm] = to * sk.get_bone_global_pose(int(_bones[nm])).origin
		if int(_bones["head"]) >= 0:
			pts["head"] = to * (sk.get_bone_global_pose(int(_bones["head"])) * HEAD_C)
		else:
			pts["head"] = pts["head"] + HEAD_C
	else:
		pts["head"] = pts["head"] + HEAD_C
	return [[pts["hips"], pts["neck"], BODY_R], [pts["upper_arm.L"], pts["upper_arm.R"], SHOULDER_R],
		[pts["upper_arm.L"], pts["forearm.L"], ARM_R], [pts["upper_arm.R"], pts["forearm.R"], ARM_R],
		[pts["head"], pts["head"], HEAD_R]]


## 点 c（ナゴミの中心）と体の当たりのすき間（m。負ならめり込んでいる）
static func body_gap(c: Vector3, caps: Array) -> float:
	var g := INF
	for cp in caps:
		var q := Geometry3D.get_closest_point_to_segment(c, cp[0], cp[1])
		g = minf(g, c.distance_to(q) - float(cp[2]) - RADIUS)
	return g


## 体の当たりにめり込まないように、いちばん深い所から外へ押し出す（3 回まで）
static func clear_of_body(c: Vector3, caps: Array) -> Vector3:
	for it in 3:
		var worst := 0.0
		var push := Vector3.ZERO
		for cp in caps:
			var q := Geometry3D.get_closest_point_to_segment(c, cp[0], cp[1])
			var v := c - q
			var need := float(cp[2]) + RADIUS - v.length()
			if need > worst:
				worst = need
				# 軸の上に乗っている（ほぼ無い）ときは、胴の軸から水平に外へ
				var dir := v.normalized() if v.length() > 1e-4 else Vector3(c.x, 0.0, c.z - AXIS_Z).normalized()
				push = dir * need
		if worst <= 0.0:
			break
		c += push
	return c


## 胴の縦の軸のまわりの座標：(角度：0 = 背中・+PI/2 = ハルの右, 軸からの距離, 高さ)
static func _cyl(v: Vector3) -> Vector3:
	return Vector3(atan2(-v.x, -(v.z - AXIS_Z)), Vector2(v.x, v.z - AXIS_Z).length(), v.y)


static func _from_cyl(th: float, rho: float, h: float) -> Vector3:
	return Vector3(-rho * sin(th), h, AXIS_Z - rho * cos(th))


## 角度 a から b への回り方：背中の側を回る（顔の前を横切らない）。背中の側がずっと遠い（1.2 回りの半分より長い）ときだけ前を回る
static func _turn(a: float, b: float) -> float:
	var d := b - a
	return d if absf(d) <= 1.2 * PI else wrapf(d, -PI, PI)


## 背中と肩の間の弧（ハルの足元の座標）：胴の縦の軸のまわりの角度・軸からの距離・高さを別々になめらかに変え、途中で外へ ARC_OUT・
## 上へ ARC_UP ふくらませる（肩の上を回る）。t：0〜1。終わりは上の後ろから下りて受け口に着く
static func arc_point(a: Vector3, b: Vector3, t: float) -> Vector3:
	var ca := _cyl(a)
	var cb := _cyl(b)
	var e := smoothstep(0.0, 1.0, t)
	var s := sin(PI * t)
	return _from_cyl(ca.x + _turn(ca.x, cb.x) * e, lerpf(ca.y, cb.y, e) + ARC_OUT * s, lerpf(ca.z, cb.z, e) + ARC_UP * s)


## 肩の横へついて行く 1 刻み（割合 k だけ寄る）。ハルの近く（軸から 1.5 m 以内）では、縦の軸のまわりの角度・距離・高さで寄る
## （ハルが向きを変えても、体・頭を突き抜けずに背中の側を回る）。遠い所（台本の位置など）はまっすぐ寄る
static func follow_step(c: Vector3, to: Vector3, k: float) -> Vector3:
	var a := _cyl(c)
	var b := _cyl(to)
	if a.y > 1.5 or b.y > 1.5:
		return c.lerp(to, k)
	return _from_cyl(a.x + _turn(a.x, b.x) * k, lerpf(a.y, b.y, k), lerpf(a.z, b.z, k))


## Fx が刻みごとに受け取る合図（背中から離れたときの煙：{type: "undock", at: 背中の板の中心, n: 外向き}）
func take_cues() -> Array:
	var c := _cues
	_cues = []
	return c


## 感情の値へ、色・明るさ・殻の角度をなめらかに寄せる（dt = 0 ならすぐに合わせる）。背中に寄った割合（dock_k）だけ殻を閉じ、
## 核の小さな光を背中の側へ移して強める（背中の板・肩ひもが琥珀に照らされる）。着いたときは click の分だけ明るく
func _apply(dt: float) -> void:
	var e: Dictionary = EMOTIONS.get(emotion, EMOTIONS.normal)
	var k := 1.0 if dt <= 0.0 else 1.0 - exp(-8.0 * dt)
	_color = _color.lerp(Color(e.color), k)
	_energy = lerpf(_energy, e.energy, k)
	var blink := 1.0
	if e.period > 0.0:
		blink = 0.7 + 0.3 * (0.5 + 0.5 * sin(TAU * _time / e.period))
	var flash := 1.0 + 1.5 * click
	if core_mat:
		core_mat.albedo_color = _color
		core_mat.emission = _color
		core_mat.emission_energy_multiplier = _energy * blink * flash
	glow.light_color = _color
	glow.position = Vector3(0, 0, 0.2).lerp(Vector3(0, 0, DOCK_LIGHT_Z), dock_k)
	glow.omni_range = lerpf(0.5, DOCK_LIGHT_RANGE, dock_k)
	glow.light_energy = lerpf(0.08, DOCK_LIGHT, dock_k) * _energy * blink + 0.5 * click
	var ka := 1.0 if dt <= 0.0 else 1.0 - exp(-6.0 * dt)
	for i in shells.size():
		_angles[i] = lerpf(_angles[i], float(e.open[i]), ka)
		shells[i].transform = shell_rest[i] * Transform3D(Basis(Vector3.RIGHT, deg_to_rad(_angles[i] * (1.0 - dock_k))), Vector3.ZERO)


## 殻をすぐに決まった角度にする（確認の画像用。STATES の名前か、4 枚の角度）
func set_shells(angles: Array) -> void:
	for i in shells.size():
		_angles[i] = float(angles[i])
		shells[i].transform = shell_rest[i] * Transform3D(Basis(Vector3.RIGHT, deg_to_rad(_angles[i])), Vector3.ZERO)
