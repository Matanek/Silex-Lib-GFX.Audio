# Compose and modulate a sound

Combine sources with `Synthesis.Mix`, then apply treatments in order with
`Synthesis.Processed`. Both implement `Generator`, so a composition can be used
like any other source. [ModulatedSounds.sx](../ModulatedSounds.sx) lets you hear
these combinations.

An application-defined generator can join the mix; a custom
`Processing.Processor` can join the chain. No Interop is needed. The
[Composition.sx](../../Tests/Consumer/Tests/Composition.sx) consumer illustrates
both stateful extensions.

These primitives require the local toolchain with protocol property reads and
mutable field iteration until those corrections are published.

## Mixing and processing

`Mix.create(sources, gains)` accepts 1 to 32 generators with matching formats
and one signed gain per source, between -16 and 16. The output is their weighted
sum, without clipping or normalization: choose levels that leave enough playback
headroom. Even a source with zero gain advances normally.

`Processed.create(source, effects)` applies 0 to 32 treatments with matching
formats, in the supplied order. An empty chain passes the source through.
Treatments receive the caller's block; a custom treatment must preserve state
and output independently of block boundaries. A delay retains its tail:
continue rendering a silent source to hear it after a note ends.

## Amplitude, LFO and curve

`AmplitudeModulation.create(source, modulation, offset:0.5, depth:0.5)` multiplies
each frame by `offset + depth * modulation`. The control is a mono generator at
the source sample rate, with finite values in [-1, 1]. All channels receive the
same gain. `abs(offset) + abs(depth)` must be at most 16. With the defaults,
a sine control produces tremolo between zero and one; `offset:0, depth:1`
produces signed ring modulation.

An `Oscillator` running at a few hertz directly serves as an LFO. For a
transition, `Curve.create(format, start, end, duration_frames)` produces a linear
segment between two values in [-1, 1]. Frame zero equals `start`, frame
`duration_frames` equals `end`, and that value is then held. Zero duration
immediately produces `end`. The maximum duration is 16,777,216 frames. The curve
advances once per frame and duplicates its value across channels; use a mono
format for a modulation control.

## Frequency

`FrequencyModulation.create(format, modulation, frequency_hz:440,
deviation_hz:100, amplitude:1, phase:0)` produces a sine wave with instantaneous
frequency `frequency_hz + deviation_hz * modulation`. The control is mono, at
the same sample rate, and bounded in [-1, 1]. Deviation is nonnegative and the
entire frequency range must stay in [0, Nyquist). Amplitude is in [0, 1] and
initial phase in [0, 1).

Output uses the current phase, then integrates the frame's frequency for the
next frame. This convention supports continuous pitch curves and vibrato without
resetting phase. Parameters are fixed at construction; live control belongs to
instruments.

Validating instantaneous frequency does not guarantee that every sideband stays
below Nyquist. Fast audio modulation, large deviations or a discontinuous
control can cause aliasing, including in AM. This first FM is sinusoidal:
it does not modulate the palette's discontinuous waveforms. Qualification
includes a musical modulation regime sufficiently far from Nyquist; no general
oversampling or alias suppression guarantee is made.

## State, errors and resources

Compositions retain the supplied objects. A class keeps its shared identity;
reusing one instance in several branches advances the same state multiple times.
Construct fresh instances in each recipe for independent voices. Lists are
retained by value; changing an input list later does not reconfigure the
composition.

`reset()` resets all contained sources, controls and treatments. For ADSR this
returns to the inactive state; call `note_on()` again for a new note. An empty
view consumes no state. An incomplete frame is rejected before rendering.

Nonfinite values, controls outside their range and float32 overflow return a
recoverable error. A generator or treatment may already have advanced and the
block may be partially written: reset the composition and rebuild the block
before retrying. Component errors are propagated.

Mix and modulation prepare their buffers at construction and process any block
length in internal chunks of at most 512 frames. The processing chain directly
uses the supplied view. Rendering explicitly creates no arrays, reads no files
and waits for no device. This does not yet promise real-time latency: runtime
costs and load will be measured during final qualification. User extensions
remain responsible for their own costs, errors and block guarantees.
