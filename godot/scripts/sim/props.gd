class_name Props
## 仕掛け：ドリルで壊せる壁、宝箱、住人、セーブビーコン、拾えるもの、トリガー、中継地点


class Breakable:
	var id: String
	var center: Vector3
	var size: Vector3
	var yaw: float
	var broken := false
	## 壊れるまでに必要なドリルの時間（秒）
	var toughness := 1.0
	var progress := 0.0
	var body: StaticBody3D = null

	func _init(i: String, c: Vector3, s: Vector3, y: float) -> void:
		id = i
		center = c
		size = s
		yaw = y

	## 回転を考えた箱との距離（y 軸まわり）
	func distance_to(p: Vector3) -> float:
		var dx := p.x - center.x
		var dz := p.z - center.z
		var c := cos(-yaw)
		var s := sin(-yaw)
		var lx := dx * c + dz * s
		var lz := -dx * s + dz * c
		var ly := p.y - center.y
		var q := Vector3(maxf(absf(lx) - size.x / 2.0, 0.0), maxf(absf(ly) - size.y / 2.0, 0.0), maxf(absf(lz) - size.z / 2.0, 0.0))
		return q.length()


class Chest:
	var id: String
	var pos: Vector3
	var yaw: float
	var contents: Dictionary
	var opened := false
	var range_m := 1.8
	var prompt := "開ける"

	func _init(i: String, p: Vector3, y: float, c: Dictionary) -> void:
		id = i
		pos = p
		yaw = y
		contents = c

	func enabled() -> bool:
		return not opened


class Npc:
	var id: String
	var pos: Vector3
	var yaw: float
	var name: String
	var talk: String
	var range_m := 2.2
	var prompt := "話す"

	func _init(i: String, p: Vector3, y: float, n: String, t: String) -> void:
		id = i
		pos = p
		yaw = y
		name = n
		talk = t

	func enabled() -> bool:
		return true


class Beacon:
	var id: String
	var pos: Vector3
	var range_m := 2.0
	var prompt := "セーブする"
	var activated := false

	func _init(i: String, p: Vector3) -> void:
		id = i
		pos = p

	func enabled() -> bool:
		return true


class Pickup:
	## cells / energy / repair
	var kind: String
	var amount: float
	var pos: Vector3
	var vel := Vector3.ZERO
	var collected := false
	var age := 0.0

	func _init(k: String, a: float, p: Vector3) -> void:
		kind = k
		amount = a
		pos = p


class Trigger:
	var id: String
	var center: Vector3
	var half: Vector3
	var event: String
	var once: bool
	var fired := false

	func _init(i: String, c: Vector3, h: Vector3, e: String, o: bool) -> void:
		id = i
		center = c
		half = h
		event = e
		once = o

	func contains(p: Vector3) -> bool:
		return absf(p.x - center.x) <= half.x and absf(p.y - center.y) <= half.y + 1.0 and absf(p.z - center.z) <= half.z


class Checkpoint:
	var id: String
	var pos: Vector3
	var yaw: float
	var radius: float

	func _init(i: String, p: Vector3, y: float, r: float) -> void:
		id = i
		pos = p
		yaw = y
		radius = r
