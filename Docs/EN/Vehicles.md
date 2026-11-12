# Create a vehicle engine with the reference sound chain

`GFX.Audio.Engines.Vehicles` prepares a thermal engine with EngineLibrary's
simulator. The `454` profile preserves its original definition and PCM. City
cars add a quiet exterior rendering; diesel uses a hybrid voice derived from
a TDI recording. Profiles still require listening qualification.

From the workspace root, the [device-free example](../../Examples/VehicleEngine.sx)
produces PCM blocks and prints final RPM:

```sh
silex run Packages/GFX.Audio/Examples/VehicleEngine.sx --debug
```

Use [AudioEngineSimulator](https://github.com/Matanek/Silex-Examples/tree/main/Sources/AudioEngineSimulator)
to listen to the demo presets and export them as WAV files.

## Choose and drive an engine

Fragment after importing `GFX.Audio.Engines` and `GFX.Audio.Engines.Vehicles`:

```sx
var engine = Vehicles.create("cross-250-4t", displacement_cc:300.0)
var controls = engine.controls()
controls.running = true
controls.throttle = 0.6
controls.load = 0.2
engine.set_controls(controls)
```

`create(key:"454", displacement_cc:null)` returns a free-bench `Engines.Engine`.
It retains the `render`, `enqueue` and `render_ready` paths
[documented for reference engines](Engines.md). Simulation owns crankshaft
motion; commands do not replace RPM with an artificial curve. This factory
does not configure a road transmission.

`Controls.throttle` is an optional continuous pedal in 0..1. When supplied, it
replaces `accelerating`; `null` preserves the historical on/off command exactly.
Ignition off closes the throttle. Non-finite or out-of-range values are rejected
before mutation. Other controls retain their meaning: load, texture, exhaust
response, intake, volume and ambience. `exhaust` blends raw and response-filtered
audio; it is not a baffle count or back-pressure setting.

## Add a transmission to the bench

Create the engine with `Vehicles.create("454", transmission:Engines.Transmission.manual)`.
It starts in neutral (`gear = 0`). Read its controls with `controls()`,
select a gear from 1 to `gearing.ratios.count()`, and pass the controls
to `set_controls()`. Shifting keeps the engine state. `drive_state()`
reports the engaged gear and speed. In neutral the
engine revs freely and the bench load setting takes effect again. When selecting a gear from neutral,
the clutch engages progressively while the pedal stays active. Four-stroke
motocross singles and the 250 cc two-stroke use the 8.5 final reduction.
The American V8 (`sport-v8`) uses the six ratios and 3.42 final drive of
the Corvette paired with the GM LS. When upshifting, the bench briefly cuts
ignition while the clutch is open to let RPM fall.

With a manual transmission, `request_gear(gear)` selects the gear at
the current vehicle speed. Gear zero selects neutral. On a downshift
the wheels can drive the engine beyond the ignition cut-off. The limiter
cuts combustion and the clutch transfers engine braking.

## Catalogue and displacement

`catalogue()` returns 18 `Profile` values with `key`, `name`, `displacement_cc`,
`cylinders`, `strokes`, `idle_rpm`, `redline_rpm` and `note`:

- reference `454`; city cars `city-i3`, `city-i4`, `city-diesel`;
- sports cars `sport-turbo-i4`, `sport-flat6`, `sport-v8`, `sport-v10`, `sport-v12`;
- motocross `cross-125-2t`, `cross-250-2t`, `cross-500-2t`, `cross-250-4t`, `cross-500-4t`;
- race bikes `race-i4`, `race-v4`; customs `custom-1200`, `custom-1800`.

`Profile.idle_rpm` describes nominal idle, not a bench-hold command. Keeping
`Controls.idle_rpm` at 800 leaves idle free, as in EngineLibrary. Automatically
copying nominal idle into this command would engage the dynamometer.

Displacement is total engine capacity in cc. It accepts finite values in
50..12,000 cc and checks the chosen model's geometry limits (20..200 mm bore,
1..500 cc chamber for resized definitions). It changes dimensions and chambers
in the simulator. Singles also adapt friction, inertia and bench load to their
size. `reset()` retains the definition and controls. Unknown profiles or invalid
displacement return `invalid_input` before an engine process is created.

Reference `454` retains its original geometry and rejects a different capacity.
Choose `sport-v8`, built from the GM LS definition, for an editable V8.
V10/V12, race I4 and custom profiles reuse the bank's LFA, Ferrari 412 T2,
Hayabusa and Harley definitions. Geometry and chambers may be adapted;
these names do not certify a commercial reproduction.

## Listen to city cars

Petrol city cars use a smaller intake, shorter valve timing and more restrictive
exhaust than the sports I4. Exterior rendering attenuates level and upper
harmonics. This close listening perspective does not model spatial propagation
or a cabin. Levels are not normalized: a city car remains quieter than a sports
car at the same listening volume.

`city-diesel` combines that muffled exhaust bed with eight acoustic excitations
derived from the supplied TDI reference. Simulated RPM drives their cadence,
load their level, and ignition cut fades the voice. `texture` controls variation
between excitations; `exhaust` also muffles their response. This hybrid rendering
contains transformed recorded sound and does not replay the full montage.
Reset clears filters and phases.

The recorded engine is unidentified. Its excerpt therefore certifies neither
1.6 L displacement nor a specific Volkswagen model. Catalogue labels and `note`
identify the hybrid path. The voice does not affect the 454, sports cars,
motorcycles or 500 four-stroke motocross profile.

## Preparation and limits

Creation prepares a private copy of native resources and starts one process
per engine. It allocates and may wait for file operations; keep it outside
audio callbacks and per-frame paths. Definitions are fixed at creation. An
editor should replace geometry with the engine stopped. Interactive rendering
consumes ready blocks; synchronous rendering suits offline export. Format stays
44,100 Hz stereo.

The native bank remains available only on macOS ARM64. Other targets return
the availability error from `Engines.Library.open()`. Standard embedded binary
and assets are retained; the factory edits only its temporary copy.

Diesel mechanics remain approximate: the simulator still uses spark ignition
and does not model diesel auto-ignition or injection. The recorded voice changes
acoustic texture, not the thermodynamic model. The sports I4 does not simulate
boost. Two-strokes retain the
bank's simplified port/scavenging model without conical expansion chambers.
These limits also appear in `note`.

The consumer test compares every `454` sample with `Library.engine("454")`
during startup, acceleration and ignition cut. It also exercises all 18
architectures, continuous throttle, errors and reset of a customized capacity.
`CityVoices.sx` measures petrol levels, distinguishes diesel transients and
checks reset, shutdown and parity between synchronous and ready rendering.
This proves reference preservation and operation; it does not replace listening
to variants. The `Synthesis.EngineVehicles` prototype remains a separate
generator and no longer supplies the workshop's sound.
