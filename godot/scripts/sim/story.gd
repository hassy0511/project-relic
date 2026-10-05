class_name Story
extends RefCounted
## 会話とイベントの台本を進める。UI は dialogue を読んで描く。書き方は docs/design/42_コンテンツの書き方.md。
##
## 会話の行：{ who, face, text, choices? } か、途中の動作 { action: give_item / flag / objective / event, ... }
##   choices：[ { text, set?: フラグ, event?: イベント, say?: 次の会話 } ]。出し終えたあと上下で選び、決定で確定する
## イベントの手順（1 つの手順に主となる 1 つのキー）：
##   say / flag / clear / give / wait / wait_until / message / objective / sfx / music
##   if（then・else）/ event（別のイベントを呼ぶ）
##   open / close（扉）/ spawn（敵）/ boss（敵 id を戦闘開始に）/ go（部屋を移る）/ teleport（同じ部屋の中で移す）
##   camera（注視点）/ freeze（操作ロック）/ mark（印）/ shop・workshop・guild（画面を開く）/ accept・complete（依頼）/ autosave
##   hint（操作の案内を出し続ける。{ kb, pad, touch } か文字列。"" で消す）/ remove（住人 id を今の部屋から消す）
##   shake（画面の揺れの強さ。0.4 くらい）/ despawn（グループの敵を倒さずに消す）

const CHARS_PER_SEC := 45.0

var flags := {}
## 表示中の会話：{ id, who, face, text, shown, index, total, choices?, sel? }。無ければ {}
var dialogue := {}
var _dialogues: Dictionary
var _events: Dictionary
var _host  # GameSim
var _lines: Array = []
var _line_index := 0
var _shown_f := 0.0
var _event_queue: Array = []
var _wait_time := 0.0
var _waiting_dialogue := false
var _wait_cond = null
var _has_wait_cond := false


func _init(dialogues: Dictionary, events: Dictionary, host) -> void:
	_dialogues = dialogues
	_events = events
	_host = host


## 会話中は true（プレイヤーは操作できない）
func blocking() -> bool:
	return not dialogue.is_empty()


func running_event() -> bool:
	return not _event_queue.is_empty() or _waiting_dialogue or _wait_time > 0.0 or _has_wait_cond


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


## 選択肢のカーソルを動かす
func move_choice(d: int) -> void:
	if not dialogue.has("choices"):
		return
	dialogue.sel = posmod(int(dialogue.sel) + d, dialogue.choices.size())


## 決定ボタンが押されたとき。表示途中なら全文を出し、出し終わっていれば次の行へ（選択肢があれば確定）
func confirm() -> void:
	if dialogue.is_empty():
		return
	var text: String = dialogue.text
	if dialogue.shown < text.length():
		dialogue.shown = text.length()
		_shown_f = text.length()
		return
	var id: String = dialogue.id
	if dialogue.has("choices"):
		var opt: Dictionary = _lines[_line_index].choices[dialogue.sel]
		if opt.has("set"):
			_host.set_flag(opt.set)
		if opt.has("event"):
			start_event(opt.event)
		if opt.has("say"):
			start_dialogue(opt.say)
			return
	_line_index += 1
	_advance_to_text(id)


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
	if _has_wait_cond:
		if not Cond.eval(_wait_cond, _host):
			return
		_has_wait_cond = false
	while not _event_queue.is_empty() and dialogue.is_empty() and _wait_time <= 0.0 and not _has_wait_cond:
		_run_step(_event_queue.pop_front())


func _push_front(steps: Array) -> void:
	var q := steps.duplicate()
	q.append_array(_event_queue)
	_event_queue = q


func _run_step(step: Dictionary) -> void:
	var h = _host
	if step.has("say"):
		start_dialogue(step.say)
		_waiting_dialogue = true
	elif step.has("flag"):
		h.set_flag(step.flag, step.get("value", true))
	elif step.has("clear"):
		h.set_flag(step.clear, false)
	elif step.has("give"):
		h.grant(step.give)
	elif step.has("wait"):
		_wait_time = step.wait
	elif step.has("wait_until"):
		_wait_cond = step.wait_until
		_has_wait_cond = true
	elif step.has("message"):
		h.emit_event({"type": "message", "text": step.message})
	elif step.has("objective"):
		h.objective = step.objective
	elif step.has("sfx"):
		h.emit_event({"type": "sfx", "id": step.sfx})
	elif step.has("music"):
		h.emit_event({"type": "music", "id": step.music})
	elif step.has("if"):
		_push_front(step.get("then", []) if Cond.eval(step["if"], h) else step.get("else", []))
	elif step.has("event"):
		assert(_events.has(step.event), "イベントが見つからない: %s" % step.event)
		_push_front(_events[step.event].steps)
	elif step.has("open"):
		h.open_door(step.open)
	elif step.has("close"):
		h.close_door(step.close)
	elif step.has("spawn"):
		for e in step.spawn:
			h.spawn_enemy_spec(e)
	elif step.has("boss"):
		for e in h.enemies:
			if e.id == step.boss and e.alive:
				e.become_alert()
	elif step.has("go"):
		h.go_to(step.go.room, step.go.get("spawn", "start"), step.go.get("autosave", false))
	elif step.has("teleport"):
		var m: Dictionary = h.place(step.teleport)
		h.player.teleport(m.pos, m.yaw)
		h.cam.yaw = m.yaw
		h.emit_event({"type": "snap"})
	elif step.has("camera"):
		var c: Dictionary = step.camera
		if c.has("at") or c.has("pos"):
			h.cam_focus = h.place(c).pos + Vector3(0, float(c.get("height", 1.5)), 0)
			h.cam_focus_time = float(c.get("time", 2.0))
			_wait_time = float(c.get("time", 2.0)) if c.get("wait", true) else 0.0
		else:
			h.cam_focus = null
			h.cam_focus_time = 0.0
	elif step.has("freeze"):
		h.player_locked = bool(step.freeze)
	elif step.has("mark"):
		h.set_mark(step.mark)
	elif step.has("shop"):
		h.emit_event({"type": "ui", "kind": "shop", "id": step.shop})
	elif step.has("workshop"):
		h.emit_event({"type": "ui", "kind": "workshop", "id": step.workshop})
	elif step.has("guild"):
		h.emit_event({"type": "ui", "kind": "guild", "id": step.guild})
	elif step.has("accept"):
		Economy.accept_request(h, step.accept)
	elif step.has("complete"):
		Economy.complete_request(h, step.complete)
	elif step.has("autosave"):
		h.emit_event({"type": "autosave"})
	elif step.has("hint"):
		h.emit_event({"type": "hint", "text": step.hint})
	elif step.has("remove"):
		h.remove_npc(step.remove)
	elif step.has("shake"):
		h.emit_event({"type": "shake", "strength": float(step.shake)})
	elif step.has("despawn"):
		h.despawn_group(String(step.despawn))
	else:
		push_error("知らないイベントの手順: %s" % str(step))


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
			if line.has("choices"):
				dialogue["choices"] = line.choices.map(func(o): return o.text)
				dialogue["sel"] = 0
			return
		match line.get("action", ""):
			"give_item":
				_host.give_item(line.item)
			"objective":
				_host.objective = line.text
			"flag":
				_host.set_flag(line.flag)
			"event":
				start_event(line.event)
			"give":
				_host.grant(line.give)
		_line_index += 1
	dialogue = {}
