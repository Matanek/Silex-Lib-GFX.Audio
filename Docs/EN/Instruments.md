# Play a polyphonic melody

`Synthesis.SineInstrument` plays sine notes with velocity, an ADSR envelope,
sustain and pitch bend. `Synthesis.Sequence` places their commands on the audio
clock and provides a `Generator`, composable with the existing effects.
No sound bank or MIDI input is required.

[PolyphonicMelody.sx](../PolyphonicMelody.sx) plays four bars at 120 BPM:
chords, repeated notes with distinct identities, a pedal in the second bar
and a pitch change in the fourth. Accents are written into the score.
A second pass limits the same piece to two voices to hear stealing with the
default connection. From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Docs/PolyphonicMelody.sx --release
```

Fragment with a mono 48 kHz `format`, a prepared `samples` buffer of 48,000
samples, and a `require(Result<void, Error>)` helper that handles errors:

```sx
match Synthesis.SineInstrument.create(format, max_voices:8) {
    failure(error) => { panic(error.detail) }
    success(var instrument) => {
        let events:Synthesis.Event[] = [
            Synthesis.Event(frame:0, command:Synthesis.Command.note_on(1, 261.6256, 0.4)),
            Synthesis.Event(frame:0, command:Synthesis.Command.note_on(2, 329.6276, 0.3)),
            Synthesis.Event(frame:24_000, command:Synthesis.Command.all_notes_off),
        ]
        match Synthesis.Sequence.create(instrument, events) {
            failure(error) => { panic(error.detail) }
            success(var source) => {
                require(source.render(&samples[0:samples.count()]))
            }
        }
    }
}
```

Explicitly attenuate the sum before `Audio.create`, or compose with a
[limiter](Dynamics.md). Voices add without hidden normalization;
16 voices at velocity 1 can exceed the audible `[-1, 1]` range.

## Send note commands

`instrument.send(command)` applies a command between renders. For placement
inside a block, use a sequence `Event`. Each operation returns
`Result<void, Error>`.

| Command | Values and behavior |
|---|---|
| `Command.note_on(id, frequency_hz, velocity)` | Integer identity ≥ 0, positive float32 frequency below Nyquist, float32 velocity in 0..1. A new voice starts at phase zero and triggers the ADSR. |
| `Command.note_off(id)` | Releases this identity; an absent identity does nothing. Under the pedal, the voice waits for pedal release. |
| `Command.sustain(down)` | `true` retains released keys; `false` enters release for them without releasing keys still held down. |
| `Command.pitch_bend(semitones)` | Finite float32 in −24..24, shared by current and future voices. Preserves phase. Rejects the entire change if an occupied voice leaves the frequency range. |
| `Command.all_notes_off` | Releases every voice, even under the pedal, using its release duration. |

Two notes at the same pitch use different identities. An occupied identity,
including its release, rejects a new `note_on`. Once silent, it can be reused.
A stolen voice's `note_off` does not release the new identity. Zero velocity
occupies a silent voice; the instrument does not apply the MIDI convention
“zero note-on = note-off”.

`reset()` immediately cuts voices and fades, resets pedal, bend and counter,
restores global gain to 1, and keeps the configuration. `active_voices()` counts occupied slots,
including releases and fades. No random change or humanization is applied.

## Set polyphony and envelope

`SineInstrument.create(format, ...)` accepts 1..8 channels and an integer rate
of 1..16,777,216 Hz. The mono sine is sent identically to every channel.
Frequency divided by sample rate must remain positive in float32, including
after bend; the upper limit is strictly Nyquist.

| Setting | Default | Range |
|---|---|---|
| `max_voices` | 16 | 1..64, allocated at creation |
| `voice_policy` | `VoicePolicy.steal_oldest` | `steal_oldest` or `reject` |
| `attack_frames` | 240 | 0..16,777,216 |
| `decay_frames` | 2,400 | 0..16,777,216 |
| `sustain` | 0.7 | Finite float32, 0..1 |
| `release_frames` | 4,800 | 0..16,777,216 |
| `steal_fade_frames` | 32 | 0..4,096 |

Durations use frames, with the [envelope semantics](Synthesis.md). Defaults
correspond to 5 ms attack, 50 ms decay and 100 ms release at 48 kHz;
they do not automatically change with sample rate.

The first free slot is used. At full capacity, `reject` returns `limit_exceeded`
without changing voices; `steal_oldest` replaces the earliest start,
including a voice in release. With a nonzero fade, the replaced voice starts
exactly at its last emitted sample, then blends that held level with the new
note over the chosen duration. This short connection avoids a jump at the
first sample; it does not keep an additional voice. Zero cuts directly.
Another steal during the fade starts from the last blended sample.
Simple `pitch_bend` is immediate. [Continuous ramps](Continuous.md) add
`pitch_bend_to` and `gain_to` without restarting voices.

## Place commands on the audio clock

`Sequence.create(instrument, events, capacity:4_096)` retains its score.
Capacity is 1..65,536 events. `schedule(event)` adds a command after the last
scheduled position or at the same time, within this capacity. Executed events
remain for replay after `reset()`. Prepare additions before rendering:
their storage may allocate.

`Event.frame` positions are integers in 0..9,223,372,036,854,775,807.
`rendered_frames()` gives the next frame to produce. Events must be chronological;
those at the same time follow insertion order. An event at the exact end of
a block applies before the first sample of the next nonempty block. An empty
block consumes no commands. A late command or an addition before the last
scheduled position is rejected, without catch-up or silent relocation.

`Synthesis.frame_at(seconds:float64, sample_rate:int)` converts a finite,
nonnegative absolute time, rounded to the nearest frame; a half-frame goes
to the next frame. The result is limited to 2⁵³−1 to retain float64 integer
precision. Use frames directly for large positions. At 48 kHz and 120 BPM,
a beat is exactly 24,000 frames. Placing each event from the origin avoids
accumulating rounding; rendering advances this clock without a UI delta
or an application timer.

## Compose and develop an instrument

A user type conforming to `Synthesis.Instrument` supplies `format`,
`validate(command)`, `send(command)`, `render(samples)` and `reset()`.
`validate` checks values without changing state; `send` also checks constraints
that depend on current notes. `render` writes all requested interleaved frames,
keeps its state across blocks and accepts an empty block. `Sequence` uses this
interface without knowing the instrument's timbre. It can then enter
`Processed`, `Mix` or modulation like any `Generator`. An instrument directly
usable as a generator also declares its nominal `Generator` conformance.

A class keeps its shared identity; a struct instrument is copied when erased
into a protocol. The sequence owns its events and retains its instrument.
Operate the whole on one thread; another sequence or a direct call on the same
class shares its state. Resetting the sequence resets that instrument and
replays the full score.

Invalid commands return `invalid_input` (`audio.synthesis`), saturated capacities
return `limit_exceeded`. Incomplete frames are rejected before writes. If a
scheduled command fails during rendering, the produced prefix and preceding
commands remain applied; the cursor stays on the failing frame, the command
is not consumed and the suffix remains intact. Reset and rebuild the render
after failure. User instrument errors propagate; if it fails inside its own
render, its contract determines the affected prefix.

The voice pool, envelopes and working buffer are prepared at creation.
Rendering and valid commands of the built-in instrument do not grow collections.
Work per frame depends on occupied voices and channel count; this qualification
does not promise a maximum load on every device. The [MIDI reader](MIDI.md)
controls these instruments. User banks, realistic instrument models and
humanization remain separate capabilities to establish.

[Play a MIDI score with your own instruments](MIDI.md).
