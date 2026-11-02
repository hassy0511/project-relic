class_name HaruPlayShots
## ハルのモデルの比べ（--haru=r と --haru=bs などで同じ場面を撮って並べる）：Demo（--demo=<フォルダ>）から使う。
##   --haru_play_shots                 全部：ゲームのカメラ（後ろ）で動作、顔の表情 4 つ、フレームの段 4 つ、会話のカメラ、ナゴミ
##   --haru_play_shots=play,face,frame,talk,nagomi   名前で選ぶ
## 出力：<フォルダ>/hp_play_<動作>.png（ゲームのカメラ、画面の表示つき）、hp_face_<0..3>.png（顔の寄り）、
## hp_frame_<段>_<front|back>.png（フレームの段）。会話のカメラ（talk_yana_*）とナゴミ（nd_*）は Demo・NagomiShots の撮り方のまま
## （--talk_cam・--nagomi_cams が無ければ yana、game,close）。
## 動作は決まった入力で起こす（見本の部屋 sample.gym。やられない）。撮る刻みで、動作の名前と時間を表に出す（撮れたのがその動作か確かめる）。
## 被弾だけは、その刻みだけ god_mode を外して 1 の傷を受ける。見た目だけ：ゲームの中身の決まりには手を加えない。
## ナゴミは動作・顔・フレームの絵では隠す（止まるとハルの頭の後ろに来て、後ろの髪を隠すので。ナゴミの絵は別に撮る）

const ROOM := "sample.gym:from_hub"
const AT := Vector3(-8.0, 0.0, 6.0)
const LOOK := Vector3(10.0, 0.0, 6.0)
## ハルの見た目の座標（+Z が正面、+X がハルの左）のカメラ：[目, 見る所, 画角]
const FACE_CAM := [Vector3(-0.28, 1.38, 0.98), Vector3(0.0, 1.33, 0.0), 26.0]
const FRAME_CAMS := {
	"front": [Vector3(1.55, 1.15, 2.3), Vector3(0.0, 0.8, 0.0), 40.0],
	"back": [Vector3(-1.3, 1.25, -2.4), Vector3(0.0, 0.85, 0.0), 40.0],
}
## フレームの段：[名前, core, arm, legs]（20_ゲームシステム設計.md 2.1 の順：作業着 → 封印室で胴 → 籠手 → 脚）
const FRAME_STAGES := [["0_none", false, false, false], ["1_core", true, false, false], ["2_arm", true, true, false], ["3_legs", true, true, true]]

static var _cam: Camera3D = null


static func steps(d) -> Array:
	var m = d.main
	var want := String(m.args.get("haru_play_shots", "1"))
	var on := func(n: String) -> bool: return want == "1" or want.split(",").has(n)
	var s := []
	if on.call("play"):
		s.append_array(_play_steps(d))
	if on.call("face"):
		s.append_array(_face_steps(d))
	if on.call("frame"):
		s.append_array(_frame_steps(d))
	if on.call("talk"):
		if not m.args.has("talk_cam"):
			m.args["talk_cam"] = "yana"
		s.append({"ticks": 2, "setup": func(): _release(d)})
		s.append_array(d._talk_cam_steps())
	if on.call("nagomi"):
		if not m.args.has("nagomi_cams"):
			m.args["nagomi_cams"] = "game,close"
		s.append({"ticks": 2, "setup": func(): _release(d)})
		s.append_array(NagomiShots.steps(d))
	return s


## 置き直す：見本の部屋の決まった所に、待機で立たせる（前の動作を消す）
static func _reset(d, keep_hidden := true) -> Dictionary:
	return {"ticks": 2, "setup": func():
		var m = d.main
		var g: GameSim = m.game
		g.god_mode = true
		var parts := ROOM.split(":")
		if g.room_id != parts[0]:
			g.load_room(parts[0], parts[1])
		for t in g.triggers:
			t.fired = true
		g.player.attack = null
		g.player.hurt_time = 0.0
		g.player.invuln = 0.0
		g.player.sword_hold = 0.0
		d._stand(AT, LOOK)
		_hide_nagomi(d, keep_hidden)
		HaruMotionShots._warm_render()}


## 撮る刻み：動作の名前と、攻撃なら攻撃の中の時間を表に出す
static func _shot(d, name: String, inp: Dictionary, expect: String) -> Dictionary:
	return {"ticks": 1, "shot": "hp_play_%s" % name, "input": inp, "check": func():
		var p: Player = d.main.game.player
		var a := p.anim()
		var t := ("　攻撃の %.3f / %.3f 秒" % [p.attack.time, p.attack.duration]) if p.attack != null else ""
		print("ハルの動作 %s：%s%s　動作の再生 %s %.3f 秒" % [name, a, t, d.main.player_view.current,
			d.main.player_view.anim.current_animation_position if d.main.player_view.anim and d.main.player_view.anim.is_playing() else -1.0])
		return d._check(a == expect, "ハルの比べ %s：動作 %s（%s）" % [name, expect, a])}


static func _play_steps(d) -> Array:
	var s := []
	# 待機
	s.append(_reset(d))
	s.append({"ticks": 120, "input": {}})
	s.append(_shot(d, "idle", {}, "idle"))
	# 走る（前へ倒し続ける）
	s.append(_reset(d))
	s.append({"ticks": 30, "input": {}})
	s.append({"ticks": 44, "input": {"move_y": 1.0}})
	s.append(_shot(d, "run", {"move_y": 1.0}, "run"))
	# 跳ぶ（上がっている間）
	s.append(_reset(d))
	s.append({"ticks": 30, "input": {}})
	s.append({"ticks": 12, "input": {"jump": true}})
	s.append(_shot(d, "jump", {"jump": true}, "jump"))
	s.append({"ticks": 70, "input": {}})
	# ダッシュ（0.22 秒の 5 刻み目）
	s.append(_reset(d))
	s.append({"ticks": 30, "input": {}})
	s.append({"ticks": 1, "input": {"dash": true}})
	s.append({"ticks": 4, "input": {}})
	s.append(_shot(d, "dash", {}, "dash"))
	s.append({"ticks": 40, "input": {}})
	# 3 連の斬り：押して、次の斬りを先に押しておく（inputBuffer）。それぞれ振り抜き（25%）の少しあと
	s.append(_reset(d))
	s.append({"ticks": 30, "input": {}})
	s.append({"ticks": 1, "input": {"sword": true}})
	s.append({"ticks": 5, "input": {}})
	s.append(_shot(d, "combo1", {}, "combo1"))
	s.append({"ticks": 3, "input": {}})
	s.append({"ticks": 1, "input": {"sword": true}})
	# combo1（17 刻み）が終わると combo2。combo2 の 7 刻み目
	s.append({"ticks": 14, "input": {}})
	s.append(_shot(d, "combo2", {}, "combo2"))
	s.append({"ticks": 2, "input": {}})
	s.append({"ticks": 1, "input": {"sword": true}})
	# combo2（18 刻み）が終わると combo3。combo3 の 10 刻み目
	s.append({"ticks": 16, "input": {}})
	s.append(_shot(d, "combo3", {}, "combo3"))
	s.append({"ticks": 50, "input": {}})
	# 溜め斬り：長押し（0.7 秒）の間は刃が短い。離して溜め斬りの 10 刻み目
	s.append(_reset(d))
	s.append({"ticks": 30, "input": {}})
	s.append({"ticks": 36, "input": {"sword": true}})
	s.append(_shot(d, "charge_hold", {"sword": true}, "idle"))
	s.append({"ticks": 12, "input": {"sword": true}})
	s.append({"ticks": 9, "input": {}})
	s.append(_shot(d, "charge", {}, "charge"))
	s.append({"ticks": 50, "input": {}})
	# 被弾：前から 1 の傷（軽い）。痛みの顔。4 刻み目
	s.append(_reset(d))
	s.append({"ticks": 30, "input": {}})
	s.append({"ticks": 1, "input": {}, "setup": func():
		var g: GameSim = d.main.game
		g.god_mode = false
		var p: Player = g.player
		p.take_damage(1.0, p.pos + U.yaw_to_dir(p.yaw) * 2.0, false)
		g.god_mode = true})
	s.append({"ticks": 3, "input": {}})
	s.append(_shot(d, "hurt", {}, "hurt"))
	s.append({"ticks": 40, "input": {}, "setup": func(): d.main.game.player.hp = d.main.game.player.max_hp})
	return s


## 顔の寄り：会話の間のように立ったまま、4 つの表情（PlayerView.set_expression）を顔の前の近いカメラで撮る
static func _face_steps(d) -> Array:
	var s := [_reset(d), {"ticks": 90, "input": {}}]
	for i in 4:
		s.append({"ticks": 1, "shot": "hp_face_%d" % i, "input": {}, "cam": func():
			_use_cam(d, FACE_CAM)
			d.main.player_view.set_expression(i)})
	s.append({"ticks": 2, "setup": func(): _release(d)})
	return s


## フレームの段：PlayerView.set_frame_parts を撮る間だけ段に合わせる（ゲームの中身は全部付いたまま）
static func _frame_steps(d) -> Array:
	var s := [_reset(d), {"ticks": 90, "input": {}}]
	for st in FRAME_STAGES:
		for view in ["front", "back"]:
			s.append({"ticks": 1, "shot": "hp_frame_%s_%s" % [st[0], view], "input": {}, "cam": func():
				_use_cam(d, FRAME_CAMS[view])
				d.main.player_view.set_frame_parts(st[1], st[2], st[3])})
	s.append({"ticks": 2, "setup": func(): _release(d)})
	return s


static func _hide_nagomi(d, hide: bool) -> void:
	var nv: NagomiView = d.main.nagomi_view
	if nv == null:
		return
	if nv.model != null:
		nv.model.visible = not hide
	if nv.glow != null:
		nv.glow.visible = not hide


## ハルの見た目の子のカメラ（画面の表示・スマホの操作を隠す）
static func _use_cam(d, c: Array) -> void:
	var m = d.main
	if _cam == null or not is_instance_valid(_cam):
		_cam = Camera3D.new()
		m.player_view.add_child(_cam)
	_cam.fov = float(c[2])
	var eye: Vector3 = c[0]
	var at: Vector3 = c[1]
	_cam.transform = Transform3D(Basis.looking_at(at - eye, Vector3.UP), eye)
	_cam.current = true
	for l in [m.hud, m.touch]:
		if l != null and is_instance_valid(l):
			l.visible = false


static func _release(d) -> void:
	var m = d.main
	if _cam != null and is_instance_valid(_cam):
		_cam.queue_free()
	_cam = null
	m.camera.current = true
	for l in [m.hud, m.touch]:
		if l != null and is_instance_valid(l):
			l.visible = true
	_hide_nagomi(d, false)
