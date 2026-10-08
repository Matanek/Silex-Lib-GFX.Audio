# Add chorus and flanger

`Processing.ModulatedDelay` mixes sound with a copy whose delay follows a
sine wave. A delay of a few tens of milliseconds produces chorus; a shorter
delay with feedback gives flanging. These effects use the supplied samples,
without a sound bank.

The [complete demonstration](../../Examples/ChorusAndFlanger.sx) plays the same procedural
chord four times: dry, chorus, positive-feedback flanger, then negative feedback.
An envelope precedes the delay, and rendering keeps half a second of silence
for its tail. From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Examples/ChorusAndFlanger.sx --release
```

Fragment for a 48 kHz `format` and a prepared `samples` buffer:

```sx
match Processing.ModulatedDelay.create(format, max_delay_frames:1_200,
    delay_frames:720.0, depth_frames:240.0, rate_hz:0.8, feedback:0.0, wet:0.5) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Choose delay, motion and level

Durations count frames, independently of channels: at 48 kHz, 48 frames
equal 1 ms. `delay_frames` is the center and `depth_frames` is the depth.
Delay is `center + depth * sin(2*pi*phase)`. Phase starts at zero and advances
by `rate_hz/sample_rate` per frame. The sine is shared across channels;
each channel retains its own sound. This chorus therefore does not
automatically add stereo width.

| Recipe at 48 kHz | Center | Depth | Rate | Feedback | Wet |
| --- | --- | --- | --- | --- | --- |
| Chorus | 720 frames / 15 ms | 240 / 5 ms | 0.8 Hz | 0 | 0.5 |
| Flanger | 96 frames / 2 ms | 72 / 1.5 ms | 0.6 Hz | ±0.75 | 0.5 |

Minimum delay is one frame. Reading is causal and linearly interpolates
between two past frames: an impulse delayed by 2.5 frames appears in halves
at frames 2 and 3. The processed copy arrives between `center-depth` and
`center+depth`, with interpolation spreading; the dry path adds no frames.
Format and frame count stay fixed.

Output is `(1-wet)*dry + wet*delayed`, and the delay stores
`dry + feedback*delayed`. Wet=1 emits only the delayed copy. Wet=0 and
bypass preserve dry samples exactly, while history and phase keep advancing.
Feedback can be negative and its magnitude must remain below 1.
No normalization or limiting is added. For input bounded by A, history is
theoretically bounded by `A/(1-abs(feedback))` from reset;
choose level headroom before audible output.

With zero feedback, after input ends, at most `ceil(center+depth)` silent
frames flush the delayed copy. With feedback, the tail decays without a
predefined finite duration: keep processing silence according to the
application's chosen threshold. `reset()` cuts it off.
Interpolation can attenuate high frequencies; fast modulation, large delay
changes and sidebands can cause aliasing. No anti-aliasing filter,
oversampling or parameter smoothing is promised.

## Prepare the effect and adjust it between blocks

`create(format, max_delay_frames, delay_frames, depth_frames:0.0,
rate_hz:0.5, feedback:0.0, wet:0.5)` returns a `Result`.
Format accepts 1..8 channels and an integer rate of 1 through 16,777,216 Hz.
Settings are finite float32 values. Center ± depth must fit
[1, max_delay_frames], depth ≥0, rate ≥0 and strictly below Nyquist.
A positive rate whose step becomes zero is rejected. Rate=0 freezes the current
phase; after reset the delay therefore equals its center.

`max_delay_frames` prepares the adjustment range; it ranges from 1 through
`1_048_576/channels - 1` using integer division. Delay storage includes one
extra frame for interpolation. All buffers are prepared at creation;
their float32 contents occupy
`4 * ((max_delay_frames+1)*channels + 2*channels)` logical bytes.
Physical allocation adds spare capacity and headers; float32 elements use
four bytes on ARM64 and eight-byte slots on X64.

`set_delay(delay_frames, depth_frames)` changes both durations together
within the prepared range. `set_rate(rate_hz)`, `set_feedback(feedback)`
and `set_wet(wet)` return `Result<void, Error>`; rejection preserves state
and settings. `set_bypass(bool)` starts at false.
Changes apply immediately to the next block, without clearing history or
restarting phase. `reset()` clears history and resets phase and cursor to zero,
while retaining settings. Construct another instance for independent state:
class references share the effect.

## Process blocks and errors

Views must contain complete frames and finite samples. The entire block is
checked before writing or advancing state, including under bypass.
An empty block does nothing. Invalid input returns `invalid_input`,
operation `audio.process`.

A float32 overflow in feedback or output returns `limit_exceeded`.
The failing frame and its audio state remain intact, but a prefix may already
have been processed. Reset and reconstruct the original block before retrying.
Feedback can overflow under bypass because the effect keeps advancing.

Rendering runs on the application thread. It allocates no new buffer in
`process`, does not retain the view, and computes at most one sine per frame,
shared across channels. Rate conversions and capacities are prepared outside
the loop; a frozen delay does not recompute its sine per frame.
Float32 phase is intended for timbre: its limited precision does not provide
a musical transport clock or a real-time guarantee.

[The oracles](Validation.md) cover impulses, signed echoes, a known LFO,
tone cancellation, decay, channels, exact chunking, reset, changes, errors
and consumer composition. To write your own effect, see
[composition](Composition.md).
