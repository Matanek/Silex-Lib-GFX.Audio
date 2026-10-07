# Choose a procedural recipe

To make a game or application sound, start with a source, control its duration
and level, then add processors expressing the intended result. The package
provides building blocks; the application owns its recipes, seeds and parameters.

[Version française](../FR/Recipes.md).

## From beeps to music

| Intent | Sources and composition | Guide and executable source |
| --- | --- | --- |
| Beep, impact, laser | Oscillator, white noise, filter, ADSR or frequency curve. | [Synthesis](Synthesis.md), [ProceduralSounds.sx](../ProceduralSounds.sx) |
| Explosion, ambience | Filtered noise, bass and envelope; mix multiple generators. | [Composition](Composition.md), [ModulatedSounds.sx](../ModulatedSounds.sx) |
| Changing engine | FM, harmonic and pink noise; smoothed commands on the frame timeline. | [Continuous production](Continuous.md), [ContinuousSounds.sx](../ContinuousSounds.sx) |
| Retro texture | Square wave, quantization and sample hold. | [Bitcrusher](Bitcrusher.md), [RetroSounds.sx](../RetroSounds.sx) |
| Direct melody | Polyphonic instrument and sequence of frame-timed commands. | [Instruments](Instruments.md), [PolyphonicMelody.sx](../PolyphonicMelody.sx) |
| MIDI score | Parse a score and supply instruments through explicit bindings. | [MIDI](MIDI.md), [MIDIMelody.sx](../MIDIMelody.sx) |

Run executable sources from `SilexProject/`, for example
`silex run Packages/GFX.Audio/Docs/MIDIMelody.sx --release`. The consolidated
demonstration belongs to `Silex-Examples/Sources/ProceduralAudio/Main.sx`; its
compiled executable provides `--case beep|impact|laser|explosion|engine|retro|melody|midi`
and `--check`. Its bilingual guide explains parameters and variations. These
paths require the Spec’s local candidates until they are delivered.

## Control duration, rhythm and level

A frame contains one sample per channel. At 48,000 frames/s, 240 frames equal
5 ms; a stereo block of 480 frames contains 960 values. Musical commands and
engine changes follow this clock without waiting for an application timer.
At 120 BPM, a beat spans 24,000 frames. The MIDI player converts score tempos
onto the same timeline.

Provide attack and release at sound boundaries. An effect such as a delay or
reverb can continue after the last note: render enough frames for its tail
before closing the stream. For a MIDI gain or pan command,
`controller_ramp_frames` enables optional smoothing.

Gains are linear; oscillators and filters use hertz. A mix adds its sources;
measure levels and reduce gains when necessary, or choose a [limiter](Dynamics.md).
The bitcrusher intentionally degrades the signal; at 48,000 frames/s,
`hold_frames:6` gives a sample hold equivalent to an effective rate of 8,000 Hz.
Fixed noise seeds and `reset` let you compare variants exactly.

## Extend your compositions

`Synthesis.Generator`, `Processing.Processor` and `Synthesis.Instrument` are
extension contracts. An application can implement its own sources, effects
and instruments; public compositions accept them. [Processing](Processing.md)
and [composition](Composition.md) describe formats, block views and state
preserved between calls.

For a short reusable sound, render samples and call `Audio.create`. For
continuous output, prepare `Synthesis.StreamProducer`, prefill and handle
partial writes before closing input. [In-memory output](Offline.md) can verify
the same render without a device. Listening judges timbre; PCM comparisons
verify reproducibility. These building blocks provide neither sample banks,
a VST host nor automatic humanization.
