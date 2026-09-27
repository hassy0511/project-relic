class_name Rng
extends RefCounted
## 種つきの乱数（mulberry32）。ゲームの中身ではこれだけを使う（同じ入力なら同じ結果になるように）

const M := 0xFFFFFFFF
var _s: int


func _init(seed_value: int = 1) -> void:
	_s = seed_value & M


static func _imul(a: int, b: int) -> int:
	return (a * b) & M


func next_float() -> float:
	_s = (_s + 0x6D2B79F5) & M
	var t := _s
	t = _imul(t ^ (t >> 15), t | 1)
	t = t ^ ((t + _imul(t ^ (t >> 7), t | 61)) & M)
	return float((t ^ (t >> 14)) & M) / 4294967296.0


func range_f(lo: float, hi: float) -> float:
	return lo + (hi - lo) * next_float()


func int_in(lo: int, hi_inclusive: int) -> int:
	return int(floor(range_f(lo, hi_inclusive + 1)))


func chance(p: float) -> bool:
	return next_float() < p
