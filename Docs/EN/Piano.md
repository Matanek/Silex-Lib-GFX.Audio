# Play a procedural piano

`Music.Instruments.piano()` creates a polyphonic piano without a sound bank.
Write the notes, choose the piano, then prepare and play the melody:

```sx
use GFX.Audio
use GFX.Audio.Music

func main() {
    var audio = Audio()
    var melody = try Music.Melody.create([
        Music.Note(key:Music.Key.C4, beats:0.5, velocity:0.4),
        Music.Note(key:Music.Key.E4, beats:0.5, velocity:0.7),
        Music.Note(key:Music.Key.G4, beats:1.0, velocity:1.0),
    ], tempo:110.0) else error { panic(error.detail) }
    var piano = try Music.Instruments.piano() else error { panic(error.detail) }
    let sound = try melody.prepare(audio, using:piano, tail_seconds:0.2) else error { panic(error.detail) }
    audio.wait(audio.play(sound))
    assert(audio.unload(sound))
}
```


[Listen to the range, settings and three velocities](../../Examples/Piano.sx):

```sh
silex run Packages/GFX.Audio/Examples/Piano.sx --release
```

Run from the SilexProject root. Preparation calculates the sound once; subsequent
plays reuse the Sound. Pass the piano to [Music.Player](MusicPlayer.md) with
`using:piano` for a MIDI score. The Silex-Examples MIDI player provides `--piano`.

## Choose the piano character

| Setting | Default | Meaning and range |
|---|---|---|
| `amplitude` | 0.2 | Maximum level of one voice before gain, 0..1 |
| `brightness` | 0.65 | Strike brightness, 0..1; velocity also modulates it |
| `decay_seconds` | 3 | Fundamental 60 dB decay time at A4, >0..30 s |
| `release_seconds` | 0.15 | Damping duration after key release, 0..5 s |
| `max_voices` | 16 | Capacity allocated at creation, 1..64 |
| `voice_policy` | `steal_oldest` | Replace the oldest start or `reject` |
| `steal_fade_seconds` | 0.001 | Voice replacement fade, 0..4,096 frames |
| `format` | 48 kHz mono | 1..192,000 Hz, 1..8 channels |

Seconds round to the nearest frame. Decay must occupy at least one frame; other
durations accept zero. The format must match preparation or the player.
Nonfinite or out-of-range settings return a failed `Result` before creation.

The sound decays even while the key remains pressed. Bass notes decay more
slowly, treble notes faster; upper partials fade earlier. A harder strike
increases level and enriches the spectrum. `brightness` changes color without
changing the notes. Every voice ends naturally after approximately 80 dB of
fundamental decay, including under sustain pedal.

[Instrument commands](Instruments.md) support chords, distinct note identities,
sustain, bend and gain ramps. The pedal delays damping of released keys; it does
not freeze their energy. `all_notes_off` damps all voices even under pedal.
`reset()` cuts voices immediately and keeps settings. Allow a tail at least as
long as release to avoid cutting it at the end of a melody or score.

## Model and resources

The model combines up to 24 slightly inharmonic partials per voice with a short,
deterministic strike transient. It fades partials near Nyquist and omits those
above it, including during bend. Channels receive the same signal; this model
does not produce an acoustic stereo image.

This first version provides a synthesized piano character. It does not simulate
all coupled strings, sympathetic resonance or the soundboard, and uses neither
recorded samples nor parameters fitted to a real piano. Listening remains
necessary to choose its musical use.

Voices, partial tables and scratch are prepared at creation. Commands and
rendering do not grow collections; cost depends on occupied voices, partials and
channels. The 64-voice capacity bounds storage; it does not guarantee load on
every device. Sine resource measurements do not measure piano load.

For direct frame programming, `Synthesis.PianoInstrument.create` accepts the
same model with `decay_frames` (default 144,000), `release_frames` (7,200) and
`steal_fade_frames` (48), corresponding to the default durations at 48 kHz.
These frame defaults do not change with sample rate. Commands, rendering,
`active_voices()` and reset follow the Instrument protocol.

[Choose a timbre or instrument](Music.md) · [Play a MIDI score](MusicPlayer.md)
