class_name Shot
extends RefCounted
## 弾。剛体にはせず、毎刻み線分で当たりを調べる。
## kind：normal / charge1 / charge2 / wave / enemy

var origin: Vector3
var dir: Vector3
var speed: float
var range_m: float
var damage: float
var radius: float
var pierce: bool
var kind: String
var homing = null  # Enemy
var from_player: bool

var pos: Vector3
var prev: Vector3
var vel: Vector3
var traveled := 0.0
var alive := true
var hit := {}


func _init(spec: Dictionary, player_shot: bool) -> void:
	origin = spec.origin
	dir = spec.dir
	speed = spec.speed
	range_m = spec.range
	damage = spec.damage
	radius = spec.radius
	pierce = spec.pierce
	kind = spec.kind
	homing = spec.get("homing")
	from_player = player_shot
	pos = origin
	prev = origin
	vel = dir.normalized() * speed
