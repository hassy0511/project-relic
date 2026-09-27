class_name U
## 数学の小道具。向き（yaw）は +Z を 0、+X を 90 度とする（three.js 版と同じ）。

const DEG := PI / 180.0


static func wrap_angle(a: float) -> float:
	a = fmod(a + PI, TAU)
	if a < 0.0:
		a += TAU
	return a - PI


## a から b へ、最短方向に最大 max_step だけ角度を近づける
static func approach_angle(a: float, b: float, max_step: float) -> float:
	var d := wrap_angle(b - a)
	if absf(d) <= max_step:
		return b
	return a + signf(d) * max_step


static func approach(v: float, target: float, step: float) -> float:
	if v < target:
		return minf(v + step, target)
	return maxf(v - step, target)


## フレームレートに依存しない指数的な追従の係数
static func damp(lambda: float, dt: float) -> float:
	return 1.0 - exp(-lambda * dt)


static func yaw_to_dir(yaw: float) -> Vector3:
	return Vector3(sin(yaw), 0.0, cos(yaw))


static func dir_to_yaw(x: float, z: float) -> float:
	return atan2(x, z)


static func hdist(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()


## 線分 p0→p1 と球（中心 c、半径 r）が交わるなら、線分上の位置 t（0〜1）を返す。交わらなければ -1
static func segment_sphere(p0: Vector3, p1: Vector3, c: Vector3, r: float) -> float:
	var d := p1 - p0
	var f := p0 - c
	var a := d.dot(d)
	if a < 1e-9:
		return 0.0 if f.dot(f) <= r * r else -1.0
	var b := 2.0 * f.dot(d)
	var cc := f.dot(f) - r * r
	if cc <= 0.0:
		return 0.0
	var disc := b * b - 4.0 * a * cc
	if disc < 0.0:
		return -1.0
	var t := (-b - sqrt(disc)) / (2.0 * a)
	return t if t >= 0.0 and t <= 1.0 else -1.0


static func load_json(path: String) -> Variant:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("読めない: %s" % path)
		return null
	return JSON.parse_string(f.get_as_text())
