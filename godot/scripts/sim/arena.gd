class_name Arena
extends RefCounted
## 試しの部屋：円形の部屋（直径 32 m）に敵やボスを置く。起動引数 --arena=mini|shield|floater|kannuki|all と、ボスのテストが使う。
## 本物のボス部屋（B4 [19]）は 3 段階の B で作る。ここは戦闘の中身を確かめるための仮の舞台。

const KINDS := ["mini", "shield", "floater", "kannuki"]


## 部屋の地形：床と、円の壁（細長い箱を円に並べる）。返り値：{ faces, markers }
static func geometry(radius := 16.0, wall_h := 16.0, segs := 36) -> Dictionary:
	var faces := []
	faces.append(_box(Vector3(0, -0.5, 0), Vector3(radius * 2.4, 1.0, radius * 2.4), 0.0))
	var seg_len := TAU * (radius + 0.5) / segs + 0.4
	for i in segs:
		var a := TAU * i / segs
		var c := Vector3(sin(a) * (radius + 0.5), wall_h * 0.5, cos(a) * (radius + 0.5))
		faces.append(_box(c, Vector3(seg_len, wall_h, 1.0), a))
	var markers := {
		"start": {"pos": Vector3(0, 0, radius - 3.0), "yaw": PI},
		"center": {"pos": Vector3.ZERO, "yaw": 0.0},
	}
	for i in 4:
		var a := PI * 0.25 + PI * 0.5 * i
		markers["pillar_%d" % i] = {"pos": Vector3(sin(a) * 6.5, 0, cos(a) * 6.5), "yaw": a}
	for i in 3:
		var a := PI + (i - 1) * 0.9
		markers["spawn_%d" % i] = {"pos": Vector3(sin(a) * 9.0, 0, cos(a) * 9.0), "yaw": a + PI}
	return {"faces": faces, "markers": markers}


## 置く物：kind が kannuki ならボス（と壊れる柱 4 本）、それ以外ならその型を 3 体
static func placement(kind: String) -> Dictionary:
	var enemies := []
	var props := []
	if kind == "kannuki":
		enemies.append({"type": "kannuki", "at": "center"})
		for i in 4:
			props.append({"id": "pillar_%d" % i, "type": "breakable", "at": "pillar_%d" % i, "size": [1.6, 6.0, 1.6]})
	elif kind == "all":
		enemies = [{"type": "mini", "at": "spawn_0"}, {"type": "shield", "at": "spawn_1"}, {"type": "floater", "at": "spawn_2"}]
	else:
		for i in 3:
			enemies.append({"type": kind, "at": "spawn_%d" % i})
	return {
		"id": "arena", "name": "試しの部屋", "playerStart": "start", "objective": "敵を倒す",
		"enemies": enemies, "props": props, "triggers": [], "checkpoints": [],
	}


static func _box(center: Vector3, size: Vector3, yaw: float) -> PackedVector3Array:
	var h := size * 0.5
	var basis := Basis(Vector3.UP, yaw)
	var c := []
	for i in 8:
		c.append(center + basis * Vector3(h.x if i & 1 else -h.x, h.y if i & 2 else -h.y, h.z if i & 4 else -h.z))
	var quads := [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
	var out := PackedVector3Array()
	for q in quads:
		out.append_array([c[q[0]], c[q[1]], c[q[2]], c[q[0]], c[q[2]], c[q[3]]])
	return out
