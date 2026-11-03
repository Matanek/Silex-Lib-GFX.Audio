# Give a combustion engine its sound

For configurable parts and assembly changes during playback, use
[Engine.assemble](EngineParts.md). This page describes the prototype retained
by `Engine.create()`.

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
Effort also changes each pulse's pressure-front contribution independently of
overall level. `engine_brake` reduces pulse energy and bite during deceleration. The model does not
calculate a transmission, vehicle speed or wheel torque.

`exhaust` ranges from muffled to open; `roughness` adds noise modulation and controls
the cylinder-specific energy and attack differences and their slow variation
between combustions. Zero disables these differences; weak flow turbulence still
follows pressure. It is not an independent hiss track and fades with the pressure
tail. Their seed is fixed at
construction. These controls preserve pulse phase and acoustic
history. The V8 groups combustion events into two exhaust paths using a
cross-plane bank sequence. Different propagation times and levels preserve this
rhythm in the mix, including mono. Other cylinder counts use a simplified alternating
distribution, without claiming to reproduce every real engine architecture.

## Render and play

`set_state` also accepts `fuel`, normalized availability from 0 to 1, defaulting
to 1. It scales the energy of future combustion events independently of mechanical
RPM. Reducing `fuel` does not alter pulses already injected into the exhaust.
At zero, the engine can keep rotating without new combustion; rendering following
blocks lets pressure and acoustic processing ring out. Ramps provide a gradual
shutdown. This control is neither a fuel mass nor an injection simulation.

Fragment reducing fuel over 350 ms at 48 kHz while the game still supplies
1,800 mechanical RPM:

```sx
source.set_state(1_800.0, ramp_frames:16_800, fuel:0.0)
```

The engine is a `Synthesis.Generator`. `render` fills a mono or stereo PCM view
and can be composed with existing processors or feed a [continuous stream](Continuous.md).
Use generators and their commands on the same application thread. Prepare the
engine, buffers and stream before playback.

`set_state` and `set_character` use linear ramps in frames, defaulting to 480.
The first frame keeps the current value; the target is reached after the chosen
duration. Retargeting starts at the current value. Zero applies an immediate,
potentially audible change. Commands do not alter already generated, queued blocks.

`current_rpm()` returns RPM for the next frame to produce, rather than the exact
frame reaching the speakers. `reset()` clears history, resets the seed and cylinder drift and restores
800 RPM, zero operating controls, fuel 1, exhaust 0.65 and roughness 0.4. To stop gradually,
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
level management when mixing several sources. Each combustion injects a prepared
phase-based exhaust release: brief front, positive blowdown then rarefaction,
with no pitched oscillator injected into the excitation. Duration follows 0.3
of a four-stroke cycle, bounded to 3–60 ms. Effort sets the front/body blend.
Two accumulators retain contributions, followed by pipe histories and three
resonances per path. The pressure derivative uses a fixed time scale so its
weight is preserved when sample rate changes. This acoustic approximation does
not calculate displacement, thermodynamic pressure or actual valve flow.
The generator does not vary supplied RPM: idle regulation belongs
to the game or listening bench. Add ambience separately with
[Processing.Reverb](Reverb.md); no reverberant space is imposed.

The model loads no recording and does not simulate gas flow. Responses and
coefficients are prepared at construction. Cost follows audio frames and
combustion events, hence RPM and cylinder count as well.

The approach is inspired by the excitation/noise/coloration separation studied
in [Engine Simulator](https://github.com/ange-yaghi/engine-sim), using an independent
simplified excitation. No code or sound file from that project is embedded.
