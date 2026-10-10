# Prepare and play a melody

Describe a few notes, choose a timbre or instrument and prepare a reusable sound.
`GFX.Audio.Music` owns the buffers, time conversions and rendering; no sound
bank is required. Use the local toolchain containing optional conversions and
shared named argument contexts until they are published.

```sx
use GFX.Audio
use GFX.Audio.Music

func main() {
    var audio = Audio()
    var melody = try Music.Melody.create([
        Music.Note(key:Music.Key.C5, beats:0.5), Music.Note(key:Music.Key.E5, beats:0.5),
        Music.Note(key:Music.Key.G5, beats:0.5), Music.Note(key:Music.Key.C6, beats:1.25),
    ], tempo:187.5) else error { panic(error.detail) }
    let victory = try melody.prepare(audio) else error { panic(error.detail) }
    audio.wait(audio.play(victory))
}
```

C5–E5–G5–C6: three 160 ms slots followed by a 400 ms slot, with 80% gate
and a 30 ms retro release. Prepare at game loading time; each subsequent
`audio.play(victory)` starts an independent playback without recalculating
the melody. `audio.wait` is only for this standalone demonstration; a game
continues its loop after `play`.

## Write notes by name

`Music.Key.C5`, `Cs5` and `Bb4` are `int` constants, usable directly as `key`.
The `s` suffix means sharp, and `b` means flat; `Cs5` and `Db5` produce the same
number. The convention is **C4 = 60**, C5 = 72 and A4 = 69. Constants remain
within 0..127; `CMinus1` names C-1 (0), and `G9` is 127. Accidentals may cross
octave boundaries: `Bs3` equals `C4`.

For a list of constants, the current compiler requires the `int[]` annotation:

```sx
let notes:int[] = [Music.Key.C5, Music.Key.E5, Music.Key.G5, Music.Key.C6]
```

For known names, use direct conversions inside `main()`:

```sx
let sharp = Music.key("D#3") // 51
let flat = Music.key("Bb4")  // 70
let notes = Music.keys(["C5", "E5", "G5", "C6"])
```

Text names accept A through G, an optional ASCII `#` or `b` accidental, then a
single-digit octave, optionally negative. The note letter may be lowercase;
spaces, double accidentals and Unicode symbols are not accepted. The resulting
pitch must remain within 0..127: C-1 and B#-2 are 0, while Cb-1 and G#9 are
rejected. Tuning is unchanged.

An ordinary call to `key` yields `int`, and to `keys` yields `int[]`. Invalid
input triggers `panic`. For entered or loaded names, add `try` to the same
call and inspect the `Result`:

```sx
let candidate = (try Music.key("C#5")) // Result<int, Error>
match candidate {
    success(number) => { print(number) }
    failure(error) => { print(error.detail) }
}
let notes = try Music.keys(["C5", "E5", "G5", "C6"]) else error { panic(error.detail) }
```

`key` returns `Result<int, Error>` and `keys` returns `Result<int[], Error>`.
Errors preserve `invalid_input`, operation `audio.music.key` and the name in
`subject`. Both list conversions preserve order and duplicates and accept an
empty list; the recoverable variant returns no partial result. These conversions
happen when describing notes, outside DSP rendering. MIDI numbers remain directly usable.

In a recoverable function, previous propagation becomes explicit:
`try Music.key(name) else error { return Result<int, Error>.failure(error) }`.
Without an `else` block, `try Music.key(name)` now keeps the result.

## Change the sound

Fragment using `audio` and `melody` from above:

```sx
var timbre = Music.Timbre.soft()
timbre.release_seconds = 0.15
timbre.amplitude = 0.16
let softer = try melody.prepare(audio, using:timbre) else error { panic(error.detail) }
```

The three starting points are `retro()` (square, 8 bits, 125 µs sample hold),
`soft()` (triangle, 10 ms attack) and `sine()` (sine). Their mutable fields
are `waveform`, `amplitude`, `duty_cycle`, `attack_seconds`, `decay_seconds`,
`sustain`, `release_seconds`, `bits` and `hold_seconds`. Waveforms and ADSR
follow the [synthesis primitives](Synthesis.md). The square uses the package's
bounded harmonics; sample hold and quantization precede the envelope, which
preserves the silent onset and release.

These are subjective sound choices without guaranteed acoustic imitation.
Changing a timbre and preparing it creates a new Sound; earlier sounds and
playbacks retain their PCM. Melody owns a copy of the notes and tempo;
changing the original list does not change the melody.

A timbre is a sound recipe; it receives no commands and keeps no active voices.
Preparation produces each note and sums its tails. Timbre presets therefore
do not constitute an instrument catalogue.

## Choose an integrated instrument

Fragment using `audio` and `melody` from above:

```sx
var instrument = try Music.Instruments.sine(amplitude:0.16,
    attack_seconds:0.003, decay_seconds:0.03, sustain:0.35, release_seconds:0.1)
    else error { panic(error.detail) }
let tone = try melody.prepare(audio, using:instrument, tail_seconds:0.1)
    else error { panic(error.detail) }
audio.wait(audio.play(tone))
```

`Music.Instruments.sine` creates the package's actual polyphonic
`Synthesis.SineInstrument`. The instrument receives musical commands and owns
its voices. This entry accepts durations in seconds and defaults to mono at
48 kHz, amplitude 0.2, a 5 ms attack, 50 ms decay, sustain 0.7, a 100 ms release
and 16 voices. `max_voices` accepts 1..64; `voice_policy` chooses rejection or
oldest-voice reassignment, with reassignment as the default.
`steal_fade_seconds` defaults to 1 ms and is limited to 4,096 frames in the
selected format. Per-voice amplitude remains separate from velocity and the
controllable gain; reset preserves it. Durations round to the nearest frame,
and each ADSR stage is limited to 16,777,216 frames. Invalid settings return
a `Result`.

[Note, sustain, pitch bend and gain commands](Instruments.md) remain available
on this instrument. A prepared melody freezes their result; changing or
commanding the instrument afterwards does not change the prepared Sound.
The format selected at creation must match `prepare`'s format.
The sine serves simple tones and alerts. [Music.Instruments.piano](Piano.md)
adds a procedural piano with strike dynamics and natural decay.
Retro timbres remain directly usable for short effects and music.

## Bring an instrument and effects

[MusicalSounds.sx](../../Examples/MusicalSounds.sx) plays the retro victory, a customized
timbre, the integrated instrument and an application instrument conforming to the existing
`Synthesis.Instrument` protocol. From SilexProject:

```sh
silex run Packages/GFX.Audio/Examples/MusicalSounds.sx --release
```

The same `melody.prepare(audio, using:instrument, tail_seconds:0.1)` operation
creates the events and renders the instrument. `effects:[myEffect]` adds
up to 32 `Processing.Processor` treatments, in the specified order, after
summing the notes. They share the requested format. Choose their tail with
`tail_seconds`; the package does not guess a user effect's duration.

Preparation resets the selected instrument and effects, then consumes their
state. A class remains shared with its other holders; use a dedicated instance
on the application thread. A rendering error may leave those objects changed:
reset or reconstruct them before retrying. The [advanced primitives](Instruments.md)
remain available.

## Rhythm, duration and limits

`Music.Note` accepts `key` (MIDI number 0..127), positive `beats`, `velocity`
in 0..1 (default 1), and `gate` in (0, 1] (default 0.8). The next note starts
after `beats`; `gate` specifies the held fraction. Release tails may overlap.
`Melody.create` accepts 1..4,096 notes and a finite positive `tempo`, defaulting
to 120 BPM. Absolute positions are rounded to the nearest frame; the held
fraction must occupy at least one frame. Tempo is independent of application
update frequency.

`prepare` produces mono at 48 kHz by default. `format:Processing.Format(...)`
allows 1..192,000 Hz and 1..8 channels. A selected instrument must have that format.
The built-in timbre sends the same signal to each channel; notes at or above
Nyquist are rejected.

Sound duration is the musical duration plus `tail_seconds`. Without that
argument, the tail is the built-in timbre's release or 100 ms for a selected
instrument, including the integrated sine instrument. An explicitly shorter tail cuts release; a longer tail lets
effects finish, then adds silence. `max_seconds` limits music plus tail to
30 s by default, replaceable within (0, 300]. Output is also limited to
16,777,216 samples. These limits protect short-sound preparation, which
materializes the PCM.

Description, setting, format and level errors return `Result`; note, duration
and storage limits use `limit_exceeded`. The mix is neither normalized nor
clipped: nonfinite samples or levels outside ±1 are rejected before `Audio.create`.
Reduce the level or choose a [limiter](Dynamics.md). Native `Audio.create`
failures keep that operation's existing contract.

Preparation allocates PCM and working states, then Audio retains its copy;
these costs belong to loading, not each playback trigger. The built-in timbre
uses a 512-frame scratch buffer, while the full output remains in memory.
`audio.unload(sound)` releases the reusable sound; already started playbacks
may finish. `audio.release(playing)` releases a playback. All these handles
belong to their Audio instance.

The [MIDI player](MusicPlayer.md) owns continuous feeding and playback controls.
The [advanced path](MIDI.md) retains channel/program routing.
[Musical resource costs](MusicResources.md) distinguish preparation, triggering
and continuous production.

[Play a score with a player and playback controls](MusicPlayer.md).

[Play guitar, violin and drums](Catalogue.md), with built-in instruments and audible examples.
