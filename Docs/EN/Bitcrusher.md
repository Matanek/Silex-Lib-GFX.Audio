# Give sound a retro texture

`Processing.Bitcrusher` reduces amplitude precision and holds samples for
several frames. Both settings are independent: 8 bits provide 256 levels;
`hold_frames:6` at 48 kHz captures 8,000 values per second per channel. Output
remains float32 PCM at 48 kHz, with the same frame and channel counts.

The [executable demonstration](../../Examples/RetroSounds.sx) compares the same dry sine,
at 8 bits, at 4 bits, then at 24 bits with sample hold. It then plays a square
arpeggio and a noise impact, without files or sound banks. From the
`SilexProject/` root:

```sh
silex run Packages/GFX.Audio/Examples/RetroSounds.sx --release
```

It prepares PCM in memory, quantizes before the envelope, and explicitly
attenuates output. This keeps the effect audible while softening starts and
ends. Each of the eight notes occupies 9,600 frames at 48 kHz; this recipe
does not yet provide a musical transport or MIDI input.

## Insert and adjust the effect

The effect implements [Processing.Processor](Processing.md). It processes a
mutable view on the application thread and can join a
[Synthesis.Processed](Composition.md) chain before or after other effects.
Use this fragment once `format` and `samples` are prepared:

```sx
match Processing.Bitcrusher.create(format, bits:8, hold_frames:6, wet:0.75) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

Keep the same instance between blocks to preserve sample hold. As with other
class effects, references share settings and state. Build fresh instances for
independent playbacks.

| Setting | Default | Range | Change |
| --- | --- | --- | --- |
| `bits`, `set_bits(bits)` | 8 | Integer from 2 to 24 | Capture on the next frame |
| `hold_frames`, `set_hold_frames(hold_frames)` | 1 | Integer from 1 to 16,777,216 | Capture on the next frame |
| `wet`, `set_wet(wet)` | 1 | Finite float32 from 0 to 1 | Immediate, preserves clock |
| `set_bypass(bypass)` | false | Boolean | Immediate, preserves clock |

The three numeric setters return `Result<void, Error>`; rejection preserves
settings and state. A valid `set_bits` or `set_hold_frames` call triggers a
capture even if the value is unchanged. `reset()` clears sample hold and
triggers a capture on the next sample while retaining settings, including
wet and bypass. Changes have no automatic smoothing: applications that need
a smooth transition prepare their own wet ramp.

## Understand levels and sample hold

With `scale = 2^(bits - 1)`, each capture saturates input to
`[-1, 1 - 1/scale]`, rounds `input * scale` to the nearest integer (ties to
even), and divides by scale. At 8 bits, codes range from −128 to 127:
−1, −127/128, …, 0, …, 127/128. Zero stays silent; +1 becomes 127/128.
This saturation explicitly belongs to the processed timbre. Finite dry values
outside ±1 remain accepted.

The first frame captures all channels, then each quantized value is reused
for `hold_frames` frames, including the capture frame. Channels have their
own values and a shared clock. A block boundary does not change that clock;
an empty block does not advance it. Sample hold emits from the first frame: no processing-latency frames or tail
are added. It changes neither the declared rate nor output length; it can
change the signal’s spectral phase.

Output is `(1 - wet) * input + wet * held_value`. Wet=1 uses processed values;
wet=0 and bypass preserve dry samples exactly. Captures continue in both
latter cases: re-enabling the effect resumes the current hold position.
Mixed output can exceed ±1 if the dry part does; choose its level before
`Audio.create` or stream writing.

Sample hold uses no anti-aliasing filter: aliasing and steps are part of this
effect. It does not replace oscillator harmonic limits or emulate a particular
console. To isolate sample hold, 24 bits make quantization small; to isolate
bit depth, keep `hold_frames:1`.

## Validation and resources

Formats follow `Processing.Format`: 1 to 2,147,483,647 Hz, 1 to 8 channels,
complete interleaved frames. Every non-finite sample, including under bypass,
is rejected with `invalid_input`, operation `audio.process`, before writes
or state changes. The buffer is not retained after `process`.

The effect prepares per-channel history at creation and creates no array
during `process`. Work is linear in sample count, with quantization only on
captures. This property is not a real-time latency guarantee; view and
application-thread rules remain those of [block processing](Processing.md).

[Numerical oracles and qualification](Validation.md) cover the grid, rounding,
hold, chunking, reset, mixing, bypass, and external composition.
