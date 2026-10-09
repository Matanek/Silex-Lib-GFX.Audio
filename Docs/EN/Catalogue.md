# Play guitar, violin and drums

Choose `Music.Instruments.guitar()`, `violin()` or `drums()`, then pass the
instrument to `using:` in a melody or [MIDI player](MusicPlayer.md). All three
produce sound without audio files. The [piano](Piano.md) and
[sine instrument](Instruments.md) remain available.

## Prepare a guitar melody

Pluck position changes the color; near the middle of the string, some harmonics
disappear. Notes decay naturally even while held. This example prepares a
reusable melody:

```sx
use GFX.Audio
use GFX.Audio.Music

func main() {
    var audio = Audio()
    var guitar = try Music.Instruments.guitar(pluck_position:0.18) else error { panic(error.detail) }
    var melody = try Music.Melody.create([
        Music.Note(key:Music.Key.G3, beats:0.5),
        Music.Note(key:Music.Key.B3, beats:0.5),
        Music.Note(key:Music.Key.D4, beats:1.0),
    ], tempo:120.0) else error { panic(error.detail) }
    let sound = try melody.prepare(audio, using:guitar, tail_seconds:0.15) else error { panic(error.detail) }
    audio.wait(audio.play(sound)); assert(audio.unload(sound))
}
```

Replace the creation of `guitar` with `Music.Instruments.violin()` for notes
maintained until release. `brightness` shapes the color and velocity changes
both intensity and spectrum. The violin has a soft attack and adjustable vibrato.
Polyphony allows several notes; this is a violin model without an automatic
ensemble layer.

## Write a drum part

`Music.Drum` provides numbers usable directly as `Music.Note.key`.
The kit contains seven sounds with General MIDI percussion map numbers:

| Key | MIDI number | Sound |
| --- | --- | --- |
| `Music.Drum.kick` | 36 | Bass drum |
| `Music.Drum.snare` | 38 | Acoustic snare |
| `Music.Drum.closed_hat` | 42 | Closed hi-hat |
| `Music.Drum.open_hat` | 46 | Open hi-hat |
| `Music.Drum.low_tom` | 45 | Low tom |
| `Music.Drum.high_tom` | 50 | High tom |
| `Music.Drum.crash` | 49 | Crash cymbal |

The [drum example](../../Examples/Drums.sx) plays a pattern, then the seven sounds
separately. The kick quickly drops in pitch, toms have inharmonic modes, the
snare adds noise and cymbals use a high-frequency texture. All strikes decay
naturally. `decay_seconds` scales their relative duration: at 0.6, the 60 dB
decay is 0.45 s for kick, 0.25 s for snare, 0.08/0.5 s for the hats,
0.6/0.45 s for the toms and 1.5 s for crash. Higher modes decay faster.

As with the other instruments, `note_off` damps a note over `release_seconds`;
a very short note cuts a long resonance. Increase `beats`/`gate` to hear the
natural tail. Sustain delays damping. Hats occupy independent voices, without
automatic choking.

For direct commands, `note_on` takes the MIDI key frequency obtained with
`MIDI.frequency(Music.Drum.kick)`. The kit recognizes its seven keys within
0.1 % relative tolerance and selects a percussion model; the selector frequency
is not the audible resonator pitch. Bend changes tonal resonances, not noise.
Other keys return `invalid_input`, including in `Melody.prepare` and MIDI
rendering. Select the kit explicitly for percussion channels through
[MIDI bindings](MIDI.md); there is no automatic channel/program selection.
This subset is not a complete General MIDI bank.

## Adjust instruments

| Setting | Guitar | Violin | Drums |
| --- | --- | --- | --- |
| `amplitude` / `brightness` | 0.2 / 0.65 | 0.2 / 0.65 | 0.2 / 0.65 |
| `pluck_position` | 0.18, in [0.05, 0.95] | — | — |
| `decay_seconds` | 2.0, in (0, 30] | — | 0.6, in (0, 5] |
| `attack_seconds` | Fixed 3 ms attack | 0.05, in [0, 5] | Fixed 1 ms attack |
| `release_seconds` | 0.08 | 0.2 | 0.04 |
| `vibrato_cents` / `vibrato_hz` | — | 12 / 5.5, in [0, 50] / [0, 12] | — |

Amplitude and brightness must be finite in [0, 1]; release is in [0, 5] seconds.
Use `vibrato_cents:0.0` to disable vibrato. Durations round to frames; a decay
rounded to zero is rejected. Guitar decay varies with register between 0.5 and
1.5 times its configured value. Guitar/drums free their voice after a nominal
80 dB decay, even with sustain. Violin keeps it until release or voice stealing.

Each factory accepts `max_voices` (default 16, 1..64), `voice_policy` (default
`steal_oldest` or `reject`), `steal_fade_seconds` (default 1 ms, 0..4096 frames)
and `format` (default 48 kHz mono, 1..8 channels). Rate is 1..192000 Hz for strings
and 512..192000 Hz for drums. A `note_on` must remain positive and below Nyquist,
including after bend. Channels receive identical signals; summed voices may
exceed a single voice's amplitude, so adjust gain for simultaneous notes.

Returned objects are `Synthesis.GuitarInstrument`, `ViolinInstrument` and
`DrumsInstrument`, implementing `Instrument` and `Generator`. Their
`create(format, ...)` factories expose the same settings with frame durations
(`attack_frames`, `decay_frames`, `release_frames`, `steal_fade_frames`). Frame
defaults correspond to 48 kHz. [Common commands](Instruments.md), identities,
ramps, reset and reject/steal rules are preserved. `active_voices()` counts
occupied voices.

## Listen and qualify

From `SilexProject` root with the local package linked:

```sh
silex run Packages/GFX.Audio/Examples/Guitar.sx --release
silex run Packages/GFX.Audio/Examples/Violin.sx --release
silex run Packages/GFX.Audio/Examples/Drums.sx --release
```

Strings compare two settings on the same melody; drums demonstrate every kit
piece. Rendering is modal: 32 harmonics for strings, 8 modes and deterministic
noise for percussion. Modes near Nyquist are faded and omitted above it. These
stylized syntheses include neither recordings, coupled strings nor a nonlinear
physical bow/string interaction.

[Numerical oracles](../../Tests/Consumer/Tests/Catalogue.sx) and the
[resource counter](../../Tests/Resources/ValidateCatalogue.py) verify behavior
and no measured allocation/copy on the calling thread during commands, rendering
and reset in ARM64 Debug/Release. Preparation allocates bounded tables and pool.
Dummy drivers allow playback tests, but human listening is still needed to
assess the result.
