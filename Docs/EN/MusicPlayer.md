# Play a score and control its playback

`Music.Player` plays a MIDI score with a selected timbre, instrument, or routing.
It owns audio production and feeding; the application writes no sample loop.
This complete standalone program keeps [its score](../MusicScore.mid) beside
the `.sx` file:

```sx
use GFX.Audio
use GFX.Audio.Music
use GFX.Audio.MIDI

func main() {
    var audio = Audio()
    let bytes = embed_bytes("MusicScore.mid")
    var score = try MIDI.Score.parse(@bytes[0:bytes.count()], 48_000) else error { panic(error.detail) }
    var timbre = Music.Timbre.retro(); timbre.amplitude = 0.10
    var player = try Music.Player.create(audio, score, using:timbre) else error { panic(error.detail) }
    let playing = try player.play() else error { panic(error.detail) }
    try player.wait() else error { panic(error.detail) }
    print("Finished; ignored messages: ", player.ignored_messages())
}
```

`wait()` feeds active Audio players until this playback finishes. It deliberately
blocks the standalone program. In a game, use the Audio plugin and keep the
application loop running; do not call `wait()` from a system. The
[interactive example](https://github.com/Matanek/Silex-Examples/tree/main/Sources/MIDIPlayer)
shows both modes, a customized retro timbre, and an integrated sine instrument.
The example preserves tempo changes; its retro mode counts eight unapplied
program or controller messages.

## Choose the sound and its interpretation

`using:` accepts a `Music.Timbre`, an integrated or application
`Synthesis.Instrument`, or an already routed `MIDI.Synthesizer`.
To select the integrated instrument, replace timbre creation with this fragment:

```sx
var instrument = try Music.Instruments.sine(amplitude:0.16,
    release_seconds:0.15) else error { panic(error.detail) }
var player = try Music.Player.create(audio, score, using:instrument) else error { panic(error.detail) }
```

Simple mode merges notes from all sixteen channels into the selected sound.
Note-off retains its original channel, pitch, and FIFO order, so two channels
playing the same pitch release correctly. Velocity is preserved. Programs,
bend, pressure, and controllers are ignored and counted by `ignored_messages()`,
except All Notes Off (CC123), which releases that channel's notes.
This choice does not reproduce the original orchestration or General MIDI drums.
The timbre realization has sixteen voices, replacing the oldest with a 1 ms
transition; an instrument keeps its own voice capacity and policy.

To preserve per-channel programs, sustain, volume, expression, pan, and bend,
supply a [routed synthesizer](MIDI.md). Each binding requires a distinct
instrument. Every encountered channel/program must have a binding; a missing
binding becomes a recoverable player error.

`effects:` accepts up to 32 processors matching the source format.
Instruments and processors belong exclusively to one playback: creation and
replay reset them. Two independent players require two sets of state; sharing
the score is supported.

Simple mode tracks up to 256 held notes; exceeding that limit is recoverable.

## Integrate with a game

Prepare Audio and the player while configuring the application, then supply
that Audio through `application.add_resource(audio)`. The Audio plugin preserves
this instance and creates one only when none was supplied. Systems borrow the
player to call `play()`, `pause()`, `resume()`, `stop()`, and `replay()`.
The plugin feeds streams during `post_update`, including when ordinary application
processing is suspended. Commands and synthesis run on the application thread.
No Silex callback runs on the native audio thread. An Audio reference borrowed
by a system must not escape: create the player from its owner during setup.

`state()` returns `ready`, `playing`, `paused`, `finished`, `stopped`, or `failed`.
`position_seconds()` follows consumed frames rather than frames produced ahead.
`error()` exposes source or transfer failure; such a failure stops the stream.
`is_starved()` reports an empty open queue: progress the application more
regularly or adjust the advanced capacity. Event counters describe production
ahead, not notification of the audible instant.

## Completion, ownership, and limits

Score completion releases notes once, then the player renders its tail.
`tail_seconds:` defaults to the timbre release or 0.2 seconds for an instrument
or routing; select a longer tail for prolonged releases or effects.
The tail is finite, from 0 to 60 seconds, and does not detect silence automatically.
A zero tail can cut a note still held at the end of the file.

`play()` starts once; `replay()` replaces the stream and resets musical state
from an active, stopped, or finished playback. Pause preserves prepared PCM;
stop discards it and suspends production. Dropping the player releases its
stream; the player retains Audio until it is dropped. The Audio handles returned
by play/replay support existing groups, levels, and notifications, and become
stale when their stream is replaced or released.

Continuous PCM is bounded by one queue of `capacity_frames:4800` and one block
of `block_frames:512` per player. Score metadata and instrument/effect state
occupy separate memory; the song is not prerendered. Starting produces at most
the capacity plus a pending block; native transfers retain their known allocations.
Advanced sizes use Audio stream capacity limits and 1..65536 block frames.
Very small capacities can starve native conversion when changing sample rate or
speed: the same-rate test covers three-frame queues, while the speed test uses
normal capacity. Capacity covers 100 ms at 48 kHz and speed 1; it does not
ensure uninterrupted playback if the game stalls longer.

`Audio.offline.render()` also owns feeding and supports deterministic export.
`wait()` rejects offline and paused playback with `resource_busy`; use render
for the former and resume for the latter. Score, format, capacity, configuration,
and output outside `[-1,1]` errors remain recoverable. No hidden clipping is
added: reduce amplitude or choose a limiter.

[Choose musical playback costs](MusicResources.md).
