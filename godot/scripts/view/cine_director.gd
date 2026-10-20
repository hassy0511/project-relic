class_name CineDirector
extends Node
## 映画のような場面（第 1 章のオープニング・オルドの停止）の見た目と音。台本の shot（カメラの道筋）を受けてカメラを動かし、
## 巡礼機オルドの足音・砂ぼこり・揺れ・風・背の町の灯・動力が切れる演出（fx: ordo_stop）を出す。ゲームの中身（GameSim）は読むだけで変えない。
## 書き方：docs/design/42_コンテンツの書き方.md 6.1、結果：docs/art_orders/W2_オルド3D化の結果.md 11 章。
##
## 道筋（shot）：time 秒で eye（カメラの場所）と look（見る所）の点の並びをなめらかにたどる（2 点は直線、3 点以上は Catmull-Rom）。
##   frame："room"（部屋の座標）・"ordo"（オルドの座標：原点 = 背の歩行面の真ん中、+Z が船首、地面は y = -120）・
##   "ground"（オルドの座標で道筋を始め、そのあと砂の地面と一緒に後ろへ流れる：地面に立つカメラ）。
##   点の代わりに "play" と書くと、ふだんの遊びのカメラ（ハルの後ろ）の場所・見る所（最後の点に書くと、そのまま遊びのカメラへ渡せる）。
##   部屋にオルドがいない（家の中の停止の場面）ときは、外の舞台（stage：オルドと砂の床と背の町の灯、夜の空）を出し、部屋を隠す。
## カメラは遊びのカメラ（CameraRig）が決めた姿のあとに上書きする（main._physics_process で camera.sync の次）。
## 場面のオルドの時計は、場面の間はここが刻みごとに進める（OrdoView の _process を止める）：足が着く時刻が台本の待ちと同じ時計になり、
## ポーズ・撮影で止めている間はオルドも止まる。場面が終わると OrdoView に返す。
## スキップ（skipped）・部屋の移動（roomChanged）・{"shot": {}} で、道筋・舞台・霞などを元へ戻す。

## 砂ぼこりの色（雰囲気ごと。照らされない粒なので、光の当たった砂の色をそのまま）
const DUST := {"dawn": Color("#b07c66"), "night": Color("#454f72"), "day": Color("#cba27e")}
## 町の灯の明るさと、遠くの灯の最小の大きさ（画素）（雰囲気ごと。夜明けは空が明るいので強く、夜は大きめ）
const LIGHT_POWER := {"dawn": 1.0, "night": 0.9, "day": 0.5}
const LIGHT_PX := {"dawn": 5.5, "night": 7.0, "day": 4.0}
## 風の大きさ（dB。効果音の音量から）
const WIND_DB := -9.0
## 霞・カメラの遠く・砂の床の消える距離の既定（元に戻す値）
const GROUND_FADE := Vector2(320.0, 850.0)

var main
## 今の道筋（空ならふだんのカメラ）と、始めてからの秒
var shot := {}
var shot_t := 0.0
## 道筋の座標の元のオルド（部屋のオルドか、外の舞台）。外の舞台（部屋にオルドがいないとき）
var _ordo: OrdoView = null
var stage: OrdoView = null
var _stage_mood := ""
## "ground" の道筋：始めたときの地面のずれ
var _start_ofs := Vector3.ZERO
## 道筋の始めに前のカメラからつなぐ（"blend" 秒）とき、前のカメラの姿
var _from := {}
var _cut := false
## ふだんの遊びのカメラの、この刻みの姿（"play" の点）
var _play_eye := Vector3.ZERO
var _play_look := Vector3.ZERO
## 変えた環境の元の値（霞の濃さ・カメラの遠く）。空なら変えていない
var _env_saved := {}
var _room_hidden := false
## 足音の揺れ（足が着くたびに上げ、すぐ消える）と見た目の時計
var _kick := 0.0
var _time := 0.0
var _wind := false
## 動力が切れる演出（fx: ordo_stop）の経過の秒（負ならしていない）
var _stop_t := -1.0
var _stop_started := false
var _rng := RandomNumberGenerator.new()
## 時計を進めているオルド（場面のオルド。_process を止めている）
var _driven: OrdoView = null
## 確かめ用：足が着いた数・鳴らした足音・出した砂ぼこりの粒の数
var steps_heard := 0
var dust_puffs := 0


func _init(m) -> void:
	main = m
	_rng.seed = 1016


## 映画のような場面の途中か（道筋か外の舞台がある）
func active() -> bool:
	return not shot.is_empty() or stage != null


## 今の道筋の座標の元のオルド（無ければ null）
func ordo() -> OrdoView:
	return _ordo if _ordo != null and is_instance_valid(_ordo) else null


# ---------------------------------------------------------------- 出来事

func handle(e: Dictionary) -> void:
	match String(e.type):
		"shot":
			start_shot(e.shot)
		"fx":
			if String(e.id) == "ordo_stop" and not e.get("skipped", false):
				_start_stop()
		"skipped":
			reset()
		"roomChanged":
			if not e.get("first", false):
				reset()


## 道筋を始める（空なら終えて、ふだんのカメラへ）
func start_shot(sh: Dictionary) -> void:
	if sh.is_empty():
		_end_shot()
		return
	var frame := String(sh.get("frame", "room"))
	if frame == "room":
		_remove_stage()
		_ordo = main._ordo()
	else:
		var room_ordo: OrdoView = main._ordo()
		if room_ordo != null:
			_remove_stage()
			_ordo = room_ordo
		elif stage == null:
			_ordo = _make_stage(sh.get("stage", {}))
		else:
			_ordo = stage
		_ready_ordo(_ordo)
	if sh.has("blend") and not shot.is_empty():
		_from = {"eye": main.camera.global_position, "look": main.camera.global_position + main.camera.forward_dir() * 50.0,
			"fov": main.camera.fov, "time": maxf(float(sh.blend), 0.01)}
	else:
		_from = {}
	shot = sh
	shot_t = 0.0
	_cut = _from.is_empty()
	var o := ordo()
	_start_ofs = o.ground_offset() if o != null else Vector3.ZERO
	_apply_env(sh, 0.0)
	_set_room_visible(bool(sh.get("room", true)) and stage == null)
	if frame != "room" or stage != null:
		_set_wind(true, float(sh.get("wind", WIND_DB)))


## 道筋を終える：ふだんのカメラへ（すぐ。次の刻みで補間を切る）、外の舞台を片付け、霞などを戻す
func _end_shot() -> void:
	var had := not shot.is_empty()
	shot = {}
	_from = {}
	_restore_env()
	_remove_stage()
	_set_room_visible(true)
	_drive(null)
	if had and main.camera != null:
		main.camera.reset_physics_interpolation()


## すべて元へ（スキップ・部屋の移動・新しいゲーム）
func reset() -> void:
	_end_shot()
	_stop_t = -1.0
	_stop_started = false
	_kick = 0.0
	_set_wind(false)
	_ordo = null


# ---------------------------------------------------------------- 毎刻み

## main._physics_process から、遊びのカメラ（camera.sync）の次に呼ぶ
func sync(dt: float) -> void:
	_time += dt
	_kick = maxf(0.0, _kick - dt * 1.4)
	if _driven != null and is_instance_valid(_driven):
		_driven.advance(dt)
	_update_stop(dt)
	if shot.is_empty():
		return
	var cam: Camera3D = main.camera
	_play_eye = cam.global_position
	_play_look = cam.global_position + cam.forward_dir() * 5.5
	shot_t += dt
	var dur := maxf(float(shot.get("time", 1.0)), 0.001)
	var u := ease_value(clampf(shot_t / dur, 0.0, 1.0), String(shot.get("ease", "inout")))
	var eye := _path(shot.get("eye", []), u, true)
	var look := _path(shot.get("look", []), u, false)
	var fov := _num(shot.get("fov", cam.fov), u)
	if not _from.is_empty():
		var b := smoothstep(0.0, 1.0, clampf(shot_t / float(_from.time), 0.0, 1.0))
		eye = (_from.eye as Vector3).lerp(eye, b)
		look = (_from.look as Vector3).lerp(look, b)
		fov = lerpf(float(_from.fov), fov, b)
	# 揺れ：道筋の揺れ（"shake"）・足音・台本の shake（Fx）。遠くのカメラでも同じだけ揺れて見えるよう、見る所は距離に比べて動かす
	var amp := _num(shot.get("shake", 0.0), u) + _kick
	if main.fx != null:
		amp += float(main.fx.shake) * 0.5
	if amp > 0.001:
		var fwd := (look - eye).normalized()
		var right := fwd.cross(Vector3.UP).normalized()
		var up := right.cross(fwd)
		var t := _time
		var n1 := sin(t * 5.3) * 0.6 + sin(t * 11.7 + 1.3) * 0.4
		var n2 := sin(t * 6.1 + 2.1) * 0.6 + sin(t * 13.9 + 0.4) * 0.4
		var n3 := sin(t * 4.7 + 4.0) * 0.5 + sin(t * 9.3 + 3.2) * 0.5
		var dist := eye.distance_to(look)
		eye += (right * n1 + up * n2) * amp * 0.12
		look += (right * n3 + up * n1) * amp * 0.011 * dist
	cam.global_position = eye
	if (look - eye).length_squared() > 1e-6 and absf((look - eye).normalized().y) < 0.999:
		cam.look_at(look, Vector3.UP)
	cam.fov = fov
	if _cut:
		cam.reset_physics_interpolation()
		_cut = false
	_apply_env(shot, u)


## 進み u（0〜1）を緩める：linear・in（だんだん速く）・out（だんだん遅く）・inout（既定）・sine
static func ease_value(u: float, kind: String) -> float:
	match kind:
		"linear":
			return u
		"in":
			return u * u
		"out":
			return 1.0 - (1.0 - u) * (1.0 - u)
		"sine":
			return 0.5 - 0.5 * cos(PI * u)
	return u * u * (3.0 - 2.0 * u)


## 数か [始め, 終わり] の、進み u のときの値
static func _num(v, u: float) -> float:
	if v is Array:
		var a: Array = v
		if a.size() >= 2:
			return lerpf(float(a[0]), float(a[1]), u)
		return float(a[0]) if a.size() == 1 else 0.0
	return float(v)


## 点の並びの、進み u のときの位置（グローバル）
func _path(keys: Array, u: float, is_eye: bool) -> Vector3:
	var pts: Array[Vector3] = []
	for k in keys:
		pts.append(_to_world(k, is_eye))
	if pts.is_empty():
		return _play_eye if is_eye else _play_look
	if pts.size() == 1:
		return pts[0]
	if pts.size() == 2:
		return pts[0].lerp(pts[1], u)
	var n := pts.size() - 1
	var f := clampf(u, 0.0, 1.0) * n
	var i := mini(int(floor(f)), n - 1)
	var t := f - i
	var p0: Vector3 = pts[maxi(i - 1, 0)]
	var p1: Vector3 = pts[i]
	var p2: Vector3 = pts[i + 1]
	var p3: Vector3 = pts[mini(i + 2, n)]
	# Catmull-Rom（端は端の点を重ねる）
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)


## 道筋の 1 つの点をグローバルの位置へ（"play"・部屋・オルド・地面の座標）
func _to_world(k, is_eye: bool) -> Vector3:
	if k is String:
		return _play_eye if is_eye else _play_look
	var p := RoomGeo.v3(k)
	var frame := String(shot.get("frame", "room"))
	var o := ordo()
	if frame == "room" or o == null:
		return p
	var w := o.global_position + p
	if frame == "ground":
		w += o.ground_offset() - _start_ofs
	return w


# ---------------------------------------------------------------- 環境（霞・遠く・砂の床）・部屋を隠す

## 道筋の "fog"（霞の濃さ。数か [始め, 終わり]）・"far"（カメラの遠く m）・"ground_fade"（砂の床の消える距離 [始め, 終わり] m）
func _apply_env(sh: Dictionary, u: float) -> void:
	var env: Environment = main.sun.get_meta("env") if main.sun != null else null
	if sh.has("fog") and env != null:
		if not _env_saved.has("fog"):
			_env_saved["fog"] = env.fog_density
		env.fog_density = _num(sh.fog, u)
	if sh.has("far") and main.camera != null:
		if not _env_saved.has("far"):
			_env_saved["far"] = main.camera.far
		main.camera.far = float(sh.far)
	var o := ordo()
	if sh.has("ground_fade") and o != null:
		var gf: Array = sh.ground_fade
		o.set_ground_fade(float(gf[0]), float(gf[1]))
		_env_saved["ground_fade"] = true


func _restore_env() -> void:
	var env: Environment = main.sun.get_meta("env") if main.sun != null else null
	if _env_saved.has("fog") and env != null:
		env.fog_density = float(_env_saved.fog)
	if _env_saved.has("far") and main.camera != null:
		main.camera.far = float(_env_saved.far)
	var o := ordo()
	if _env_saved.has("ground_fade") and o != null:
		o.set_ground_fade(GROUND_FADE.x, GROUND_FADE.y)
	_env_saved = {}


## 部屋（地形・飾り・明かり）とハル・住人などの見た目を隠す・出す（オルドと砂ぼこりは残す）。遠くから全体を見る場面で描画を減らす
func _set_room_visible(on: bool) -> void:
	if on == not _room_hidden:
		return
	_room_hidden = not on
	if main.level != null and is_instance_valid(main.level):
		for c in main.level.get_children():
			if c.name != "Ordo" and c is Node3D:
				(c as Node3D).visible = on
	for v in [main.player_view, main.nagomi_view, main.props_view, main.enemy_view]:
		if v != null and is_instance_valid(v):
			v.visible = on


# ---------------------------------------------------------------- オルド（部屋のオルドか外の舞台）

## 場面のオルドの用意：砂の床（部屋が "ground": false でも出す）・背の町の灯・足の知らせ
func _ready_ordo(o: OrdoView) -> void:
	if o == null:
		return
	_drive(o)
	o.set_ground(true)
	var tl := o.add_town_lights()
	tl.power = LIGHT_POWER.get(_mood(), 1.0)
	tl.px = LIGHT_PX.get(_mood(), 5.5)
	tl.flicker = 0.0
	tl.out = 0.0
	tl.apply()
	if not o.foot_planted.is_connected(_on_planted):
		o.foot_planted.connect(_on_planted)


## 部屋にオルドがいないときの外の舞台：体が止まり砂の床が流れるオルド（背の町の影絵 ordo_town）を部屋の代わりに出し、空と光を外の雰囲気に
## （cfg：{ "mood": "night", "phase": 歩きの周期の位置 0〜1 }）
func _make_stage(cfg: Dictionary) -> OrdoView:
	var o := OrdoView.new()
	o.name = "CineStage"
	o.body_fixed = true
	o.ground = true
	o.back_part = String(cfg.get("back", "town/ordo_town"))
	o.phase = fposmod(float(cfg.get("phase", 0.0)), 1.0)
	main.add_child(o)
	stage = o
	_stage_mood = String(cfg.get("mood", "night"))
	EnvironmentSetup.apply_mood(main.sun, _stage_mood)
	var kd: Dictionary = RoomKit.load_kit("town").get("data", {})
	EnvironmentSetup.apply_sky(main.sun, String(kd.get("sky", {}).get(_stage_mood, "")), kd.get("light", {}).get(_stage_mood, {}))
	o.set_mood(_stage_mood)
	if main.level != null and is_instance_valid(main.level):
		main.level.visible = false
	_set_room_visible(false)
	return o


## このオルドの時計を場面の刻みで進める（null で前のオルドに返す）
func _drive(o: OrdoView) -> void:
	if _driven == o:
		return
	if _driven != null and is_instance_valid(_driven):
		_driven.set_process(true)
	_driven = o
	if o != null:
		o.set_process(false)


func _remove_stage() -> void:
	if stage == null:
		return
	if _driven == stage:
		_drive(null)
	if is_instance_valid(stage):
		stage.queue_free()
	if _ordo == stage:
		_ordo = null
	stage = null
	_stage_mood = ""
	if main.level != null and is_instance_valid(main.level):
		main.level.visible = true
	_set_room_visible(true)
	# 舞台の砂ぼこりは片付ける（部屋の下に残さない）。空と光は部屋の雰囲気へ
	if main.fx != null and main.fx.vfx != null:
		main.fx.vfx.clear()
	if main.game != null:
		main._apply_mood()


## 今の場面の雰囲気（舞台なら舞台の、部屋のオルドなら部屋の mood）
func _mood() -> String:
	if _stage_mood != "":
		return _stage_mood
	if main.game == null:
		return "day"
	var m := String(main.game.room.get("mood", "day"))
	if m == "outdoor" or m == "day":
		return "night" if main.game.flag("ch1.night") else "day"
	return m


# ---------------------------------------------------------------- 足音・砂ぼこり

func _on_planted(tag: String, at: Vector3) -> void:
	if not active():
		return
	var o := ordo()
	var heavy := o != null and o.cine_stopping()
	var d: float = main.camera.global_position.distance_to(at) if main.camera != null else 300.0
	steps_heard += 1
	# 大きさは距離で（150 m で 0 dB、近くは +5 まで、遠くは -22 まで）。止まるときの足は重く低く
	var gain := clampf(-20.0 * log(maxf(d, 30.0) / 150.0) / log(10.0), -22.0, 5.0)
	if heavy:
		main.audio.play_gain("ordo_step", gain + 5.0, 0.82)
		main.audio.play_gain("rumble", gain + 1.0, 0.75)
	else:
		main.audio.play_gain("ordo_step", gain, _rng.randf_range(0.93, 1.04))
	_kick = maxf(_kick, clampf(70.0 / maxf(d, 1.0), 0.03, 0.7) * (1.8 if heavy else 1.0))
	_dust(at, heavy)


## 足の裏（52 × 34 m）のまわりから、横へ広がって上がる大きな砂ぼこり
func _dust(at: Vector3, heavy: bool) -> void:
	if main.fx == null or main.fx.vfx == null:
		return
	var vfx: Vfx = main.fx.vfx
	var col: Color = DUST.get(_mood(), DUST.day)
	var n := 18 if heavy else 14
	var big := 1.3 if heavy else 1.0
	for i in n:
		var a := TAU * float(i) / n + _rng.randf_range(-0.18, 0.18)
		var dir := Vector3(sin(a), 0.0, cos(a))
		# 足の裏の縁（半分の広さ 17 × 26 m）の少し外から、地面に沿って広がり、ゆっくり上がる
		var p := at + Vector3(dir.x * 18.0, _rng.randf_range(2.0, 5.0), dir.z * 27.0)
		var speed := _rng.randf_range(5.0, 10.0) * big
		var q := vfx.emit(Vfx.DUST, p, dir * speed + Vector3(0, _rng.randf_range(1.0, 2.6), 0), _rng.randf_range(6.0, 9.0) * big,
			_rng.randf_range(9.0, 13.0) * big, _rng.randf_range(34.0, 46.0) * big, Color(col, _rng.randf_range(0.42, 0.58)))
		q.rot = _rng.randf() * TAU
		q.spin = _rng.randf_range(-0.1, 0.1)
		q.drag = 0.45
		q.grav = -0.2
		q.fin = 0.06
		q.fpow = 1.4
		dust_puffs += 1


# ---------------------------------------------------------------- 動力が切れる（fx: ordo_stop）

## 動力が切れる演出：町の灯がちらついて消えていき、オルドの琥珀の灯は暗く（非常灯の明るさに）なり、振り出し中の足が落ちて着いて体が沈む。
## 0 秒：うなりが下がる音、灯のちらつき。0.6 秒：足が止まり始める（OrdoView.cine_stop。足が着くのは約 2.9 秒）。5.5〜9.5 秒：町の灯が順に消える
func _start_stop() -> void:
	var o := ordo()
	if o == null:
		return
	_stop_t = 0.0
	_stop_started = false
	main.audio.play_gain("ordo_powerdown", 2.0, 1.0)


func _update_stop(dt: float) -> void:
	if _stop_t < 0.0:
		return
	var o := ordo()
	if o == null:
		_stop_t = -1.0
		return
	_stop_t += dt
	var t := _stop_t
	if t >= 0.6 and not _stop_started:
		_stop_started = true
		o.cine_stop()
	var tl := o.town_lights
	if tl != null:
		tl.flicker = clampf(t / 1.5, 0.0, 1.0) * 0.7
		tl.out = smoothstep(5.5, 9.5, t)
		tl.power = LIGHT_POWER.get(_mood(), 1.0) * (1.0 - 0.4 * smoothstep(8.0, 10.0, t))
		tl.apply()
	# 琥珀の灯（体の帯・梁の灯）：1/12 秒ごとにちらついてから、非常灯の明るさ（0.3）へ
	var k := 1.0
	if t < 4.0:
		var n := fposmod(sin(floor(t * 12.0) * 12.9898) * 43758.5453, 1.0)
		k = 0.2 if n < clampf(t / 1.5, 0.0, 1.0) * 0.5 else 1.0
	else:
		k = lerpf(1.0, 0.3, smoothstep(4.0, 5.5, t))
	o.set_amber(k)


# ---------------------------------------------------------------- 風

func _set_wind(on: bool, db := WIND_DB) -> void:
	if main.audio == null:
		return
	if on:
		main.audio.set_ambience("amb_wind", db, 2.0)
	elif _wind:
		main.audio.set_ambience("", 0.0, 1.2)
	_wind = on
