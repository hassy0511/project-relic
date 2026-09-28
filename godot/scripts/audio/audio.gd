class_name GameAudio
extends Node
## 効果音と BGM。音はすべて ID で呼び、ファイル（assets/audio/<ID>.ogg）の差し替えだけで音を変えられる。
## 位置つきの音は、カメラ（聞き手）との距離で大きさと左右が変わる。

var _streams := {}
var _last := {}
var _music: AudioStreamPlayer
var _pool: Array[AudioStreamPlayer3D] = []
var _ui_pool: Array[AudioStreamPlayer] = []
var volumes := {"master": 0.8, "music": 0.5, "sfx": 0.8}


func _ready() -> void:
	_music = AudioStreamPlayer.new()
	_music.volume_db = linear_to_db(volumes.music)
	add_child(_music)
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


func play_music(id: String) -> void:
	var s := _stream(id)
	if s == null:
		return
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	_music.stream = s
	_music.play()


func stop_music() -> void:
	_music.stop()
