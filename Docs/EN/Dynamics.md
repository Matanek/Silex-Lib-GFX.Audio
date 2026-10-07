# Control differences in level

`Processing.Compressor` reduces differences above a threshold and allows explicit
makeup gain. `Processing.Limiter` imposes a ceiling on processed samples.
Both implement `Processor` and compose with application-defined effects.
Neither is automatically added to sources or playback.

[DynamicSounds.sx](../DynamicSounds.sx) compares a phrase with uneven accents:
dry, compressed with makeup, half dry mix, then limited. Final attenuation
is identical in all four passages; volume differences are intentional.
From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Docs/DynamicSounds.sx --release
```

Fragment for a prepared `format` and `samples` buffer:

```sx
match Processing.Compressor.create(format, threshold_db:-18.0, ratio:4.0,
    attack_seconds:0.008, release_seconds:0.12, makeup_db:9.0) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Choose settings

Formats accept 1..8 channels and an integer rate of 1..384,000 Hz. Controls are
finite float32 values within the ranges below. dBFS refers to a sample amplitude
of 1: linear level is `exp(db * ln(10)/20)`.

| Effect / parameter | Default | Range and meaning |
|---|---|---|
| Compressor `threshold_db` | −18 | −96..0 dBFS, threshold |
| Compressor `ratio` | 4 | 1..100; 4:1 reduces a 12 dB excess to 3 dB at steady state |
| Compressor `attack_seconds` | 0.01 | 0..10 s, detector rise |
| Both `release_seconds` | 0.1 | 0..10 s, detector fall |
| Compressor `makeup_db` | 0 | −24..24 dB, gain/attenuation after compression |
| Limiter `ceiling_db` | −1 | −96..0 dBFS, sample ceiling |
| Both `wet` | 1 | 0..1, dry/processed mix |

`Compressor.create(format, ...)` and `Limiter.create(format, ...)` return a
`Result`. The compressor exposes `set_threshold(threshold_db)`, `set_ratio(ratio)`,
`set_times(attack_seconds, release_seconds)` and `set_makeup(makeup_db)`.
The limiter exposes `set_ceiling(ceiling_db)` and `set_release(release_seconds)`.
Both provide `set_wet(wet)` and `set_bypass(bool)`. Numeric setters return
`Result<void, Error>`; rejection preserves settings and history.
Changes apply at the next block, without parameter smoothing.

Times are one-pole filter constants, not a duration to reach the target exactly
or a 10-to-90-percent measurement. For positive duration t,
`alpha=1-exp(-1/(sample_rate*t))`, calculated in float32; t=0 gives alpha=1.
Rounding limits precision at extreme times. The limiter always attacks
immediately: no slow attack setting compromises its ceiling.

## Understand detection and output

A single peak `max(abs(channel))` per frame controls every channel. All receive
the same reduction, preserving their balance within float32 precision.
A silent channel stays silent. Linked detection can attenuate every channel
because of just one; this model does not provide independent detection.

The compressor follows peak p with `e=e_previous+alpha*(p-e_previous)`;
alpha comes from attack when rising and release when falling. The implementation
uses equivalent forms to avoid intermediate overflows.
For linear threshold T, gain is 1 if e<=T or ratio=1, otherwise
`(e/T)^(1/ratio-1)`. Logs are subtracted before exponentiation,
without calculating a ratio that might overflow. Makeup is explicit.
The [hard-knee static curve](https://www.mathworks.com/help/audio/ref/compressor-system-object.html)
expresses ratio in dB; the times and detection described here belong to Silex.
Positive attack allows transients through; this compressor guarantees
no ceiling and its makeup can produce values outside ±1.

The limiter immediately sets e=p when rising; when falling, its detector follows
the same release filter. If e exceeds ceiling C, processed output is
`(sample/e)*C`, bounded to ±C for rounding. Normalizing before multiplication
avoids an imprecise subnormal gain for an immense input. Otherwise the sample is
preserved. The ceiling is guaranteed on float32 samples with wet=1 and bypass=false;
it is not a true-peak measurement of the reconstructed signal between samples.

Wet mixes `(1-wet)*dry + wet*processed`. Wet=0 and bypass return dry samples
exactly while advancing the detector. A mix containing dry signal can exceed
the ceiling. Format, frame count and positions are preserved; there is no
lookahead or audio delay. These effects do not create an audible tail in silence,
but their detector influences subsequent notes. `reset()` clears that detector
and preserves settings and bypass. A class reference shares state;
construct separate instances for independent chains.

## Prepare resources and handle errors

The whole block is checked before mutation: finite samples and complete frames,
including under bypass. An empty view advances nothing. Invalid input returns
`invalid_input`, operation `audio.process`. Output buffers are prepared at
creation: one float32 per channel, up to eight, plus scalar state.
Physical bytes depend on runtime slots, headers and spare capacity.

An entire frame is calculated before writing output and the detector.
A float32 overflow returns `limit_exceeded`, preserving the failing frame and
its state; a prefix may already have been processed. Reset and reconstruct the
original block before retrying. Compressor makeup can trigger this case;
the limiter normalizes extreme input without first multiplying a large amplitude.

`process` does not retain the view or create any array. Work is linear in
samples; peak and gain are shared between channels. The compressor computes at
most one log and one exponential per frame above threshold, outside
bypass/wet=0/ratio=1; time coefficients are calculated only at creation and
when changing times. No real-time guarantee is made.

[The oracles](Validation.md) cover curves, times, channels, blocks, settings,
extremes and errors; [composition](Composition.md) explains user extension.
