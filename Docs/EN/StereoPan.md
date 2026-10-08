# Move sound between left and right

`Processing.StereoPan` positions both channels of a stereo signal. At center,
it preserves left and right. At full left, it adds both channels on the left
and outputs zero on the right; at full right, it does the reverse. It transfers
the opposite channel rather than simply silencing it.

The [demonstration](../../Examples/StereoSounds.sx) plays left, center, right, then moves
across prepared blocks. Its generator provides the same sine in both channels,
followed by an explicit envelope and attenuation. From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Examples/StereoSounds.sx --release
```

Fragment for a prepared stereo `format` and `samples` buffer:

```sx
match Processing.StereoPan.create(format, pan:-0.5, wet:1.0) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Predict levels and channels

Pan ranges from −1 (left) to +1 (right), with 0 at center. For negative pan,
`angle = abs(pan) * pi/2`, `L' = L + sin(angle)*R`, and `R' = cos(angle)*R`.
For positive pan, `L' = cos(angle)*L` and `R' = R + sin(angle)*L`.
Poles and center use exact coefficients.

| Pan with wet=1 | Left | Right |
| --- | --- | --- |
| −1 | L + R | 0 |
| −0.5 | L + 0.7071 R | 0.7071 R |
| 0 | L | R |
| +0.5 | 0.7071 L | R + 0.7071 L |
| +1 | 0 | R + L |

The transferred channel follows a sine/cosine law. The complete mix does not
have constant power: correlated channels add, and opposite-phase channels
can cancel at a pole. Two values of 0.75 produce 1.5 on the selected side.
No implicit normalization or limiter hides this sum; choose gain before
`Audio.create` or stream writing. This effect retains a stereo format; it
does not convert a mono source to stereo.

Wet blends `(1 - wet) * dry + wet * pan_output`. Combined coefficients are
prepared when settings change. Wet=0 and bypass preserve dry samples exactly;
center also preserves samples. Frame count and output rate stay unchanged.

## Adjust placement between blocks

`create(format, pan:0.0, wet:1.0)` requires two channels and a rate accepted by
[Processing.Format](Processing.md). `set_pan(pan)` accepts finite float32 from
−1 to +1; `set_wet(wet)` accepts finite float32 from 0 to 1. They return
`Result<void, Error>` and preserve settings on rejection.
`set_bypass(bypass)` takes a boolean, initially false.

Changes take effect at the next `process`, without smoothing. To prepare
movement, choose positions and block boundaries in frames, as in the example;
this does not yet provide an automation engine. `reset()` preserves settings:
there is no audio history, processing-latency frame or tail. Class references
share settings.

## Handle errors and understand resources

Views must contain complete stereo frames and finite values. An empty block
does nothing. Invalid input returns `invalid_input`, operation `audio.process`,
before writes, including at center or under bypass.

If a sum exceeds finite float32 range, `limit_exceeded` leaves the failing
frame intact; a prefix may already be processed. Reconstruct the original
block before retrying. Finite values outside ±1 are accepted, which does not
mean they can be used directly for audible output.

Trigonometric coefficients are calculated at creation and setting changes.
`process` performs linear work with no new allocation, history or per-sample
trigonometry. This does not guarantee real-time latency. The view is not
retained. [Oracles](Validation.md) cover bases, the law, levels, chunking,
composition, reset, invalid input and partial overflow.
