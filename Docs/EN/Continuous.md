# Evolve a sound during playback

`Synthesis.Control` produces a mono signal that the application can change
gradually. It feeds pitch and gain modulation, as well as user generators.
Instruments also receive ramps through `Command.pitch_bend_to` and
`Command.gain_to`, directly or in a `Sequence`.

[ContinuousSounds.sx](../ContinuousSounds.sx) plays two sources in bounded
streams: a procedural engine whose regime rises and falls, then a chord with
pitch glides, gain changes and an echo tail. Each pass uses a single playback.
From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Docs/ContinuousSounds.sx --release
```

The engine combines two modulated sines and seeded pink noise; it illustrates
an adjustable procedural timbre without simulating a real engine or loading
a sound bank. Commands and accents are explicit. No humanization is added.

## Change the target without restarting

Fragment with a `require(Result<void, Error>)` helper and a prepared mono
`samples` buffer of 1,000 frames:

```sx
match Synthesis.Control.create(48_000, value:-1.0) {
    failure(error) => { panic(error.detail) }
    success(var pitch) => {
        require(pitch.set(1.0, duration_frames:24_000))
        require(pitch.render(&samples[0:samples.count()]))
        // Retarget from the next frame's current value, without resetting phase.
        require(pitch.set(0.0, duration_frames:12_000))
    }
}
```

`Control.create(sample_rate, value:0)` accepts integer rates in
1..16,777,216 Hz and finite float32 values in −1..1.
`set(value, duration_frames:0)` accepts 0..16,777,216 frames. Its format stays
mono; a control used with multiple sources needs independent instances,
because each render advances its state. Classes retained by AM/FM remain
shared with the application's controller.

An N-frame ramp emits the current level at its first sample, then advances
linearly; frame N emits the exact target. `current_value()` gives the next
frame's value. Changing the target resumes from this value, even during a ramp.
N=0 changes immediately and may create a jump. An empty block advances nothing;
`reset()` restores the creation value and cancels the ramp. Rejected values,
durations or formats leave state unchanged.

`Command.pitch_bend_to(semitones, frames)` applies the same progression in
semitone space (−24..24), preserving phase. The frequency ratio is
`2^(semitones/12)`. The full ramp must keep voices below Nyquist and float32
steps positive; a new note is also checked against the target still in progress.
`Command.gain_to(gain, frames)` linearly sets the instrument's global gain in
0..1, initially 1, after the sum of voices. Durations use the same range as
Control. Instrument reset restores gain to 1 and bend to 0. The ramp keeps advancing
while no voice plays; it does not restart for each note. Existing effects do
not automatically receive parameter ramps.

## Feed a stream without replaying the block

`Synthesis.StreamProducer.create(audio, source, duration_frames,
block_frames:512, capacity_frames:4_800)` prepares a working buffer and opens
a stream matching the Generator's format. The finite duration accepts
0..int64 max, including for an infinite source. Blocks accept 1..65,536 frames;
capacity follows [the stream contract](Streaming.md).

`producer.stream()` provides the handle for `audio.play`, controls and
`stream_info`. Keep the producer alive throughout playback: it retains Audio
and the source, and releases the stream when its last reference disappears.
A class source shares its state; a struct is copied into the protocol value.
The producer starts from the source's current state, without an implicit reset.
Its counter starts at zero at creation.

`pump()` produces at most one block and tries to write its suffix. It returns
the accepted frame count or `would_block` if the stream is full. A partial write
keeps the rest of the buffer; later calls send it without rendering the source
again or repeating commands. Once the full duration is written, the producer
automatically closes input. Subsequent calls return zero. Zero duration closes
without rendering a sample.

The application prefills the stream before `play`, calls `pump` regularly,
then waits for completion after `input_closed()`. It may call `wait_writable`
outside block calculation after a `would_block`, or retry on its next turn.
The producer performs no intentional wait or Silex callback on a native thread.
Prepare and use source/producer on a single thread.

## Observe look-ahead and late commands

| Counter | Meaning |
|---|---|
| `produced_frames()` | Frames already calculated since producer creation |
| `written_frames()` | Frames accepted by the stream |
| `pending_frames()` | Difference produced − written, always ≤ block_frames |
| `input_closed()` | All frames written and input closed |
| `stream_info().consumed_frames` | Frames taken by the mixer |

Already calculated frames are not modified by a new Control target.
Scheduling a Sequence command before its `rendered_frames()` is rejected.
Known events therefore use the production clock; a live gesture affects the
next frames to calculate. Stream capacity plus one block bounds look-ahead
in unconsumed frames, with prepared mixer/device output on top.
`consumed_frames` is not the exact loudspeaker position. The example uses
1,440 queued frames and a 480-frame block at 48 kHz, at most 40 ms of
unconsumed PCM, excluding prepared output, at speed1. This calculation does
not promise uniform system latency or freedom from starvation.

Pause/resume use Audio controls; pause retains the queue and block. A starved
open source remains active and can be fed again. Early stop ends playback;
the next pump refuses to produce more. Duration includes the chosen note
release and effect tail: closing input does not automatically generate them.
Wait for `drained` for normal completion. To replay, wait/stop and release the
old producer, reset the source and create a new stream; a started stream
cannot be reused.

Writes must be exclusive to the producer. Directly writing or closing its
stream before completion is detected before the next calculation. A source
failure or non-finite/out-of-range −1..1 output blocks the producer: release
and rebuild with a reset source. Source/Audio errors propagate. Internal
rendering can exceed −1..1, but Audio output needs explicit headroom;
ramps do not normalize voices.

The Silex buffer stays bounded after preparation. This does not certify SDL
provider allocations or hard real time. Proof covers partial writes,
identity with memory rendering, pauses, starvation, stop, closure, tails and
lifetime. Listening to the program complements this proof for transitions
and continuity of actual output.

[Play a MIDI score with your own instruments](MIDI.md).
