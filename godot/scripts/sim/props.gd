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
	## false なら壊れた状態をセーブしない（ボス部屋の柱：やり直しで元に戻る）
	var persist := true
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
	var event := ""

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
	## talk の代わりにイベントを走らせる（任意）
	var event := ""
	var range_m := 2.2
	var prompt := "話す"
	var body = null

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
	## 使ったとき立てるフラグ・走らせるイベント（任意）
	var flag := ""
	var event := ""

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
	## enter（範囲に入る）| flag（cond が真になる）| cleared（group の敵を全部倒す）
	var on := "enter"
	var cond = null
	var group := ""
	## false なら「走った」ことをセーブしない（戦闘の部屋のやり直しで、もう一度走る）
	var persist := true

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


## 扉：施錠（lock の条件）・近づいて調べると開く（interact）か条件が満ちると勝手に開く（auto）。
## side：front＝正面（ローカル +Z 側）からだけ開けられる／back＝背面から／any。近道の「内側から開ける」に使う
class Door:
	var id: String
	var pos: Vector3
	var size: Vector3
	var yaw: float
	var lock = null
	var opens := "interact"
	var side := "any"
	var consume := ""
	var lock_text := "鍵がかかっている"
	var event := ""
	var is_open := false
	var open_amt := 0.0
	var body: StaticBody3D = null
	var range_m := 2.4
	var prompt := "開ける"

	func enabled() -> bool:
		return not is_open and opens == "interact"

	## player_pos 側から使えるか
	func usable_from(p: Vector3) -> bool:
		if side == "any":
			return true
		var lz := (p.x - pos.x) * sin(yaw) + (p.z - pos.z) * cos(yaw)
		return lz > 0.0 if side == "front" else lz < 0.0


## 別の部屋へ移る出口（範囲に入ると移る）。lock が偽なら移れない
class Exit:
	var id: String
	var center: Vector3
	var half: Vector3
	var to: String
	var spawn: String
	var lock = null
	var lock_text := "まだ進めない"
	var msg_cool := 0.0

	func contains(p: Vector3) -> bool:
		return absf(p.x - center.x) <= half.x and absf(p.y - center.y) <= half.y + 1.0 and absf(p.z - center.z) <= half.z


## スイッチ：shoot＝撃つと入る（動力の球・弁の輪）／interact＝調べると入る。
## timer>0 なら入っている時間が決まっている。toggle なら調べるたびに入り切り。入っている間フラグ switch.<id> が立つ
class Switch:
	var id: String
	var pos: Vector3
	var mode := "shoot"
	var radius := 0.7
	var on := false
	var timer := 0.0
	var time_left := 0.0
	var toggle := false
	var range_m := 2.0
	var prompt := "動かす"
	var cond = null

	func enabled() -> bool:
		return mode == "interact" and (toggle or not on)


## 動く足場・ピストン・リフト。from→to を往復する。
## toggle：cond が真なら to、偽なら from へ／pingpong：cond が真の間ずっと往復／ride：上に乗ると to へ、降りると from へ
class Mover:
	var id: String
	var size: Vector3
	var from: Vector3
	var to: Vector3
	var speed := 2.0
	var mode := "toggle"
	var cond = null
	var wait := 1.0
	var t := 0.0
	var dir := 1.0
	var hold := 0.0
	var pos: Vector3
	var body: StaticBody3D = null

	func length() -> float:
		return maxf(0.001, from.distance_to(to))

	func at_t(v: float) -> Vector3:
		return from.lerp(to, v)

	## 足場の上（底面の中心 pos、上面の高さ pos.y + size.y）に乗っているか
	func carries(feet: Vector3) -> bool:
		return absf(feet.x - pos.x) <= size.x * 0.5 + 0.15 and absf(feet.z - pos.z) <= size.z * 0.5 + 0.15 \
			and feet.y >= pos.y + size.y - 0.2 and feet.y <= pos.y + size.y + 0.4


## 調べる物（端末・看板）：調べるとイベントが走る
class Terminal:
	var id: String
	var pos: Vector3
	var event: String
	var range_m := 2.0
	var prompt := "調べる"

	func enabled() -> bool:
		return true


## 置いてある拾い物（遺物・素材・セルなど）。触れると 1 度だけ手に入る
class Loot:
	var id: String
	var pos: Vector3
	var contents: Dictionary
	var taken := false
	var radius := 1.1
