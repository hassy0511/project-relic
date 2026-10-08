class_name RoomGeo
extends RefCounted
## 部屋のデータ（content/areas の rooms）から、仮の灰色の地形（当たり判定用の面と目印）を作る。
## 形の書き方は docs/design/42_コンテンツの書き方.md。単位はメートル、角度は度。
##   { "t": "box",    "pos": [x,y,z], "size": [幅,高さ,奥行き], "yaw": 0 }       pos は底の中心
##   { "t": "ramp",   "pos": [..], "size": [幅,高さ,長さ], "yaw": 0 }           ローカル -Z 側が低く +Z 側が高い斜面
##   { "t": "stairs", "pos": [..], "size": [幅,高さ,長さ], "steps": 6, "yaw": 0 } 同じ向きの階段
##   { "t": "shell",  "pos": [x,y,z], "size": [幅,高さ,奥行き], "thick": 1, "ceiling": true, "openings": [...] }
##       床と四方の壁（と天井）。pos は床の中心、size は内側の寸法。openings：{ "side": "n|s|e|w", "at": 横のずれ,
##       "w": 2.5, "h": 3.5, "y": 0 }。n は +Z、s は -Z、e は +X、w は -X の壁
## どの形にも "tint": "#rrggbb"（見た目の色）を付けられる。
## "cam": false の形は体だけを止める（Phys.PROP。カメラの壁よけ・弾は通す）。返り値の "prop" に分けて入れる

const DEFAULT_TINT := Color(0.62, 0.59, 0.55)


## 返り値：{ faces: [PackedVector3Array...], tints: [Color...], prop: [PackedVector3Array...]（"cam": false の形）,
##   markers: { 名前: { pos, yaw(ラジアン) } } }
static func build(room: Dictionary) -> Dictionary:
	var faces: Array = []
	var tints: Array = []
	var prop: Array = []
	for s in room.get("geometry", []):
		if not s.get("cam", true):
			prop.append_array(_shape(s))
			continue
		var tint := Color(s.tint) if s.has("tint") else DEFAULT_TINT
		for f in _shape(s):
			faces.append(f)
			tints.append(tint)
	var markers := {}
	var mk: Dictionary = room.get("markers", {})
	for k in mk:
		markers[k] = {"pos": v3(mk[k].pos), "yaw": float(mk[k].get("yaw", 0.0)) * U.DEG}
	return {"faces": faces, "tints": tints, "prop": prop, "markers": markers}


## 形 1 つ分の面（箱ごとの PackedVector3Array の配列）。見た目の側（RoomKit）が形ごとに材質を分けるのに使う
static func shape(s: Dictionary) -> Array:
	return _shape(s)


static func v3(a) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))


static func _shape(s: Dictionary) -> Array:
	var pos := v3(s.get("pos", [0, 0, 0]))
	var size := v3(s.get("size", [1, 1, 1]))
	var yaw := float(s.get("yaw", 0.0)) * U.DEG
	match s.get("t", "box"):
		"box":
			return [box(pos + Vector3(0, size.y * 0.5, 0), size, yaw)]
		"ramp":
			return [ramp(pos, size, yaw)]
		"stairs":
			var out := []
			var n := maxi(1, int(s.get("steps", 6)))
			var basis := Basis(Vector3.UP, yaw)
			for i in n:
				var h := size.y * (i + 1) / n
				var z := -size.z * 0.5 + size.z * (i + 0.5) / n
				out.append(box(pos + basis * Vector3(0, h * 0.5, z), Vector3(size.x, h, size.z / n), yaw))
			return out
		"shell":
			return _shell(pos, size, s)
		_:
			push_error("知らない形: %s" % s.get("t"))
			return []


static func box(center: Vector3, size: Vector3, yaw: float = 0.0) -> PackedVector3Array:
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


## 斜面（くさび形の立体）。pos は低い側の底の中心ではなく、底の中心
static func ramp(pos: Vector3, size: Vector3, yaw: float) -> PackedVector3Array:
	var basis := Basis(Vector3.UP, yaw)
	var hw := size.x * 0.5
	var hl := size.z * 0.5
	# 底の 4 点（0〜3）と高い側の上の 2 点（4・5）。ローカル座標
	var p := [
		Vector3(-hw, 0, -hl), Vector3(hw, 0, -hl), Vector3(hw, 0, hl), Vector3(-hw, 0, hl),
		Vector3(-hw, size.y, hl), Vector3(hw, size.y, hl),
	]
	for i in p.size():
		p[i] = pos + basis * p[i]
	var tris := [
		[0, 1, 2], [0, 2, 3],          # 底
		[3, 2, 5], [3, 5, 4],          # 後ろの壁
		[0, 4, 5], [0, 5, 1],          # 斜面
		[0, 3, 4],                      # 左の側面
		[1, 5, 2],                      # 右の側面
	]
	var out := PackedVector3Array()
	for t in tris:
		out.append_array([p[t[0]], p[t[1]], p[t[2]]])
	return out


static func _shell(pos: Vector3, size: Vector3, s: Dictionary) -> Array:
	var t := float(s.get("thick", 1.0))
	var out := []
	# 床（上面が pos.y）
	out.append(box(pos + Vector3(0, -t * 0.5, 0), Vector3(size.x + 2 * t, t, size.z + 2 * t)))
	if s.get("ceiling", false):
		out.append(box(pos + Vector3(0, size.y + t * 0.5, 0), Vector3(size.x + 2 * t, t, size.z + 2 * t)))
	var ops: Array = s.get("openings", [])
	for side in ["n", "s", "e", "w"]:
		var along: float = size.x if side in ["n", "s"] else size.z
		var depth: float = size.z if side in ["n", "s"] else size.x
		var ext := along + (2 * t if side in ["n", "s"] else 0.0)
		var mine := ops.filter(func(o): return o.side == side)
		mine.sort_custom(func(a, b): return float(a.get("at", 0)) < float(b.get("at", 0)))
		# 壁を「開口で切った縦の区間」に分ける
		var cur := -ext * 0.5
		for o in mine:
			var w := float(o.get("w", 2.5))
			var a0 := float(o.get("at", 0.0)) - w * 0.5
			var a1 := a0 + w
			if a0 > cur:
				out.append(_wall_box(pos, size, side, t, depth, cur, a0, 0.0, size.y))
			var oy := float(o.get("y", 0.0))
			var oh := float(o.get("h", 3.5))
			if oy > 0.0:
				out.append(_wall_box(pos, size, side, t, depth, a0, a1, 0.0, oy))
			if oy + oh < size.y:
				out.append(_wall_box(pos, size, side, t, depth, a0, a1, oy + oh, size.y))
			cur = a1
		if cur < ext * 0.5:
			out.append(_wall_box(pos, size, side, t, depth, cur, ext * 0.5, 0.0, size.y))
	return out


## 壁の一部（壁に沿った座標 a0〜a1、高さ y0〜y1）の箱
static func _wall_box(pos: Vector3, _size: Vector3, side: String, t: float, depth: float, a0: float, a1: float, y0: float, y1: float) -> PackedVector3Array:
	var mid := (a0 + a1) * 0.5
	var len := a1 - a0
	var off := depth * 0.5 + t * 0.5
	var cy := pos.y + (y0 + y1) * 0.5
	var h := y1 - y0
	match side:
		"n":
			return box(Vector3(pos.x + mid, cy, pos.z + off), Vector3(len, h, t))
		"s":
			return box(Vector3(pos.x + mid, cy, pos.z - off), Vector3(len, h, t))
		"e":
			return box(Vector3(pos.x + off, cy, pos.z + mid), Vector3(t, h, len))
		_:
			return box(Vector3(pos.x - off, cy, pos.z + mid), Vector3(t, h, len))
