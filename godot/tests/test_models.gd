extends RefCounted
## 人物の GLB の床の接地（tools/blender/recon/glb_audit.py の、骨で見る軽い版。CI は Python なしでこれを走らせる）。
##   tools/godot.sh test test_models
## 人物の GLB ごとに、AnimationPlayer で全部の動作を 60 こま/秒で標本し、Skeleton3D の骨の位置と、骨に付けた目印の点の
## 高さ（モデルの座標。床は y=0）を見る。目印の点は、基準の姿勢で 1 本の骨にほぼ固く付いた頂点（重み 0.9 以上）のうち、
## 骨の座標の 14 の向きでいちばん外れた点（骨ごと・材質ごとに最大 14 点）。全部の頂点の皮の変形は glb_audit.py が見る。
## 決まり：足は床の 1.5 cm 下まで、ほかの骨（腰・胸・頭・手・髪）と持ち物は 1 cm 下まで。立つ動作（idle・walk・cower）で
## 両足とも 2 cm より上は浮き。地上でだけ出す動作（TOUCH）で、動作の間ずっと足が 2 cm より上も浮き（touch）。
## 今わかっている失敗は KNOWN に深さ（cm）とともに書く：1 cm より深くなったら失敗、
## 直ったのに KNOWN に残っていても失敗（消す）。人物でない GLB は NOT_CHARACTERS に書く（新しい人物の入れ忘れを防ぐ）。

var h: TestHelpers

const DIR := "res://assets/models/"
const NOT_CHARACTERS := ["banki_charger", "banki_floater", "banki_mini", "banki_sentry", "banki_shield", "kannuki", "nagomi",
	"ordo", "practice_gun"]
const FPS := 60.0
const LIMIT := {"feet": -0.015, "body": -0.010, "held": -0.010}
const FLOAT_MIN := 0.020
const WORSE_TOL := 1.0   # cm。KNOWN より 1 cm 深くなったら失敗
const GROUNDED := ["idle", "walk", "cower"]
## 地上でだけ出し、跳ぶこまの無い動作（glb_audit.py の TOUCH と同じ）：動作の間の足の最も低い点が FLOAT_MIN 以下であること
const TOUCH := ["dash", "lunge", "charge", "drill", "combo1", "combo2", "combo3"]
const HELD_WORDS := ["gun", "blade", "weapon", "staff", "cane", "hammer", "sword"]
const GROUPS := ["feet", "body", "held"]

## 今わかっている失敗：「モデル/動作/組」→ 床の下の深さ（cm。float は両足の浮きの高さ）。この試験の骨と目印の点で測った値。
## 組は feet（足）・body（足と持ち物の外の体）・held（持ち物）・float（立つ動作で両足とも浮く）・
## touch（地上の動作で足がずっと浮く。値は浮きの高さ）。
## 後ろの注は glb_audit.py（全部の頂点・皮の変形）で測った値と、こま（60 こま/秒）。直したら消す。
## 残してよい訳は、モデルの組ごとに 1 行で書く（W1_ハル再構築の結果.md 10.3）。
## glb_audit.py だけが見つけるもの（目印の点では 1.5 cm に届かない・骨の子の硬い物体・光刃・dead の最後のこまの胴）：
## yana/charge・combo1〜3 の足 1.6 cm、haru_bs/dead の銃（骨の子の物体）13.5 cm と光刃（長押しの 0.6 倍）16.7 cm、haru_a/dead の光刃 12.1 cm、
## dead の最後のこまで胴が床から浮く burton 12.7・haru_a 10.5・haru_bs 4.0・haru_proxy 20.5 cm。
const KNOWN := {
	# burton・yana：NPC。ゲームでは idle だけを出す（props_view.gd の _npc_anim_for）。直すときは
	# rebake_anims.py --model godot/assets/models/<名前>.glb で標準の動作を焼き直す（dead・jump・fall・hurt・dash・lunge は
	# 直った定義になる）。air・drill・charge・combo1〜3 は別に直す
	"burton/air/feet": 5.7,      # glb_audit 5.7 cm（foot.R・こま 0）
	"burton/dead/feet": 48.2,    # glb_audit 48.2 cm（foot.R・こま 38）
	"burton/dead/body": 25.3,    # glb_audit 29.4 cm（legs・こま 38）
	"burton/drill/feet": 1.8,    # glb_audit 1.9 cm（foot.R・こま 0）
	"burton/fall/feet": 5.1,     # glb_audit 5.3 cm（foot.L・こま 0）
	"burton/hurt/feet": 4.0,     # glb_audit 4.4 cm（foot.L・こま 0）
	"burton/jump/feet": 7.2,     # glb_audit 7.4 cm（foot.R・こま 0）
	"burton/dash/touch": 5.3,    # 浮き。glb_audit 4.9 cm（こま 0）
	"burton/lunge/touch": 7.3,   # 浮き。glb_audit 6.9 cm（こま 0）
	# haru_a・haru_proxy：前の版のハル。F2（main.gd の toggle_haru。haru_a だけ）か --haru=a・--haru=proxy でだけ出る。直さない
	"haru_a/dead/feet": 30.3,    # glb_audit 30.3 cm（foot.R・こま 33）
	"haru_a/dead/body": 17.9,    # glb_audit 17.9 cm（hands・こま 38）
	"haru_a/jump/feet": 2.1,     # glb_audit 2.1 cm（foot.R・こま 0）
	"haru_a/charge/touch": 3.6,  # 浮き。glb_audit 3.5 cm（こま 0）
	"haru_a/combo1/touch": 3.6,  # 浮き。glb_audit 3.5 cm（こま 0）
	"haru_a/combo2/touch": 3.6,  # 浮き。glb_audit 3.5 cm（こま 0）
	"haru_a/combo3/touch": 3.6,  # 浮き。glb_audit 3.5 cm（こま 0）
	"haru_a/dash/touch": 9.0,    # 浮き。glb_audit 9.0 cm（こま 0）
	"haru_a/lunge/touch": 9.9,   # 浮き。glb_audit 9.7 cm（こま 11）
	# haru_bs：外の技能の試作（--haru=bs でだけ出る）。直さない
	"haru_bs/combo1/feet": 3.3,  # glb_audit 3.3 cm（foot.R・こま 5）
	"haru_bs/combo2/feet": 3.3,  # glb_audit 3.3 cm（foot.R・こま 0）
	"haru_bs/combo3/feet": 4.0,  # glb_audit 4.0 cm（foot.R・こま 8）
	"haru_bs/dead/feet": 3.5,    # glb_audit 3.3 cm（foot.L・こま 4）
	"haru_bs/dead/body": 10.1,   # glb_audit 10.1 cm（hands・こま 28）
	"haru_bs/fall/feet": 7.0,    # glb_audit 7.0 cm（foot.R・こま 0）
	"haru_bs/hurt/feet": 3.3,    # glb_audit 3.3 cm（foot.L・こま 3）
	"haru_bs/jump/feet": 9.3,    # glb_audit 9.3 cm（foot.L・こま 0）
	"haru_bs/lunge/feet": 5.0,   # glb_audit 5.0 cm（foot.R・こま 15）
	"haru_bs/run/feet": 6.0,     # glb_audit 6.0 cm（foot.L・こま 5）
	"haru_proxy/dead/feet": 25.7,  # glb_audit 25.7 cm（foot.R・こま 28）
	"haru_proxy/dead/body": 13.7,  # glb_audit 13.7 cm（legs・こま 28）
	"haru_proxy/charge/touch": 4.3,  # 浮き。glb_audit 4.3 cm（こま 0）
	"haru_proxy/combo1/touch": 4.3,  # 浮き。glb_audit 4.3 cm（こま 0）
	"haru_proxy/combo2/touch": 4.3,  # 浮き。glb_audit 4.3 cm（こま 0）
	"haru_proxy/combo3/touch": 4.3,  # 浮き。glb_audit 4.3 cm（こま 0）
	"haru_proxy/dash/touch": 10.8,   # 浮き。glb_audit 10.8 cm（こま 0）
	"haru_proxy/drill/touch": 2.4,   # 浮き。glb_audit 2.4 cm（こま 0）
	"haru_proxy/lunge/touch": 12.1,  # 浮き。glb_audit 12.1 cm（こま 0）
	# yana：burton と同じ（上）
	"yana/air/feet": 6.4,        # glb_audit 6.4 cm（foot.R・こま 0）
	"yana/dead/feet": 49.8,      # glb_audit 49.8 cm（foot.R・こま 38）
	"yana/dead/body": 30.6,      # glb_audit 32.3 cm（legs・こま 38）
	"yana/drill/feet": 2.0,      # glb_audit 2.2 cm（foot.L・こま 0）
	"yana/fall/feet": 6.1,       # glb_audit 6.4 cm（foot.L・こま 0）
	"yana/hurt/feet": 4.4,       # glb_audit 4.8 cm（foot.L・こま 0）
	"yana/jump/feet": 6.7,       # glb_audit 6.8 cm（foot.R・こま 0）
	"yana/lunge/touch": 2.8,     # 浮き。glb_audit 2.5 cm（こま 0）
}


func _init(helpers: TestHelpers) -> void:
	h = helpers


static func _dirs() -> PackedVector3Array:
	var d := PackedVector3Array()
	for v in [Vector3.RIGHT, Vector3.LEFT, Vector3.UP, Vector3.DOWN, Vector3.FORWARD, Vector3.BACK]:
		d.append(v)
	for i in 8:
		d.append(Vector3(1 if i & 1 else -1, 1 if i & 2 else -1, 1 if i & 4 else -1).normalized())
	return d


static func _group_of_bone(bone: String) -> String:
	var n := bone.to_lower()
	return "feet" if n.contains("foot") or n.contains("toe") else "body"


## 人物の GLB の名前（拡張子なし）。NOT_CHARACTERS の外のすべて
static func _characters() -> PackedStringArray:
	var out := PackedStringArray()
	for f in DirAccess.get_files_at(DIR):
		if f.get_extension() == "glb" and not NOT_CHARACTERS.has(f.get_basename()):
			out.append(f.get_basename())
	return out


## 目印の点：{bone: PackedInt32Array, local: PackedVector3Array, group: PackedInt32Array}（骨の原点も入れる。root は除く）
func _probes(root: Node, skel: Skeleton3D) -> Dictionary:
	var bone := PackedInt32Array()
	var local := PackedVector3Array()
	var group := PackedInt32Array()
	for b in skel.get_bone_count():
		if skel.get_bone_name(b) != "root":
			bone.append(b)
			local.append(Vector3.ZERO)
			group.append(GROUPS.find(_group_of_bone(skel.get_bone_name(b))))
	var dirs := _dirs()
	for mi: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		if mi.skin == null or mi.mesh == null:
			continue
		var skin := mi.skin
		var bind_bone := PackedInt32Array()
		var bind_pose: Array[Transform3D] = []
		for i in skin.get_bind_count():
			var b := skin.get_bind_bone(i)
			bind_bone.append(b if b >= 0 else skel.find_bone(skin.get_bind_name(i)))
			bind_pose.append(skin.get_bind_pose(i))
		for s in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(s)
			var mname := (mat.resource_name if mat else "").to_lower()
			var held := HELD_WORDS.any(func(w): return mname.contains(w))
			var arr := mi.mesh.surface_get_arrays(s)
			var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
			var bones: PackedInt32Array = arr[Mesh.ARRAY_BONES]
			var weights: PackedFloat32Array = arr[Mesh.ARRAY_WEIGHTS]
			var per := bones.size() / maxi(1, verts.size())
			var nd := dirs.size()
			var scores := PackedFloat32Array()   # （バインドの番号 × 14 の向き）の値と点
			scores.resize(bind_bone.size() * nd)
			scores.fill(-INF)
			var pts := PackedVector3Array()
			pts.resize(bind_bone.size() * nd)
			for v in verts.size():
				var bw := 0.0
				var bi := -1
				for k in per:
					if weights[v * per + k] > bw:
						bw = weights[v * per + k]
						bi = bones[v * per + k]
				if bw < 0.9:
					continue
				var p: Vector3 = bind_pose[bi] * verts[v]
				for d in nd:
					var x := p.dot(dirs[d])
					if x > scores[bi * nd + d]:
						scores[bi * nd + d] = x
						pts[bi * nd + d] = p
			for bi in bind_bone.size():
				var seen := {}
				for d in nd:
					var p := pts[bi * nd + d]
					if scores[bi * nd + d] == -INF or seen.has(p):
						continue
					seen[p] = true
					bone.append(bind_bone[bi])
					local.append(p)
					group.append(GROUPS.find("held") if held else GROUPS.find(_group_of_bone(skel.get_bone_name(bind_bone[bi]))))
	return {"bone": bone, "local": local, "group": group}


## 1 体の測り：「動作/組」→ 最も低い高さ（m）とこま、立つ動作の両足の最も高い高さ
func _measure(name: String) -> Dictionary:
	var root: Node3D = (load(DIR + name + ".glb") as PackedScene).instantiate()
	h.tree.root.add_child(root)
	var anim: AnimationPlayer = root.find_child("AnimationPlayer", true, false)
	var skels := root.find_children("*", "Skeleton3D", true, false)
	h.expect(anim != null and skels.size() == 1, "%s: AnimationPlayer と Skeleton3D が 1 つずつある" % name)
	if anim == null or skels.size() != 1:
		root.queue_free()
		return {}
	var skel: Skeleton3D = skels[0]
	var pr := _probes(root, skel)
	var bone: PackedInt32Array = pr.bone
	var local: PackedVector3Array = pr.local
	var group: PackedInt32Array = pr.group
	var to_model: Transform3D = root.global_transform.affine_inverse() * skel.global_transform
	var out := {}
	var poses: Array[Transform3D] = []
	poses.resize(skel.get_bone_count())
	for clip in anim.get_animation_list():
		if clip == "RESET":
			continue
		var a := anim.get_animation(clip)
		anim.play(clip, 0.0)
		var low := [INF, INF, INF]
		var at := [0, 0, 0]
		var feet_high := -INF
		var feet_high_at := 0
		var n := int(round(a.length * FPS))
		for f in n + 1:
			anim.seek(minf(f / FPS, a.length), true)
			for b in skel.get_bone_count():
				poses[b] = to_model * skel.get_bone_global_pose(b)
			var fl := [INF, INF, INF]
			for i in bone.size():
				var y := (poses[bone[i]] * local[i]).y
				if y < fl[group[i]]:
					fl[group[i]] = y
			for g in 3:
				if fl[g] < low[g]:
					low[g] = fl[g]
					at[g] = f
			if fl[0] > feet_high:
				feet_high = fl[0]
				feet_high_at = f
		for g in 3:
			if low[g] < INF:
				out["%s/%s" % [clip, GROUPS[g]]] = [low[g], at[g]]
		if GROUNDED.has(clip):
			out["%s/float" % clip] = [feet_high, feet_high_at]
		if TOUCH.has(clip) and low[0] < INF:
			out["%s/touch" % clip] = [low[0], at[0]]
	root.queue_free()
	return out


func test_models_floor_contact() -> void:
	var names := _characters()
	h.expect(names.has("haru_r") and names.size() >= 18, "人物の GLB が見つかる（%d 体）" % names.size())
	var found := {}
	var lines := PackedStringArray()
	for name in names:
		var m := _measure(name)
		for k: String in m:
			var key := "%s/%s" % [name, k]
			var y: float = m[k][0]
			var frame: int = m[k][1]
			var grp := k.get_slice("/", 1)
			var up := grp == "float" or grp == "touch"
			var bad: bool = y > FLOAT_MIN if up else y < float(LIMIT[grp])
			var cm := (y if up else -y) * 100.0
			if bad:
				found[key] = true
				lines.append("\"%s\": %.1f,   # こま %d" % [key, cm, frame])
				if KNOWN.has(key):
					h.expect(cm <= KNOWN[key] + WORSE_TOL, "%s が悪くなった：%.1f cm（KNOWN は %.1f cm、こま %d）" % [key, cm, KNOWN[key], frame])
				else:
					h.expect(false, "%s が床の決まりの外：%.1f cm（こま %d）。直すか、KNOWN に足す" % [key, cm, frame])
	var same := found.size() == KNOWN.size()
	for key: String in KNOWN:
		h.expect(found.has(key), "%s は直った（または無い）。KNOWN から消す" % key)
		same = same and found.has(key)
	if not same:
		print("  測った床の失敗（KNOWN の形）：\n    " + "\n    ".join(lines))
