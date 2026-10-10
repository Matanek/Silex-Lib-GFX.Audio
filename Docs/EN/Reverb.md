# Add reverberation to sound

`Processing.Reverb` adds a diffuse tail to the signal without an impulse
file or sound bank. Choose room size at creation, then adjust decay,
high-frequency damping and the dry/wet mix.

The [demonstration](../../Examples/ReverberantSounds.sx) plays three plucked notes, then
lets silence resonate. It compares dry sound, a short room, a long bright tail
and a long dark tail. The envelope precedes the effect; the final silent blocks
render its tail. From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Examples/ReverberantSounds.sx --release
```

Fragment for a prepared `format` and `samples` buffer:

```sx
match try Processing.Reverb.create(format, room_size:0.65, decay_seconds:2.0,
    damping:0.5, wet:0.45) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match try effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Adjust space, color and levels

`create(format, room_size:0.5, decay_seconds:1.5, damping:0.5, wet:0.3)`
returns a `Result`. Format accepts 1..8 channels and an integer sample rate
of 1 through 384,000 Hz. Room size, damping and wet are finite float32 values
from 0 to 1; decay ranges from 0.05 to 20 seconds.

Room size increases delays without representing a physical dimension in
meters. It stays fixed: prepare a new instance for another size.
`set_decay(decay_seconds)`, `set_damping(damping)` and `set_wet(wet)`
return `Result<void, Error>`. Rejection preserves settings and history.
`set_bypass(bool)` starts at false.
Changes apply immediately to the next block without smoothing or clearing
the tail; abrupt changes may be audible.

Wet mixes `(1-wet)*dry + wet*reverb`. Wet=1 emits only the tail;
wet=0 and bypass preserve dry samples exactly while feeding history.
Keep processing silence after the source to hear the ending.
The tail has no predefined finite duration: the application chooses its
threshold and rendering duration. `reset()` clears every delay and filter,
while retaining size and settings; it therefore cuts off the tail.

Each channel owns its delays and filters. Sound never moves to another
channel: a silent channel stays silent, and identical inputs give identical
outputs. This version does not create stereo width, convert mono or simulate
a measured physical room. A class reference shares state; create two
instances for two independent reverbs.

Feedback can amplify some frequencies. The internal mix of four lines uses
a fixed gain of 0.25 per line; it does not normalize their contents according
to level or duration. No limiter is added. Leave headroom before
`Audio.create` or an audible stream, which require samples within ±1.
Calculations accept finite input outside ±1.

## Understand delays and decay

The network uses four filtered-feedback delay lines in parallel followed
by two allpass diffusers in series. Its structure draws on
[Schroeder reverberators described by Julius O. Smith](https://www.dsprelated.com/freebooks/pasp/Schroeder_Reverberators.html).
The Silex implementation defines its own delays and settings.

The six lengths are `max(1, round(base * scale))`, calculated in float32
at creation, where `scale=(0.5+1.5*room_size)*sample_rate/48000`.
Bases at 48 kHz are 1429, 1783, 1973, 2099, then 241 and 83 frames.
Round rounds half-integers away from zero. At very low rates, several
lengths coincide; behavior stays causal but does not represent natural
reverberation.

For a line of length D, delayed sample v passes through
`f=(1-d)*v+d*f_previous`, where `d=0.95*damping`; the line receives
`dry+g*f`, where `g=exp(-ln(1000)*D/(sample_rate*decay_seconds))`.
Zero damping preserves bright feedback; increasing it attenuates high
frequencies. Decay sets a nominal 60 dB decay for an isolated undamped line.
It does not guarantee measured RT60 for the whole network: color,
interference and diffusers alter its response.

The mix is the average of the four delayed samples. Each allpass with
coefficient 0.5 computes `y=delayed-0.5*x` and stores `x+0.5*y`.
These two stages diffuse echoes; they are not a second wet mix.
The dry path adds no frames. The first processed output appears after
the shortest feedback line, without adding diffuser lengths because those
stages have a direct path. Format and frame count are preserved.

## Handle errors and prepare resources

The entire block is checked before writing or advancing state: finite samples
and complete frames, including under bypass. An empty view does nothing.
Invalid input returns `invalid_input`, operation `audio.process`.
A float32 overflow returns `limit_exceeded` before modifying the failing
frame or its history, but a prefix may already have been processed.
Reset and reconstruct the original block before retrying. Feedback can
overflow under bypass because delays keep advancing.

Buffers are private and prepared at creation. Delays contain at most
973,824 float32 samples for 384 kHz, eight channels and room size=1.
The logical float32 value payload is
`4 * (channels * sum_of_six_lengths + 15*channels + 4)` bytes.
This does not measure physical allocation: ARM64 uses four-byte float32
elements, X64 eight-byte slots; spare capacity, headers and three arrays
of six integers add to that. Decay duration does not change logical capacity. Feedback coefficients are computed at creation
and `set_decay` without allocation.

`process` does not retain the view or allocate a new buffer. Per frame
and channel, it processes four filtered lines and two allpasses, with constant
work per sample; it never recomputes exponentials inside this loop.
It runs on the application thread without a real-time guarantee.

[The proofs](Validation.md) check analytical first echoes, damping, tails,
channels, blocks, settings, limits, errors and composition.
See [chorus and flanger](ChorusAndFlanger.md) for a moving delay,
or [composition](Composition.md) for a custom effect.
