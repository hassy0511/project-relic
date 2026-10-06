class_name PadConfig
extends RefCounted
## 操作の割り当て（ゲームパッドのボタン・キーボードのキー）を持ち、InputMap に反映する。
## 設定画面（Menu.show_controls）から変えられ、user://input.cfg に保存される。
## パッドの割り当ては文字列：ボタンは "b0"（番号）、トリガーなどの軸は "a4+"（軸の番号と向き）。
## 「決定」「戻る」はメニュー用（Godot の ui_accept / ui_cancel に反映する）。ゲーム中の操作とは別の組として扱い、
## 同じボタンを重ねて割り当てられる（A がジャンプと決定、など）。

const PATH := "user://input.cfg"

## [名前, 表示, 組]。組が同じ中で、同じボタン・キーを割り当てると入れ替える
const ACTIONS := [
	["jump", "ジャンプ", "game"], ["dash", "ダッシュ", "game"], ["fire", "撃つ", "game"], ["sword", "斬る", "game"],
	["special", "特殊武器", "game"], ["lock_on", "ロックオン", "game"], ["heal", "回復", "game"],
	["camera_reset", "カメラを戻す", "game"], ["pause", "ポーズ", "game"], ["map", "地図", "game"],
	["confirm", "決定（メニュー・会話）", "menu"], ["back", "戻る（メニュー）", "menu"],
]
## 名前 → Godot の InputMap の名前（メニューの決定・戻る）
const MENU_ACTIONS := {"confirm": "ui_accept", "back": "ui_cancel"}

## Xbox 配置：A=0 B=1 X=2 Y=3 Back=4 Start=6 L3=7 R3=8 LB=9 RB=10 十字キー 上=11 下=12 左=13 右=14
const BUTTON_NAMES := {
	0: "A", 1: "B", 2: "X", 3: "Y", 4: "Back", 5: "Guide", 6: "Start", 7: "L3", 8: "R3", 9: "LB", 10: "RB",
	11: "十字上", 12: "十字下", 13: "十字左", 14: "十字右", 15: "Misc", 16: "パドル1", 17: "パドル2", 18: "パドル3",
	19: "パドル4", 20: "タッチパッド",
}
const AXIS_NAMES := {4: "LT", 5: "RT"}

static var path := PATH
## 名前 → パッドの割り当て（"b0" など。"" は未割り当て）
static var pad := {}
## 名前 → キー（physical_keycode）の配列
static var keys := {}
static var _loaded := false


static func defaults() -> Dictionary:
	return {
		"pad": {
			"jump": "b0", "dash": "b1", "sword": "b2", "special": "b3", "heal": "b11", "camera_reset": "b8",
			"pause": "b6", "map": "b4", "fire": "a5+", "lock_on": "a4+", "confirm": "b0", "back": "b1",
		},
		"keys": {
			"jump": [KEY_SPACE], "dash": [KEY_SHIFT], "sword": [KEY_E, KEY_K], "special": [KEY_Q], "heal": [KEY_R],
			"camera_reset": [KEY_C], "lock_on": [KEY_F, KEY_L], "fire": [KEY_J], "pause": [KEY_ESCAPE], "map": [KEY_TAB],
			"confirm": [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE], "back": [KEY_ESCAPE],
		},
	}


static func reset() -> void:
	var d := defaults()
	pad = d.pad
	keys = d.keys
	_loaded = true


## 読み込む（まだなら）。ファイルが無い・壊れているときは初期の割り当て
static func ensure_loaded() -> void:
	if not _loaded:
		load_file()


static func load_file() -> void:
	reset()
	var cf := ConfigFile.new()
	if cf.load(path) != OK:
		return
	for a in ACTIONS:
		var id: String = a[0]
		var p = cf.get_value("pad", id, "?")
		if p is String and (p == "" or _valid_code(p)):
			pad[id] = p
		var k = cf.get_value("keys", id, [])
		if k is Array:
			var out := []
			for v in k:
				if v is int and v > 0:
					out.append(v)
			if not out.is_empty():
				keys[id] = out


static func save() -> void:
	var cf := ConfigFile.new()
	for a in ACTIONS:
		var id: String = a[0]
		cf.set_value("pad", id, pad.get(id, ""))
		cf.set_value("keys", id, keys.get(id, []))
	cf.save(path)


static func _valid_code(c: String) -> bool:
	if c.length() < 2:
		return false
	if c[0] == "b":
		return c.substr(1).is_valid_int()
	if c[0] == "a" and (c.ends_with("+") or c.ends_with("-")):
		return c.substr(1, c.length() - 2).is_valid_int()
	return false


## 軸（トリガー・十字キーが軸で届く機種）の割り当て。スティックの軸（0〜3）は、倒しているだけで反応するので除く。
## 機種によってトリガーは「ボタン」でも「軸」でも届くので、どちらも割り当てられる（軸は番号 4 以上、押した向きも覚える）
static func code_of_axis(axis: int, value: float) -> String:
	if axis < 4 or absf(value) < 0.6:
		return ""
	return "a%d%s" % [axis, "+" if value > 0.0 else "-"]


## 入力イベント → パッドの割り当て文字列（割り当てられないものは ""）
static func code_of_event(e: InputEvent) -> String:
	if e is InputEventJoypadButton and e.pressed:
		return "b%d" % e.button_index
	if e is InputEventJoypadMotion:
		return code_of_axis(e.axis, e.axis_value)
	return ""


static func code_text(c: String) -> String:
	if c == "":
		return "（なし）"
	if c[0] == "b":
		var i := int(c.substr(1))
		return "%s（%d）" % [BUTTON_NAMES[i], i] if BUTTON_NAMES.has(i) else "ボタン %d" % i
	var ax := int(c.substr(1, c.length() - 2))
	var sg := "" if c.ends_with("+") else "−"
	return "%s（軸 %d）" % [AXIS_NAMES[ax], ax] if AXIS_NAMES.has(ax) and c.ends_with("+") else "軸 %d%s" % [ax, sg if sg != "" else "＋"]


## 短い名前（案内の文に入れる）："A"、"RT" など
static func code_short(c: String) -> String:
	if c == "":
		return "（なし）"
	if c[0] == "b":
		var i := int(c.substr(1))
		return BUTTON_NAMES.get(i, "ボタン%d" % i)
	var ax := int(c.substr(1, c.length() - 2))
	if AXIS_NAMES.has(ax) and c.ends_with("+"):
		return AXIS_NAMES[ax]
	return "軸%d%s" % [ax, "＋" if c.ends_with("+") else "−"]


static func pad_short(action: String) -> String:
	ensure_loaded()
	return code_short(String(pad.get(action, "")))


static func keys_text(action: String) -> String:
	ensure_loaded()
	var out := []
	for k in keys.get(action, []):
		out.append(OS.get_keycode_string(k))
	return " / ".join(out) if not out.is_empty() else "（なし）"


static func group_of(action: String) -> String:
	for a in ACTIONS:
		if a[0] == action:
			return a[2]
	return ""


static func label_of(action: String) -> String:
	for a in ACTIONS:
		if a[0] == action:
			return a[1]
	return action


## パッドの割り当てを変える。同じ組で既に使っている操作があれば入れ替える。返り値：入れ替えた相手（なければ ""）
static func assign_pad(action: String, code: String) -> String:
	ensure_loaded()
	var old := String(pad.get(action, ""))
	var swapped := ""
	for a in ACTIONS:
		var id: String = a[0]
		if id != action and a[2] == group_of(action) and code != "" and pad.get(id, "") == code:
			pad[id] = old
			swapped = id
	pad[action] = code
	apply()
	save()
	return swapped


static func assign_key(action: String, keycode: int) -> String:
	ensure_loaded()
	var old: Array = keys.get(action, [])
	var swapped := ""
	for a in ACTIONS:
		var id: String = a[0]
		if id != action and a[2] == group_of(action) and keys.get(id, []).has(keycode):
			keys[id] = old.duplicate() if not old.is_empty() else [keycode]
			swapped = id
	keys[action] = [keycode]
	apply()
	save()
	return swapped


static func reset_all() -> void:
	reset()
	apply()
	save()


## InputMap に反映する。マウスの割り当てはそのまま、キー・パッドの割り当てだけ作り直す
static func apply() -> void:
	ensure_loaded()
	for a in ACTIONS:
		var id: String = a[0]
		var act := String(MENU_ACTIONS.get(id, id))
		if not InputMap.has_action(act):
			InputMap.add_action(act, 0.3)
		for e in InputMap.action_get_events(act):
			if e is InputEventKey or e is InputEventJoypadButton or e is InputEventJoypadMotion:
				InputMap.action_erase_event(act, e)
		for k in keys.get(id, []):
			var ek := InputEventKey.new()
			ek.physical_keycode = k
			InputMap.action_add_event(act, ek)
		var c := String(pad.get(id, ""))
		if c == "":
			continue
		if c[0] == "b":
			var eb := InputEventJoypadButton.new()
			eb.device = -1
			eb.button_index = int(c.substr(1))
			InputMap.action_add_event(act, eb)
		else:
			var em := InputEventJoypadMotion.new()
			em.device = -1
			em.axis = int(c.substr(1, c.length() - 2))
			em.axis_value = 1.0 if c.ends_with("+") else -1.0
			InputMap.action_add_event(act, em)
