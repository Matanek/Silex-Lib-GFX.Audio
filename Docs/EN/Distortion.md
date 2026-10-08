# Saturate or distort sound

`Processing.Distortion` gives the signal soft saturation or hard clipping.
`drive` pushes the signal into the curve; `output_gain` then sets its level,
and `wet` blends the result with dry input. It processes channels independently
and can join a [Processed](Composition.md) chain.

The [executable demonstration](../../Examples/SaturatedSounds.sx) compares the same dry
sine, soft saturation with drive 2 then 8, and hard clipping with drive 8.
It then applies an explicit envelope and attenuation. From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Examples/SaturatedSounds.sx --release
```

Fragment for an already prepared `format` and `samples` buffer:

```sx
match Processing.Distortion.create(format, drive:4.0,
    mode:Processing.DistortionMode.soft, output_gain:0.5, wet:0.75) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Choose the curve and level

For `z = drive * input`, `soft` computes `z / (1 + abs(z))`, while `hard`
limits z to [-1, 1]. Float32 expressions are stabilized to avoid overflow
on large finite inputs, even with drive 256. Both curves are symmetric, and
zero remains zero. The soft mode also reduces small-signal levels; it uses
no implicit gain compensation. Processed output is `output_gain * curve(z)`,
then output is `(1 - wet) * input + wet * processed_output`.

Drive=0 removes the processed part. Output gain can exceed ±1: choose a
suitable level explicitly before `Audio.create` or stream writing. Mixing
with dry input outside ±1 can also exceed that range. Wet=0 and bypass
preserve dry samples exactly; wet=1 uses processed output only. Finite dry
values outside ±1 are accepted. Saturation changes harmonics and can produce
aliasing; no oversampling or anti-aliasing filter is added.

## Adjust the effect between blocks

| Setting | Default | Range |
| --- | --- | --- |
| `drive`, `set_drive(drive)` | 2 | Finite float32 from 0 to 256 |
| `mode`, `set_mode(mode)` | soft | `DistortionMode.soft` or `.hard` |
| `output_gain`, `set_output_gain(output_gain)` | 1 | Finite float32 from 0 to 16 |
| `wet`, `set_wet(wet)` | 1 | Finite float32 from 0 to 1 |
| `set_bypass(bypass)` | false | Boolean |

Numeric setters return `Result<void, Error>` and preserve settings when a
value is rejected. All changes take effect at the next `process`, with no
smoothing: the application prepares smooth transitions. `reset()` preserves
settings; the effect has no audio history and adds no processing-latency
frames or tail. References to the same class share its settings.

## Formats, errors and resources

Formats, interleaved frames and views follow [Processing](Processing.md).
An empty block produces nothing. Non-finite samples and incomplete frames
return `invalid_input`, operation `audio.process`, before writes, even with
wet=0 or bypass. The view is not retained after the call.

Work is linear in sample count, with no history or arrays allocated during
`process`. This does not guarantee real-time latency.
[Numerical oracles](Validation.md) cover curves, extremes, channels, chunking,
changes, invalid input and order with a consumer-defined processor.
