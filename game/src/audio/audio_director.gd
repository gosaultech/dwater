# damned_waters/game/src/audio/audio_director.gd
# Purpose: all non-positional audio (autoload "AudioDirector").
#  * Every clip is loaded once at boot: playing a sound never touches disk.
#  * A small voice pool plays one-shots with slight pitch variation, so
#    repeated footsteps don't sound like a machine gun of identical samples.
#  * Ambience crossfades between rooms; each room sets the SFX reverb, so a
#    gunshot sounds different in the marble hall than in the brick cellar.
extends Node

const AUDIO_DIR := "res://assets/audio"
const VOICES := 10
const ROOM_ACOUSTICS := {  # room_size, damping, wet
	"gang": [0.75, 0.2, 0.28], "voorkamer": [0.45, 0.65, 0.14], "kelder": [0.85, 0.35, 0.34],
}

var _streams := {}
var _voices: Array[AudioStreamPlayer] = []
var _next_voice := 0
var _amb_a: AudioStreamPlayer
var _amb_b: AudioStreamPlayer
var _music: AudioStreamPlayer
var _reverb: AudioEffectReverb


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_setup_buses()
	var dir := DirAccess.open(AUDIO_DIR)
	if dir:
		for f in dir.get_files():
			var clean := f.trim_suffix(".import").trim_suffix(".remap")
			if clean.ends_with(".wav") and not _streams.has(clean.get_basename()):
				var s = load(AUDIO_DIR + "/" + clean)
				if s:
					_streams[clean.get_basename()] = s
	for i in VOICES:
		var p := AudioStreamPlayer.new()
		p.bus = "SFX"
		add_child(p)
		_voices.append(p)
	_amb_a = _player("Ambience")
	_amb_b = _player("Ambience")
	_music = _player("Music")


func _player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func _setup_buses() -> void:
	for bus in ["SFX", "Ambience", "Music"]:
		if AudioServer.get_bus_index(bus) == -1:
			AudioServer.add_bus()
			var i := AudioServer.bus_count - 1
			AudioServer.set_bus_name(i, bus)
			AudioServer.set_bus_send(i, "Master")
	_reverb = AudioEffectReverb.new()
	_reverb.predelay_msec = 25.0
	AudioServer.add_bus_effect(AudioServer.get_bus_index("SFX"), _reverb)
	var limiter := AudioEffectHardLimiter.new()
	AudioServer.add_bus_effect(AudioServer.get_bus_index("Master"), limiter)


func stream(sfx_name: String) -> AudioStream:
	return _streams.get(sfx_name)


func play(sfx_name: String, volume_db: float = 0.0, pitch_jitter: float = 0.0) -> void:
	var s: AudioStream = _streams.get(sfx_name)
	if s == null:
		return
	var p := _voices[_next_voice]
	_next_voice = (_next_voice + 1) % VOICES
	p.stream = s
	p.volume_db = volume_db
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	p.play()


func set_room(room_id: String, ambience: String) -> void:
	var ac: Array = ROOM_ACOUSTICS.get(room_id, [0.5, 0.5, 0.15])
	_reverb.room_size = ac[0]
	_reverb.damping = ac[1]
	_reverb.wet = ac[2]
	_reverb.dry = 1.0
	var next: AudioStream = _streams.get(ambience)
	if _amb_a.playing and _amb_a.stream == next:
		return
	var old := _amb_a
	_amb_a = _amb_b
	_amb_b = old
	var tw := create_tween().set_parallel()
	if next:
		_amb_a.stream = next
		_amb_a.volume_db = -40.0
		_amb_a.play()
		tw.tween_property(_amb_a, "volume_db", 0.0, 1.2)
	if _amb_b.playing:
		tw.tween_property(_amb_b, "volume_db", -40.0, 1.2)
		tw.chain().tween_callback(_amb_b.stop)


func play_music(track: String) -> void:
	var s: AudioStream = _streams.get(track)
	if s and _music.stream != s:
		_music.stream = s
		_music.volume_db = -6.0
		_music.play()


func stop_music(fade: float = 1.5) -> void:
	if _music.playing:
		var tw := create_tween()
		tw.tween_property(_music, "volume_db", -40.0, fade)
		tw.tween_callback(func(): _music.stop(); _music.stream = null)


func stop_ambience() -> void:
	_amb_a.stop()
	_amb_b.stop()
