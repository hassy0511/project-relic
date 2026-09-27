class_name Story
extends RefCounted
## 会話とイベントの台本を進める。UI は dialogue を読んで描く。
## 会話の行：{ who, face, text } か、途中の動作 { action: give_item / flag / objective, ... }
## イベントの手順：say / flag / give / wait / message / objective / sfx

const CHARS_PER_SEC := 45.0

var flags := {}
## 表示中の会話：{ id, who, face, text, shown, index, total }。無ければ {}
var dialogue := {}
var _dialogues: Dictionary
var _events: Dictionary
var _host  # GameSim（give_item などを持つ）
var _lines: Array = []
var _line_index := 0
var _shown_f := 0.0
var _event_queue: Array = []
var _wait_time := 0.0
var _waiting_dialogue := false


func _init(dialogues: Dictionary, events: Dictionary, host) -> void:
	_dialogues = dialogues
	_events = events
	_host = host


## 会話中は true（プレイヤーは操作できない）
func blocking() -> bool:
	return not dialogue.is_empty()


func running_event() -> bool:
	return not _event_queue.is_empty() or _waiting_dialogue or _wait_time > 0.0


func has_dialogue(id: String) -> bool:
	return _dialogues.has(id)


func start_dialogue(id: String) -> void:
	assert(_dialogues.has(id), "会話が見つからない: %s" % id)
	_lines = _dialogues[id].lines
	_line_index = 0
	dialogue = {}
	_advance_to_text(id)


func start_event(id: String) -> void:
	assert(_events.has(id), "イベントが見つからない: %s" % id)
	_event_queue.append_array(_events[id].steps)


## 決定ボタンが押されたとき。表示途中なら全文を出し、出し終わっていれば次の行へ
func confirm() -> void:
	if dialogue.is_empty():
		return
	var text: String = dialogue.text
	if dialogue.shown < text.length():
		dialogue.shown = text.length()
		_shown_f = text.length()
		return
	_line_index += 1
	_advance_to_text(dialogue.id)


func update(dt: float) -> void:
	if not dialogue.is_empty():
		var text: String = dialogue.text
		if dialogue.shown < text.length():
			_shown_f += CHARS_PER_SEC * dt
			dialogue.shown = mini(text.length(), int(floor(_shown_f)))
		return
	if _waiting_dialogue:
		_waiting_dialogue = false
	if _wait_time > 0.0:
		_wait_time -= dt
		return
	while not _event_queue.is_empty() and dialogue.is_empty() and _wait_time <= 0.0:
		_run_step(_event_queue.pop_front())


func _run_step(step: Dictionary) -> void:
	var h = _host
	if step.has("say"):
		start_dialogue(step.say)
		_waiting_dialogue = true
	elif step.has("flag"):
		flags[step.flag] = true
	elif step.has("give"):
		if step.give.has("cells"):
			h.give_cells(int(step.give.cells))
		if step.give.has("item"):
			h.give_item(step.give.item)
	elif step.has("wait"):
		_wait_time = step.wait
	elif step.has("message"):
		h.emit_event({"type": "message", "text": step.message})
	elif step.has("objective"):
		h.objective = step.objective
	elif step.has("sfx"):
		h.emit_event({"type": "sfx", "id": step.sfx})


## 次の「セリフ」の行まで進める。途中の動作（アイテムを渡す等）はその場で実行する
func _advance_to_text(id: String) -> void:
	while _line_index < _lines.size():
		var line: Dictionary = _lines[_line_index]
		if line.has("who"):
			_shown_f = 0.0
			dialogue = {
				"id": id, "who": line.who, "face": line.get("face", "normal"), "text": line.text,
				"shown": 0, "index": _line_index, "total": _lines.size(),
			}
			return
		match line.get("action", ""):
			"give_item":
				_host.give_item(line.item)
			"objective":
				_host.objective = line.text
			"flag":
				flags[line.flag] = true
		_line_index += 1
	dialogue = {}
