class_name InputFrame
extends RefCounted
## 1 刻み分の入力。ゲームの中身はこれだけを見て動く（キーやボタンの種類を知らない）。
## 記録・再生（リプレイ）できるよう、ただのデータにしておく。

const BUTTONS := ["jump", "dash", "fire", "sword", "special", "lock_on", "heal"]

## 移動（-1〜1）。move_y は前が +1
var move_x := 0.0
var move_y := 0.0
## カメラ操作（この刻みでの回転量、ラジアン）
var look_x := 0.0
var look_y := 0.0
var look_active := false
var jump := false
var dash := false
var fire := false
var sword := false
var special := false
var lock_on := false
var heal := false
## 決定（メニュー・会話を送る）
var confirm := false
var switch_left := false
var switch_right := false
var camera_reset := false


## 辞書から作る（テストで使う）。例：InputFrame.of({"move_y": 1, "jump": true})
static func of(d: Dictionary) -> InputFrame:
	var f := InputFrame.new()
	for k in d:
		f.set(k, d[k])
	return f


func button(name: String) -> bool:
	return bool(get(name))


## ボタンの「押した瞬間」「離した瞬間」を前の刻みとの比較で得る
class Edges:
	var prev := InputFrame.new()
	var cur := InputFrame.new()

	func update(frame: InputFrame) -> void:
		prev = cur
		cur = frame

	func pressed(k: String) -> bool:
		return cur.button(k) and not prev.button(k)

	func released(k: String) -> bool:
		return not cur.button(k) and prev.button(k)

	func down(k: String) -> bool:
		return cur.button(k)
