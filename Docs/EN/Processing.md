# Process samples before output

`GFX.Audio.Processing` provides `Format`, the `Processor` protocol, `LowPass`,
`Delay`, `Equalizer`, `Bitcrusher`, `Distortion`, `DistortionMode` and `levels`.
An effect retains state and modifies an application-owned `&float32[..]` view. It can process producer blocks, offline
rendered blocks, or blocks to feed a stream.

Factories return `Result` and take `Format(sample_rate:48_000, channels:2)`.
Format stays fixed for the effect lifetime. Samples must be finite interleaved
complete frames; an empty view does not advance state. Values beyond ±1 are
accepted to preserve mix headroom within float32 range (the bitcrusher
explicitly saturates its processed part). Effect parameters,
coefficients and state use float32, like the PCM.
RMS energy is accumulated in float64.

`process(samples:&buffer[0:buffer.count()])` returns `Result<void, Error>`.
Call order defines processing order. The consumer chooses the chain and keeps
the same effect between blocks; `reset()` clears its
history. Effects never retain the view. A dynamic `Processor` shares the effect
class identity, including settings and history.

Work runs sequentially on the application thread, without a Silex callback on
a native audio thread. Effects do not allocate a new output buffer per block.
Silex view ownership can detach shared collections before mutation. Stream
capacity sets prepared headroom, not a guaranteed presentation time. This API
uses the toolchain fix allowing methods to receive mutable views like free
functions; use the locally qualified toolchain until that fix is published.

## Low-pass filter

`LowPass.create(format, cutoff_hz:1000.0)` creates a one-pole filter per channel:
`y = (1 - alpha) * y + alpha * x`, where `alpha = 1 - exp(-2*pi*cutoff/sample_rate)`.
Cutoff must be positive and below Nyquist, with a representable nonzero
coefficient. `set_cutoff(cutoff_hz)` validates the setting and preserves history.

## Delay and echo

`Delay.create(format, delay_frames:4800, feedback:0.5, wet:0.5)` produces
`output = input + wet * delayed` and stores `input + feedback * delayed`.
Delay is in frames independently of channels; each channel has its own tail.
Capacity is at most 1,048,576 interleaved samples. Feedback must be finite with
magnitude below one; wet is finite, nonnegative and float32-representable.
`set_feedback` and `set_wet` preserve the tail. Render tails by explicitly
processing silence for a chosen duration; there is no infinite tail wait.

## Equalization and levels

`Equalizer.create(format, low_hz:250.0, high_hz:4000.0, low_gain:1.0,
mid_gain:1.0, high_gain:1.0)` splits the signal with two one-pole low-pass filters:
low, the difference between low-pass outputs, and input minus upper low-pass.
Cutoffs must be ordered, positive and below Nyquist. Gains must be finite,
nonnegative and float32-representable. Three unit gains reconstruct the input;
three gains of 0.5 explicitly attenuate it. `set_gains(low, mid, high)` preserves
history. Setting changes have no automatic smoothing.

`levels(@samples[0:count], channels:2)` returns `Result<Level[], Error>` with
absolute peak and float64 RMS per channel in interleaved order. The supplied
view is the exact analysis window; an empty window returns zero. Analysis
allocates small per-channel arrays and never changes samples.

Invalid inputs are rejected before mutation or state changes. Processing overflow
returns `limit_exceeded`, without clipping or normalization. A prefix may already
be processed in this case: reset and reconstruct the original block before
retrying. Before stream writing or sound creation, explicitly choose a level
within ±1, for example with equalizer gains. Whole/chunked continuity is
qualified within absolute 10⁻⁶ for controlled-level fixtures; reset removes tails.

[Example: independent producer filtered during playback](../ProcessedTone.sx).

[Bitcrusher: resolution, sample hold, mixing and bypass](Bitcrusher.md).

[Saturate or distort sound](Distortion.md).
