# Give a combustion engine its sound

`Synthesis.Engine` generates a four-stroke engine from RPM and operating context.
The game supplies RPM, throttle, load and engine braking without describing
mechanical parts. This first acoustic model is a prototype requiring listening
evaluation.

The [standalone example](../../Examples/Engine.sx) revs a V8 and returns to idle
in one continuous playback. From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Examples/Engine.sx --release
```

## Supply the game's RPM

Fragment in a program importing `GFX.Audio.Synthesis`:

```sx
var source = Synthesis.Engine.create()
source.set_state(3_200.0, throttle:0.8, load:0.6, engine_brake:0.0, ramp_frames:480)
source.set_character(exhaust:0.7, roughness:0.4, ramp_frames:480)
```

RPM sets pulse frequency. `throttle` describes throttle opening and `load` the
effort delivered: changing load at constant RPM changes the signal.
`engine_brake` reduces pulse energy during deceleration. The model does not
calculate a transmission, vehicle speed or wheel torque.

`exhaust` ranges from muffled to open; `roughness` controls noise modulation and
combustion energy variations. These controls preserve pulse phase and acoustic
history. The V8 groups combustion events into two exhaust paths using a
cross-plane bank sequence. Other cylinder counts use a simplified alternating
distribution, without claiming to reproduce every real engine architecture.

## Render and play

The engine is a `Synthesis.Generator`. `render` fills a mono or stereo PCM view
and can be composed with existing processors or feed a [continuous stream](Continuous.md).
Use generators and their commands on the same application thread. Prepare the
engine, buffers and stream before playback.

`set_state` and `set_character` use linear ramps in frames, defaulting to 480.
The first frame keeps the current value; the target is reached after the chosen
duration. Retargeting starts at the current value. Zero applies an immediate,
potentially audible change. Commands do not alter already generated, queued blocks.

`current_rpm()` returns RPM for the next frame to produce, rather than the exact
frame reaching the speakers. `reset()` clears history, resets the seed and restores
800 RPM, zero operating controls, exhaust 0.65 and roughness 0.4. To stop gradually,
command zero RPM, render the acoustic tail, then close the stream; the model does
not generate an end notification itself.

## Settings and limits

`Engine.create(format, cylinders:8, seed:42, amplitude:0.4)` accepts:

- 22,050–192,000 Hz, one or two channels; default 48 kHz stereo;
- 1–12 cylinders, fixed at construction;
- an integer seed, reused by reset;
- a finite amplitude from 0 to 1, fixed at construction.

RPM must be finite in 0–12,000; other controls must be finite in 0–1. Ramp
durations accept 0–16,777,216 frames. Invalid input returns `invalid_input` before
mutation; use `try` to keep that error. Blocks must contain complete frames;
an empty block does not advance the engine.

Soft saturation bounds each sample by the chosen amplitude. It does not replace
level management when mixing several sources. Rendering keeps two pipe histories
and three resonances per path; it loads no recording and does not simulate gas
flow. Coefficients are prepared at construction; rendering cost follows audio frames.

The approach is inspired by the excitation/noise/coloration separation studied
in [Engine Simulator](https://github.com/ange-yaghi/engine-sim), using an independent
simplified excitation. No code or sound file from that project is embedded.
