class_name Story
extends RefCounted
## 会話とイベントの台本を進める。UI は dialogue を読んで描く。書き方は docs/design/42_コンテンツの書き方.md。
##
## 会話の行：{ who, face, text, choices? } か、途中の動作 { action: give_item / flag / objective / event, ... }
##   choices：[ { text, set?: フラグ, event?: イベント, say?: 次の会話 } ]。出し終えたあと上下で選び、決定で確定する
## イベントの手順（1 つの手順に主となる 1 つのキー）：
##   say / flag / clear / give / wait / wait_until / message / objective / sfx / music（曲の ID。"none" で無音、"auto" で部屋の曲へ戻す）
##   if（then・else）/ event（別のイベントを呼ぶ）
##   open / close（扉）/ spawn（敵）/ boss（敵 id を戦闘開始に）/ go（部屋を移る）/ teleport（同じ部屋の中で移す）
##   camera（注視点）/ freeze（操作ロック）/ mark（印）/ shop・workshop・guild（画面を開く）/ accept・complete（依頼）/ autosave
##   hint（操作の案内を出し続ける。{ kb, pad, touch } か文字列。"" で消す）/ remove（住人 id を今の部屋から消す）
##   shake（画面の揺れの強さ。0.4 くらい）/ despawn（グループの敵を倒さずに消す）
##   fx（見た目の合図。出来事 {type: "fx", id, part?, at?} を出すだけで遊びは変えない。Fx が描く：frame_fit・node_memory）
##   cutscene（true / false：黒帯の場面を始める・終える。イベントに "cutscene": true と書くと、始めに {"cutscene": true} を置いたのと同じ）
##
## 黒帯の場面（cutscene）：台本がカメラを取った（camera の手順で注視点を決めた）か、"cutscene": true のイベントが始まってから、
## プレイヤーに操作が戻るまで（{"freeze": false}・{"cutscene": false}・操作できる間の wait_until で待ち始める・台本がすべて終わる）。
## 見た目は上下に黒帯を出して遊びの表示を隠し、長押しのスキップ（skip）を受け付ける。
## スキップ（begin_skip）：残りの手順をこの刻みのうちに、ふだんと同じ _run_step で走らせる（待ち・カメラの寄せは飛ばし、会話は送り切る）。
## 選択肢では止まる（選んだあと、まだ押していれば続ける。after_choice）。部屋を移る手順（go）では、移り終わって移った部屋の世界が
## 1 刻み動くまで待ってから続ける（見ているときの待ちの間と同じく、移った先のトリガーが走る）。黒帯の場面が終わる所（操作が戻る所）で止まる。
## スキップの間に出る効果音・画面の揺れは出さず（GameSim.emit_event）、見た目の合図には skipped を付ける（Fx は光らせずに終わりの姿にする）

const CHARS_PER_SEC := 45.0

var flags := {}
## 表示中の会話：{ id, who, face, text, shown, index, total, choices?, sel? }。無ければ {}
var dialogue := {}
## 黒帯の場面の間 true（上の説明）。見た目（Hud・TouchControls）は GameSim.cinematic() で読む
var cutscene := false
## 長押しのスキップで、残りの手順を待たずに進めている間 true
var skipping := false
## スキップが選択肢で止まっている（プレイヤーが選ぶのを待つ）
var skip_at_choice := false
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
## スキップの間に選択肢が選ばれた（after_choice が続けるか決める）
var _choice_made := false
## スキップの間に部屋を移る手順（go）を走らせた：1 ＝ 移り終わるのを待つ、2 ＝ 移った部屋の世界を 1 刻み動かしてから続ける
var _skip_room := 0


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


## そのイベントが、台本のカメラ（camera の手順）を使うか、黒帯の場面（"cutscene": true のイベント・{"cutscene": true} の手順）を含むか。
## if の両方の枝・呼ぶイベント・会話（行の動作のイベント・選択肢の先）までたどる。
## 住人に話しかけて始まるイベントが自分でカメラを動かす・黒帯の場面になるなら、会話のカメラは使わない（GameSim.talk_npc）
func event_uses_camera(id: String) -> bool:
	return _event_cam(id, {})


## その会話が（行の動作・選択肢の先のイベントで）台本のカメラ・黒帯の場面を使うか
func dialogue_uses_camera(id: String) -> bool:
	return _dialogue_cam(id, {})


## イベントに "cutscene": true と書いてあるか（黒帯の場面として始まる）
func event_is_cutscene(id: String) -> bool:
	return bool(_events.get(id, {}).get("cutscene", false))


func _event_cam(id: String, seen: Dictionary) -> bool:
	if seen.has("e:" + id) or not _events.has(id):
		return false
	seen["e:" + id] = true
	if event_is_cutscene(id):
		return true
	return _steps_cam(_events[id].steps, seen)


func _dialogue_cam(id: String, seen: Dictionary) -> bool:
	if seen.has("d:" + id) or not _dialogues.has(id):
		return false
	seen["d:" + id] = true
	for ln in _dialogues[id].lines:
		if ln.get("action", "") == "event" and _event_cam(String(ln.event), seen):
			return true
		for o in ln.get("choices", []):
			if (o.has("event") and _event_cam(String(o.event), seen)) or (o.has("say") and _dialogue_cam(String(o.say), seen)):
				return true
	return false


func _steps_cam(steps: Array, seen: Dictionary) -> bool:
	for s in steps:
		if s.has("camera") or (s.has("cutscene") and bool(s.cutscene)):
			return true
		if s.has("if") and (_steps_cam(s.get("then", []), seen) or _steps_cam(s.get("else", []), seen)):
			return true
		if (s.has("event") and _event_cam(String(s.event), seen)) or (s.has("say") and _dialogue_cam(String(s.say), seen)):
			return true
	return false


func start_dialogue(id: String) -> void:
	assert(_dialogues.has(id), "会話が見つからない: %s" % id)
	_lines = _dialogues[id].lines
	_line_index = 0
	dialogue = {}
	_advance_to_text(id)


func start_event(id: String) -> void:
	assert(_events.has(id), "イベントが見つからない: %s" % id)
	_event_queue.append_array(_steps_of(id))


## イベントの手順。"cutscene": true のイベントは、始めに黒帯の場面を始める手順を置く（手順が走った刻みから黒帯になる。
## 何もせずに終わるイベント（2 回目の分岐など）は、同じ刻みのうちに場面も終わるので黒帯は出ない）
func _steps_of(id: String) -> Array:
	var steps: Array = _events[id].steps
	if event_is_cutscene(id):
		return [{"cutscene": true}] + steps
	return steps


## 長押しでスキップできるか：黒帯の場面で、まだスキップしていない。操作できる間の遊びの待ち（wait_until）の間は除く
func skippable() -> bool:
	if not cutscene or skipping:
		return false
	if _has_wait_cond and not Cond.eval(_wait_cond, _host):
		return false
	return running_event() or not dialogue.is_empty()


## スキップを始める（GameSim が長押しを数え終えたとき）。台本のカメラ（注視・置き場所）はここで手放す（寄せを待たない）。
## 残りの手順は、この刻みの update から _fast_forward が走らせる
func begin_skip() -> void:
	if not skippable():
		return
	skipping = true
	skip_at_choice = false
	_choice_made = false
	_skip_room = 0
	_host.cam_focus = null
	_host.cam_focus_time = 0.0
	_host.cam_eye = null


## スキップを終える。見た目へ「スキップした」と知らせる（カメラをすぐ戻す・待っている見た目の合図を終わりの姿にする）
func end_skip() -> void:
	if not skipping:
		return
	skipping = false
	skip_at_choice = false
	_choice_made = false
	_skip_room = 0
	_host.emit_event({"type": "skipped"})


## スキップが選択肢で止まっていて、プレイヤーが選んだ（GameSim.step が会話の入力のあとに呼ぶ）：
## held（スキップのボタン）をまだ押していれば続けて進め、離していればスキップを終える（残りはふだんどおり見る）
func after_choice(held: bool) -> void:
	if not (skipping and skip_at_choice and _choice_made):
		return
	skip_at_choice = false
	_choice_made = false
	if not held:
		end_skip()


## 選択肢のカーソルを動かす
func move_choice(d: int) -> void:
	if not dialogue.has("choices"):
		return
	dialogue.sel = posmod(int(dialogue.sel) + d, dialogue.choices.size())


## 選択肢を番号で選んで確定する（スマホで札をタップしたとき）。選択肢を出し終えていない・番号が範囲の外なら何もしない（false）
func choose(i: int) -> bool:
	if not dialogue.has("choices") or i < 0 or i >= dialogue.choices.size():
		return false
	if dialogue.shown < String(dialogue.text).length():
		return false
	dialogue.sel = i
	confirm()
	return true


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
		if skip_at_choice:
			_choice_made = true
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
	if skipping:
		_fast_forward()
		if skipping:
			# 選択肢・部屋の移動を待っている
			_end_cutscene_if_done()
			return
		# スキップが終わった（操作が戻る所）：続きの手順は、見ているときと同じく、この刻みのうちにふだんどおり走らせる
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
	_end_cutscene_if_done()


## 台本がすべて終わったら（手順も会話も待ちも無い）、黒帯の場面も終わる
func _end_cutscene_if_done() -> void:
	if cutscene and dialogue.is_empty() and not running_event():
		cutscene = false


## スキップ：残りの手順を、ふだんと同じ _run_step で待たずに走らせる。会話は全文を出して送り切る（行の間の動作も今までどおり走る）。
## 止まる所：選択肢（選ぶのを待つ）・部屋の移動（移り終わるまで。そのあと移った部屋の世界を 1 刻み動かす）・
## 操作できる間の遊びの待ち（wait_until が偽）・黒帯の場面の終わり（操作が戻る所）・台本の終わり
func _fast_forward() -> void:
	for guard in 100000:
		if not skipping or skip_at_choice:
			return
		if not dialogue.is_empty():
			var text: String = dialogue.text
			dialogue.shown = text.length()
			_shown_f = text.length()
			if dialogue.has("choices"):
				# 選択肢はプレイヤーが選ぶ（全文を出して待つ。選んだあとは GameSim.step → after_choice）
				skip_at_choice = true
				return
			confirm()
			continue
		_waiting_dialogue = false
		if _skip_room == 1:
			# 部屋の移動（GameSim の刻みの最後）と読み込み待ち（2 刻み）が終わるまで待つ
			if not _host.room_settled():
				return
			# 移った部屋の世界を 1 刻み動かしてから続ける（入口のトリガーなど、見ているときの待ちの間に走るもの）
			_skip_room = 2
			return
		_skip_room = 0
		_wait_time = 0.0
		if _has_wait_cond:
			if not Cond.eval(_wait_cond, _host):
				# 遊び（敵の全滅待ちなど）：操作が戻る所まででスキップを止める
				end_skip()
				return
			_has_wait_cond = false
		if not cutscene or _event_queue.is_empty():
			end_skip()
			return
		var step: Dictionary = _event_queue.pop_front()
		_run_step(step)
		if step.has("go"):
			_skip_room = 1
	push_error("スキップが終わらない（手順が多すぎる）")
	end_skip()


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
		# 操作できる間に遊び（敵の全滅など）を待ち始めたら、黒帯の場面はそこまで（プレイヤーに操作が戻っている）
		if cutscene and not h.player_locked and not Cond.eval(_wait_cond, h):
			cutscene = false
	elif step.has("message"):
		h.emit_event({"type": "message", "text": step.message})
	elif step.has("objective"):
		h.objective = step.objective
	elif step.has("sfx"):
		h.emit_event({"type": "sfx", "id": step.sfx})
	elif step.has("music"):
		h.music_override = "" if step.music == "auto" else String(step.music)
		h.emit_event({"type": "music", "id": step.music})
	elif step.has("if"):
		_push_front(step.get("then", []) if Cond.eval(step["if"], h) else step.get("else", []))
	elif step.has("event"):
		assert(_events.has(step.event), "イベントが見つからない: %s" % step.event)
		_push_front(_steps_of(step.event))
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
		if (c.has("at") or c.has("pos")) and skipping:
			# スキップ中：台本がカメラを取ったことだけ覚える（注視・置き場所へ寄せない。待たない）
			cutscene = true
		elif c.has("at") or c.has("pos"):
			# 台本がカメラを取った：ここから黒帯の場面（操作が戻るまで）
			cutscene = true
			var focus: Vector3 = h.place(c).pos + Vector3(0, float(c.get("height", 1.5)), 0)
			# "eye": [x,y,z]：カメラをその場所へ置いて注視点を見る（部屋の外から見せる。町の下のオルドの脚など）
			var eye = RoomGeo.v3(c.eye) if c.has("eye") else null
			# "side": true：ハルが部屋の真ん中の線（x = 0）の反対側にいたら、注視点と置き場所を左右に映す
			# （左右対称の部屋で、真ん中の柱の陰にハルが隠れないように。炉心のノードの記憶）
			if c.get("side", false) and eye != null and (h.player.pos.x < 0.0) != (eye.x < 0.0):
				focus.x = -focus.x
				eye.x = -eye.x
			h.cam_focus = focus
			h.cam_focus_time = float(c.get("time", 2.0))
			h.cam_eye = eye
			_wait_time = float(c.get("time", 2.0)) if c.get("wait", true) else 0.0
		else:
			h.cam_focus = null
			h.cam_focus_time = 0.0
			h.cam_eye = null
	elif step.has("freeze"):
		h.player_locked = bool(step.freeze)
		# 操作が戻ったら、黒帯の場面はそこまで（続く手順は、ふだんの会話・案内・遊び）
		if not h.player_locked:
			cutscene = false
	elif step.has("cutscene"):
		cutscene = bool(step.cutscene)
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
		if float(step.shake) >= 0.3:
			h.emit_event({"type": "sfx", "id": "rumble"})
	elif step.has("despawn"):
		h.despawn_group(String(step.despawn))
	elif step.has("fx"):
		# 見た目の合図（Fx.handle が描く）："part"（フレームの部位）、"pos" か "at"＋"height"（エフェクトの出る所）
		var e := {"type": "fx", "id": String(step.fx)}
		if skipping:
			# スキップ中：光らせずに終わりの姿にする（フレームの部品はすぐ付ける。記憶の光は流さない）
			e["skipped"] = true
		if step.has("part"):
			e["part"] = String(step.part)
		if step.has("pos") or step.has("at"):
			e["at"] = h.place(step).pos + Vector3(0, float(step.get("height", 0.0)), 0)
		h.emit_event(e)
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
