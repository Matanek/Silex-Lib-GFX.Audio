# Generate a sound without an audio file

`GFX.Audio.Synthesis` generates a sine wave with `Oscillator`, reproducible
white noise with `WhiteNoise`, and an ADSR envelope with `Envelope`.
The [ProceduralSounds.sx program](../ProceduralSounds.sx) produces a beep,
then an impact combining a bass tone and filtered noise, without a sound bank
or audio asset.

From the workspace root, with Silex 0.47.1 or newer:

```sh
silex run Packages/GFX.Audio/Docs/ProceduralSounds.sx --release
```

## Generate and play

A generator writes into an already sized buffer. This program produces a
quarter-second sine wave at a low level, then uses ordinary Audio playback:

```sx
use GFX.Audio
use GFX.Audio.Processing
use GFX.Audio.Synthesis

func main() {
    let format = Processing.Format(sample_rate:48_000, channels:1)
    match Synthesis.Oscillator.create(format, frequency_hz:440.0, amplitude:0.1) {
        failure(error) => { panic(error.detail) }
        success(var source) => {
            var samples:float32[] = []
            var frame = 0
            while frame < 12_000 { samples.append(0.0); frame++ }
            match source.render(&samples[0:samples.count()]) {
                failure(error) => { panic(error.detail) }; success => {}
            }
            var audio = Audio()
            let sound = audio.create(@samples[0:samples.count()], sample_rate:48_000)
            let playing = audio.play(sound)
            audio.wait(playing)
        }
    }
}
```

The generator overwrites the view, preserves its phase between calls, and does
not retain the view. The same buffer can be reused for several blocks. An empty
view does not advance state; an incomplete frame is rejected before mutation.
Channels are interleaved; these mono sources duplicate the same value in each
channel of the format. Rendering needs no device: its values can also feed
analysis, a stream, or an in-memory mix.

`Generator` requires `format`, `render(samples:&float32[..])`, and `reset()`.
A user class can conform without Interop. A dynamic protocol preserves class
identity: use two instances for independent states. Calls remain sequential
on the application thread.

## Configure sources

`Oscillator.create(format, frequency_hz:440.0, amplitude:1.0, phase:0.0)`
returns a `Result<Oscillator, Error>`. Initial phase counts cycles in `[0, 1)`.
Frequency is finite, nonnegative, and strictly below Nyquist; its step must
remain representable. Zero frequency holds the value at the chosen phase.
Amplitude is finite and between 0 and 1.

`set_frequency` preserves phase; `set_amplitude` changes the level without
automatic smoothing. `reset` returns to the initial phase and retains current
settings. This initial capability produces sine waves; other waveforms are
not yet available.

`WhiteNoise.create(format, seed:42, amplitude:1.0)` returns a
`Result<WhiteNoise, Error>`. The same seed and commands produce the same sequence;
`reset` restarts it while retaining the current amplitude. All signed integers
are accepted. Seeds are normalized into a finite state; distinct seeds may
produce the same sequence. `set_amplitude` accepts the oscillator's range.
This noise is intended for sound production, not cryptography.

Calculations and phases use float32, like Processing PCM. The format's sample
rate ranges from 1 to 16,777,216 Hz and its channel count from 1 to 8; the rate
bound ensures the integer is exactly representable in this calculation path.
Very low frequencies remain subject to float32 phase resolution.

## Shape attack and release

`Envelope.create(format, attack_frames:240, decay_frames:2_400, sustain:0.5,
release_frames:4_800)` returns a `Result<Envelope, Error>`.
Durations count frames regardless of channel count: 240 frames at 48 kHz are
5 ms. Each duration ranges from 0 to 16,777,216 frames; sustain is a finite
level in `[0, 1]`.

The envelope starts inactive. `note_on()` restarts from zero, rises linearly
to 1, decays to sustain, and holds until `note_off()`. Release starts from the
current level, even during attack or decay. A second note-off during release
does not restart it. Zero duration immediately crosses its stage. Each frame
uses the current level, then advances state: a two-frame attack produces
`0, 0.5`, followed by the peak `1`.

`process(&samples[...])` multiplies block values and satisfies the
`Processing.Processor` protocol. Explicitly apply the source, envelope, then
filter or delay according to the desired timbre. Processing accepts finite
values beyond ±1 without normalization; envelope gain stays between 0 and 1.
Invalid values are rejected before buffer or state mutation. `is_active()`
remains true until release ends, including with zero sustain; `reset()` returns
to inactive silence. Retriggering and abrupt setting changes can introduce a
discontinuity: no smoothing is implicit.

## Use blocks and understand limits

Whole and split renders preserve state within 10⁻⁶ absolute error on the
qualified fixtures. Generation does not resize the buffer or create an output
per frame; hidden runtime allocations and real-time load have not yet been
measured for this capability. No Silex callback runs on the audio thread.

Invalid creation or settings return `invalid_input`, with operation
`audio.synthesis`. Failed settings preserve the previous state. Generators are
continuous sources; choose the render duration explicitly or close the stream
after the desired blocks. Partial queues follow the
[streaming contract](Streaming.md).

[Process blocks](Processing.md) · [Render a mix in memory](Offline.md) ·
[Return to the Audio guide](README.md)
