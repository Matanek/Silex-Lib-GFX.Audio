# Build an engine sound from parts

`Synthesis.Engine.assemble` prepares an engine from typed parts. The game then
supplies RPM, load, throttle and fuel. Generation works without the workshop,
recorded sounds or a helper process.

The [complete example](../../Examples/EngineAssembly.sx) assembles a V8, replaces
a silencer and plays a continuous stream. From the workspace root:

```sh
silex run Packages/GFX.Audio/Examples/EngineAssembly.sx --release
```

Pass `--check` to its compiled executable to exercise the same consumer without
opening an audio device.

## Start from a vehicle signature

`GFX.Audio.Synthesis.EngineVehicles.catalogue()` supplies 17 acoustic profiles:
three/four-cylinder petrol and turbo diesel city cars, turbo I4, flat-six,
cross-plane V8, V10 and V12 sports cars, 125/250/500 two-stroke and 250/500
four-stroke motocross bikes, I4/V4 race motorcycles and 1,200/1,800 cc V-twin
customs. Each `Profile` contains `id`, `name`, `parts`, `idle_rpm`, `redline_rpm`,
`response_seconds` and `roughness`. IDs are independent of interface labels.
RPM limits and response time guide the consumer's bench; the generator does
not simulate a transmission.

Fragment after importing `GFX.Audio.Synthesis` and
`GFX.Audio.Synthesis.EngineVehicles`:

```sx
let profile = EngineVehicles.catalogue()[9]
var engine = Synthesis.Engine.assemble(profile.parts)
engine.set_character(1.0, profile.roughness, ramp_frames:0)
engine.set_state(6_000.0, throttle:0.85, load:0.7)
```

This profile is a 250 cc two-stroke motocross single. Generation remains fully
procedural. Profiles are stylized archetypes without recordings or certified
reproduction of commercial vehicles. This prototype is separate from the
[reference thermal chain](Vehicles.md) now used by the vehicle workshop to
preserve EngineLibrary's sound.

## Choose an assembly and replace a part

Fragment after importing `GFX.Audio.Synthesis` and
`GFX.Audio.Synthesis.EngineParts`:

```sx
var parts = EngineParts.v8()
parts.exhausts[0].silencer = EngineParts.Silencer(
    volume_litres:18.0, absorption:0.8)
var engine = Synthesis.Engine.assemble(parts)
engine.set_state(3_200.0, throttle:0.8, load:0.6)
```

`EngineParts.v8()` provides a 7.45 L cross-plane V8 with two exhausts.
The paths have different lengths and outlet levels of 1 and 0.1, matching the
Chevrolet reference bench. `Exhaust.outlet_level` (0..1, default 1) controls the
heard contribution of each outlet; this listening level does not change
displacement or firing. Identical paths at equal levels can erase the individual
bank rhythm when summed to mono.
`EngineParts.motocross()` and `motocross(Cycle.two_stroke)` provide approximate
450 four-stroke and 250 two-stroke singles. These are acoustic starting points,
not certified reproductions of commercial vehicles. `Assembly()` also provides
a configurable four-stroke single.

The engine implements `Synthesis.Generator`: render PCM blocks, compose existing
processors or feed a `StreamProducer`. Commands and rendering belong to the
same application thread.

## Understand each part’s role

| Part | Parameters | Model effect |
| --- | --- | --- |
| `Block` | Cylinders, bore/stroke in mm, cycle, firing, banks | Displacement, pulse cadence and distribution |
| `Head` | Chamber in cc, combustion in ms, `ignition`, `sharpness` | Geometric compression, energy and attack; compression ignition clatter |
| `Intake` | Runner `Pipe`, airbox litres, filter absorption | Propagation, resonance and pulsed intake noise |
| `Exhaust` | Header and main `Pipe`, `Silencer`, `outlet_level`, `expansion_litres` | Delays, reflections and optional expansion resonance |
| `Silencer` | Litres, absorption 0..1, `baffles` | Chamber resonance, attenuation and successive baffle filters |
| `Mechanics` | Block mass in kg, damping, `clatter`, `whine` | Block resonance, noisy clatter and rotation-related whine |
| Optional `Turbo` | Wheel mm, blades, maximum bar, inertia seconds | Whistle, spool response and release noise |

Combustion and intake share the crankshaft clock. At equal RPM, a two-stroke
fires every revolution and a four-stroke every two revolutions. Intake and
mechanics continue during fuel cut while the game supplies nonzero RPM. The
branches are mixed after processing; they are not unrelated sound tracks.

`Block.displacement_litres()` computes displacement. `Assembly.compression_ratio()`
computes `1 + swept volume per cylinder / chamber volume`. `Head.chamber_cc`
describes one chamber. This is a geometric ratio; effective two-stroke
compression would also depend on port timing.

Ducts use attenuated reflections and round-trip delays at 343 m/s; chambers use
prepared resonances. Excitation, losses, mechanics and turbo are acoustic
approximations. The model does not calculate valves, gas flow, torque or full
thermodynamics. Two-stroke expansion adds a volume-related resonance; it does
not simulate cones or scavenging. Baffles are acoustic filtering stages without
back-pressure calculations. Timbre quality and coverage require listening separately
from the availability of configurable parts.

## Drive the engine and isolate branches

`set_state(rpm, throttle:0, load:0, engine_brake:0, ramp_frames:480, fuel:1,
boost:0)` takes finite commands. RPM spans 0..20,000; other controls span 0..1.
`boost` is a normalized acoustic request with the turbo's configured inertia.
The game owns vehicle dynamics.

`set_mix(EngineParts.Mix(...), ramp_frames:480)` sets `exhaust`, `intake`,
`mechanics` and `turbo` levels separately, each in 0..1. Set three to zero to
isolate the fourth. `set_character(exhaust, roughness)` retains its 0..1 controls:
global exhaust openness and combustion variation. `roughness` varies combustion
energy and adds a small rotation ripple. Ramps preserve phases and
acoustic tails.

`fuel:0` stops future combustion. For a full stop, also supply falling RPM and
render the tail. `current_rpm()` describes the next produced frame, not the
exact loudspeaker position.

## Replace parts during playback

Editing a copied definition does not change an existing engine:

```sx
parts.exhausts[0].pipe.length_mm = 1_000.0
engine.set_parts(parts, transition_frames:2_400)
```

`set_parts` validates and prepares buffers and coefficients on the calling
thread. At 48 kHz the default crossfade lasts 50 ms. The new assembly inherits
RPM, control ramps and crankshaft phase; its resonances start within the fade.
Its configured mix takes effect with it.

During a fade, only one next request is retained; a newer request replaces it.
At most three models are prepared and two are rendered simultaneously.
Durations span 0..16,777,216 frames; zero replaces immediately and may click.
Splitting blocks does not change transition PCM. Rejection preserves the current
sound.

`parts()` returns the last requested definition. `cylinders` describes the model
currently fading in. `reset()` keeps the last requested assembly, cancels fades,
clears history and restores 800 RPM, zero throttle/load/brake/boost, fuel 1,
openness 1, roughness 0.15 and that definition's mix. It is not a gradual shutdown. Releasing the last reference frees prepared
storage.

## Validate dimensions

`Assembly.validate()` and `assemble` return `invalid_input` before mutation for
invalid definitions. Use `try` to retain and handle the error.

- 1..16 cylinders; bore 20..200 mm, stroke 20..250 mm;
- chamber 1..500 cc, combustion 0.1..8 ms, geometric compression 2..25;
- 1..4 exhausts; pipes 20..5,000 mm long and 5..250 mm in diameter;
- silencer chamber and airbox 0.05..100 L; absorption 0..1;
- mechanical mass 1..2,000 kg, damping 0..1;
- turbo wheel 20..150 mm, 2..16 blades, pressure 0.1..4 bar, inertia 0.01..5 s.

`Head.ignition` defaults to `Ignition.spark`, or can be `Ignition.compression`.
`Head.sharpness`, `Mechanics.clatter` and `Mechanics.whine` span 0..1
(default 0). `Silencer.baffles` accepts 0..8 (default 0);
`Exhaust.expansion_litres` accepts 0..30 L (default 0, resonance disabled).
Non-finite values are rejected. Mechanics approximate radiated noise;
these controls do not determine engine power.

An explicit firing order is a permutation of cylinder numbers 1..N. Explicit
angles, one per event, start at zero and increase within the 720° or 360° cycle.
An empty angle list means evenly spaced events. `exhaust_banks` maps each
cylinder to a zero-based exhaust index; an empty list routes all cylinders to
the first exhaust.

Formats span 22,050..192,000 Hz, mono or stereo. Seed and amplitude 0..1 are fixed
at preparation. Pipe pressure is transformed into outlet radiation with a smoothed attack and
a common playback calibration. This remains an acoustic approximation; it does
not guarantee that every small geometry change will be audible in a full mix.
Isolate the branch and compare at identical RPM/load before judging a control.

Headroom before the limiter preserves more of the loaded attacks; the parts
path's level is reduced relative to the previous model.
Output is bounded by amplitude, default 0.4. Blocks must contain
complete frames; empty blocks do not advance state. The original `Engine.create()`
factory retains the four-stroke prototype and its [existing contract](Engine.md);
`assemble` opens the parts-based path.

## Storage and measurement

Buffers and coefficients are prepared at construction or by `set_parts`.
The macOS ARM64 Debug/Release check observes zero allocations during the first
block, 1,000 blocks with state and mix changes, a prepared crossfade and reset.
Preparation and part replacement allocate and belong outside a real-time audio
callback. The counter covers the calling thread and excludes SDL, `Audio.write`,
stream feeding and UI. See [resource qualification](Resources.md).
