## haru_bs.glb を Godot で読む確かめ（godot-export の "Test import once"）。ゲームの PlayerView.load_model をそのまま通し、
## 骨・動作・ゲームが探す物・材質・表情・フレームの段・揺れ・足の接地・練習銃を出力する。
##   flock -o /tmp/godot.lock .tools/godot/godot --headless --path godot --script "$PWD/tools/blender/trial_bs/godot_check.gd"
extends SceneTree

func _init() -> void:
	var path := "res://assets/models/haru_bs.glb"
	var pv := PlayerView.new()
	root.add_child(pv)
	pv.load_model(path)
	print("AnimationPlayer: ", pv.anim != null, "  Skeleton3D: ", pv.skeleton != null)
	print("bones: ", pv.skeleton.get_bone_count())
	var names := []
	for i in pv.skeleton.get_bone_count():
		names.append(pv.skeleton.get_bone_name(i))
	print("bone names: ", names)
	var clips := []
	for n in pv.anim.get_animation_list():
		var a := pv.anim.get_animation(n)
		clips.append("%s %.4f %s tracks %d" % [n, a.length, "loop" if a.loop_mode != Animation.LOOP_NONE else "once", a.get_track_count()])
	print("clips: ", clips.size())
	for c in clips:
		print("  ", c)
	print("LightBlade: ", pv.blade, " visible ", pv.blade.visible if pv.blade else null, " parent ", pv.blade.get_parent().get_class() if pv.blade else null)
	print("muzzle: ", pv.muzzle != null, "  frame nodes: ", pv.frame_nodes.keys())
	print("face mats: ", pv.face_mats.size(), "  spark surfaces: ", pv._spark_surfaces.size(), "  body mats: ", pv.body_mats.size())
	print("practice gun: ", pv.practice_gun != null, "  sway: ", pv.sway != null, " sway bones ", pv.sway.bones.size() if pv.sway else 0)
	print("foot_ik: ", pv.foot_ik != null, "  pose: ", pv.pose != null)
	var mats := {}
	var surf := 0
	for mi in pv.meshes:
		for s in mi.mesh.get_surface_count():
			surf += 1
			var m: BaseMaterial3D = mi.get_surface_override_material(s)
			mats[m.resource_name] = "transparency %d" % m.transparency
	print("mesh instances (no blade): ", pv.meshes.size(), "  surfaces: ", surf, "  materials: ", mats)
	# 表情の切り替え・フレームの段・練習銃
	pv.set_expression(1)
	print("face uv1_offset after smile: ", pv.face_mats[0].uv1_offset if pv.face_mats.size() else null)
	pv.set_frame_parts(true, false, false)
	for k in pv.frame_nodes:
		print("frame ", k, " visible ", pv.frame_nodes[k].visible)
	# 動作を流して骨の向き（局所の回転）が変わるか
	var run := pv.anim.get_animation("run")
	var paths := []
	for t in run.get_track_count():
		paths.append(str(run.track_get_path(t)).get_slice(":", 1) + "/" + str(run.track_get_type(t)))
	print("run tracks: ", paths)
	for clip in ["idle", "run", "combo1", "dead"]:
		pv.anim.play(clip)
		pv.anim.seek(pv.anim.get_animation(clip).length * 0.5, true)
		pv.anim.advance(0.0)
		var nb := pv.skeleton.find_bone("neck")
		var ub := pv.skeleton.find_bone("upper_arm.L")
		var hb := pv.skeleton.find_bone("hips")
		print("%s mid: neck rot %s  upper_arm.L rot %s  hips pos %s" % [clip, pv.skeleton.get_bone_pose_rotation(nb), pv.skeleton.get_bone_pose_rotation(ub), pv.skeleton.get_bone_pose_position(hb)])
	quit()
