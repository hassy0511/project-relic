class_name GameAudio
extends Node
## 効果音と BGM。音はすべて ID で呼び、ファイル（assets/audio/<ID>.ogg）の差し替えだけで音を変えられる。
## 位置つきの音は、カメラ（聞き手）との距離で大きさと左右が変わる。

var _streams := {}
var _last := {}
var _music: AudioStreamPlayer
var _music_b: AudioStreamPlayer
var _music_tween: Tween
var _active: AudioStreamPlayer = null
## 今かけている曲の ID（"" ＝ なし）。曲が最後まで鳴り終わると "" に戻り、music_finished が出る（ファンファーレなど、ループしない曲）
var current_music := ""
## 音楽のクロスフェードの秒数
var fade_time := 1.4
signal music_finished(id: String)
var _pool: Array[AudioStreamPlayer3D] = []
var _ui_pool: Array[AudioStreamPlayer] = []
var volumes := {"master": 0.8, "music": 0.5, "sfx": 0.8}


func _ready() -> void:
	_music = AudioStreamPlayer.new()
	_music.volume_db = -60.0
	add_child(_music)
	_music_b = AudioStreamPlayer.new()
	_music_b.volume_db = -60.0
	add_child(_music_b)
	_music.finished.connect(_on_music_finished.bind(_music))
	_music_b.finished.connect(_on_music_finished.bind(_music_b))
	for i in 16:
		var p := AudioStreamPlayer3D.new()
		p.unit_size = 6.0
		p.max_distance = 60.0
		p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
		add_child(p)
		_pool.append(p)
	for i in 8:
		var q := AudioStreamPlayer.new()
		add_child(q)
		_ui_pool.append(q)
	AudioServer.set_bus_volume_db(0, linear_to_db(volumes.master))


func _stream(id: String) -> AudioStream:
	if not _streams.has(id):
		var path := "res://assets/audio/%s.ogg" % id
		_streams[id] = load(path) if ResourceLoader.exists(path) else null
	return _streams[id]


## 効果音。at を渡すと 3D の位置から鳴る
func play(id: String, at = null) -> void:
	var s := _stream(id)
	if s == null:
		return
	# 同じ音が同時に鳴りすぎないように
	var now := Time.get_ticks_msec()
	if now - int(_last.get(id, -1000)) < 30:
		return
	_last[id] = now
	var pitch := randf_range(0.95, 1.05)
	var vol := linear_to_db(volumes.sfx)
	if at is Vector3:
		for p in _pool:
			if not p.playing:
				p.stream = s
				p.global_position = at
				p.pitch_scale = pitch
				p.volume_db = vol
				p.play()
				return
	for q in _ui_pool:
		if not q.playing:
			q.stream = s
			q.pitch_scale = pitch
			q.volume_db = vol
			q.play()
			return


func _on_music_finished(p: AudioStreamPlayer) -> void:
	if p == _active:
		var id := current_music
		current_music = ""
		music_finished.emit(id)


## 曲を切り替える（今の曲を消しながら新しい曲を上げる）。同じ曲なら何もしない。"" で止める。bgm_end は繰り返さない
func play_music(id: String, fade := -1.0) -> void:
	if id == current_music:
		return
	var seconds := fade_time if fade < 0.0 else fade
	current_music = id
	var old := _active if _active != null and _active.playing else null
	var nxt := _music_b if old == _music else _music
	_active = null
	if _music_tween != null and _music_tween.is_valid():
		_music_tween.kill()
	_music_tween = create_tween().set_parallel(true)
	var s := _stream(id) if id != "" else null
	if s != null:
		if s is AudioStreamOggVorbis:
			(s as AudioStreamOggVorbis).loop = id != "bgm_end"
		nxt.stop()
		nxt.stream = s
		nxt.volume_db = -60.0
		nxt.play()
		_active = nxt
		_music_tween.tween_property(nxt, "volume_db", linear_to_db(volumes.music), seconds)
	elif old == null:
		nxt.stop()
	if old != null:
		_music_tween.tween_property(old, "volume_db", -60.0, seconds)
		_music_tween.chain().tween_callback(old.stop)


func stop_music() -> void:
	play_music("")
