extends SceneTree
## 練習銃とスパークを、ゲームの画面（main.tscn）で撮る：スパークを受け取る前（練習銃）と後（スパーク）を、ふだんのカメラと
## 右手の近写で 1 枚ずつ。部屋とフラグはゲームと同じ引数（--room・--flags）で渡す。受け取りはフラグ ch1.got_spark を立てて作る
## （main.gd が次の刻みで PlayerView.sync_gun を呼び、持ち替える）。
##   tools/godot.sh shot --resolution 1600x900 --script /abs/tools/blender/recon/godot_gun_shots.gd -- \
##     <出力のフォルダ> <名前> --room=ch1.training:start --flags=ch1.chores_started,ch1.t_move,trigger.ch1.training.start
## スマホ：--rendering-driver opengl3 --rendering-method gl_compatibility --resolution 844x390、引数に --touch。
## 撃った直後の近写は続く 4 こまを撮る（_aim_close_0〜3。描画と中身の刻みが 1 対 1 でないので、弾の描かれないこまがある。
## --fixed-fps 60 にすると、構えの姿勢が付く前の手の位置にカメラを置いてしまう）。
## 撃った弾の、中身の銃口と見た目の銃口の目印の差を「muzzle gap」として出す（Fx はこの差を弾が 2.5m 進む間に 0 へ減らして描く）
## できるもの：<フォルダ>/<名前>_{practice,spark}_{normal,aim_close_0〜3,close}.png（normal・aim_close は撃ち続けている所）

var out_dir := "user://gun_shots"
var label := "pc"
var main: Node


func _initialize() -> void:
	var pos: Array[String] = []
	for a in OS.get_cmdline_user_args():
		if not a.begins_with("--"):
			pos.append(a)
	if pos.size() > 0:
		out_dir = pos[0]
	if pos.size() > 1:
		label = pos[1]
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await physics_frame


func _save(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_texture().get_image()
	DirAccess.make_dir_recursive_absolute(out_dir)
	img.save_png("%s/%s_%s.png" % [out_dir, label, name])
	print("shot ", name)


## 右手の銃の近写：銃の右側（貸出札の側。ハルの体の外側）の少し上から。aim = true は撃っている間（銃口の先の弾も入れる）
func _close(cam: Camera3D, aim: bool) -> void:
	var pv: PlayerView = main.player_view
	var held: Node3D = pv.practice_gun   # 隠していても、スパークと同じ置き場所で手に付いて動く
	var t := held.global_transform
	var target := t * (Vector3(0.45, 0.03, 0.0) if aim else Vector3(0.08, 0.02, 0.0))
	var eye := t * (Vector3(0.30, 0.20, 1.15) if aim else Vector3(0.16, 0.10, 0.62))
	cam.global_position = eye
	var up := Vector3.UP if absf((target - eye).normalized().dot(Vector3.UP)) < 0.95 else Vector3.FORWARD
	cam.look_at(target, up)
	cam.fov = 40.0
	cam.current = true


## 撃ったばかりの弾（銃口から max_d 以内）が出るまで待つ（銃口から弾が出る所を撮る）
func _wait_fresh_shot(max_d: float) -> void:
	for i in 90:
		for sh in main.game.shots:
			if sh.from_player and sh.alive and sh.pos.distance_to(sh.origin) < max_d:
				# 弾の出た所（中身の銃口）と、見た目の銃口の目印の差を、ハルの向きの右・上・前で出す
				var pv: PlayerView = main.player_view
				var fwd := U.yaw_to_dir(main.game.player.yaw)
				var right := Vector3(-fwd.z, 0.0, fwd.x)
				var dv: Vector3 = sh.origin - pv.muzzle.global_position
				print("muzzle gap (%s): right %.3f up %.3f fwd %.3f (m)" % [pv.gun, dv.dot(right), dv.y, dv.dot(fwd)])
				return
		await _frames(1)


func _run() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	main = scene.instantiate()
	root.add_child(main)
	await _frames(150)
	var pv: PlayerView = main.player_view
	if pv == null or pv.practice_gun == null:
		push_error("練習銃が付いていない")
		quit(1)
		return
	var cam := Camera3D.new()
	main.add_child(cam)
	for state in ["practice", "spark"]:
		if state == "spark":
			main.game.set_flag("ch1.got_spark")
			await _frames(4)
		# 会話を送って閉じる（訓練場の始まりのバートンの台詞）
		for i in 60:
			if main.game.story.blocking():
				main.game.story.confirm()
			await _frames(1)
		main.hud.set_hint("")
		print(state, " gun=", pv.gun)
		# ふだんのカメラ：撃ち続けている所（構えた銃と、銃口から出る弾）
		main.camera.current = true
		main.hud.visible = true
		Input.action_press("fire")
		await _frames(26)
		await _wait_fresh_shot(0.9)
		await _save(state + "_normal")
		main.hud.visible = false
		await _frames(8)
		await _wait_fresh_shot(0.45)
		for k in 4:
			_close(cam, true)
			await _save(state + "_aim_close_%d" % k)
			await _frames(1)
		Input.action_release("fire")
		main.camera.current = true
		await _frames(50)
		_close(cam, false)
		await _frames(2)
		await _save(state + "_close")
	quit(0)
