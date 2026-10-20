extends SceneTree
## ハル（haru_r）の髪・ポーチの揺れ（HaruSway）が描画の速さに左右されないことの確かめ。同じ入力（待機 → 走る → 止まる → 跳ぶ →
## 着地 → ダッシュ）を物理の刻みごとに進め、刻みごとの揺れの角度の最大（度）と、終わりの骨の向きを出す。描画の速さだけを変えて
## 3 回動かし、tools/blender/recon/sway_fps_compare.py で 60 と比べる（W1_ハル再構築の結果.md 8.5）：
##   .tools/godot/godot --headless --path godot --fixed-fps <30|60|144> --script /abs/tools/blender/recon/godot_sway_fps.gd > <フォルダ>/fps_<N>.log
##   python3 tools/blender/recon/sway_fps_compare.py <フォルダ>
## 出力：SWAY（刻み 100〜283 の揺れの最大、度）・DIRS（終わりの各骨の向き）

## 入力の並び：[刻み数, 入力]
const SEQ := [[60, {}], [50, {"move_y": 1.0}], [40, {}], [20, {"jump": true}], [60, {}], [4, {"dash": true}], [50, {}]]
const FROM_TICK := 100


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var h := TestHelpers.new(self)
	var g := h.make_game({})
	await h.settle()
	var pv := PlayerView.new()
	root.add_child(pv)
	pv.load_model("res://assets/models/haru_r.glb")
	var out := []
	var tick := 0
	for st in SEQ:
		for i in int(st[0]):
			await physics_frame
			g.step(InputFrame.of(st[1]))
			pv.sync(g.player, g, 1.0 / 60.0, Vector3.FORWARD)
			tick += 1
			out.append("%.2f" % rad_to_deg(pv.sway.last_max))
	var dirs := []
	for d in pv.sway._d:
		dirs.append("%.4f,%.4f,%.4f" % [d.x, d.y, d.z])
	print("ticks=", tick, " frames=", Engine.get_process_frames())
	print("SWAY ", " ".join(out.slice(FROM_TICK)))
	print("DIRS ", " ".join(dirs))
	quit()
