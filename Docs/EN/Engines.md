# Reuse the validated engine-bench sounds

`GFX.Audio.Engines` retains the first bench's sound chain: engine simulation,
profiles, exhaust responses, four-stroke intake and output mixing. Consumers
copy neither its calculations nor the demo's filters. The eight profiles and
existing controls are preserved independently of the experimental parts workshop.

## Prepare the library

The library is a deployable directory containing the renderer and its resources.
Build and stage it using the package-owned tools described in
[native preparation](../../Native/EngineSimulator/README.md). They use no files
from Silex-Examples. Deploy the whole directory with the application; its path
may be absolute or relative to the current directory. The API does not implicitly
search the demo repository.

The [standalone example](../../Examples/EngineLibrary.sx) consumes only this
package. From the workspace root:

```sh
silex compile Packages/GFX.Audio/Examples/EngineLibrary.sx --release -o Build/EngineLibrary-Consumer
Build/EngineLibrary-Consumer /absolute/path/to/EngineLibrary
```

It exercises the engine offline without a window or audio device.

## Select an engine and its controls

Fragment after `use GFX.Audio.Engines`:

```sx
var library = Engines.Library.open("Audio/EngineLibrary")
var engine = library.engine("454")
var controls = engine.controls()
controls.running = true
controls.accelerating = true
engine.set_controls(controls)
```

`library.profiles()` returns profiles with keys, labels, redline, tachometer
scale, idle speed, gear count and stroke cycle. Current keys are `454`, `berline`, `sport`,
`cruiser`, `moto`, `truck`, `cross4` and `cross2`. Unknown profiles are rejected.
Each engine owns its simulation, phases and histories independently.

`controls()` returns a copy. `set_controls()` validates every value before
mutation and rejects non-finite values. Controls retain the validated bench's
meaning:

| Control | Effect |
| --- | --- |
| `running` | Ignition and starter; switching off retains rotation and acoustic tails |
| `accelerating` | Open or released throttle with the native engine response |
| `idle_rpm` | Free-bench holding speed, 700..4,000 RPM; not an instantaneous RPM override |
| `load` | Free-bench load, 0..1 |
| `texture` | Profile air noise and jitter, 0..1; physical combustion remains variable |
| `exhaust` | Raw/filtered exhaust blend, 0..1, with existing balancing and smoothing |
| `intake` | Measured `cross4` aspiration, 0..1; other profiles do not supply this branch |
| `volume` | Smoothed output gain, 0..1 |
| `ambience` | Short reverb mix, 0..1 |

Initial values match the bench: ignition off, throttle released, holding speed
800, load 0.2, texture/exhaust 1, volume 0.7 and ambience 0. Initial intake comes
from the profile. The application owns shortcuts, focus loss and vehicle-change
guards.

## Add an optional transmission

`library.engine("454")` retains free-bench mode by default. To reuse the original
bench's road context:

```sx
var engine = library.engine("454", transmission:Engines.Transmission.automatic)
var controls = engine.controls()
controls.running = true
controls.accelerating = true
engine.set_controls(controls)
```

Transmission presence is fixed at creation. `controls.transmission` can then
switch between `Transmission.automatic` and `Transmission.manual` without
recreating the simulation. In manual mode, `controls.gear` is the requested gear,
from 0 (neutral) to `engine.gearing.ratios.count()`. `controls.braking` brakes the bench
vehicle. Road mode retains the existing longitudinal calculations without a
Physics dependency. Free-bench holding speed and load do not drive road mode.

`engine.drive_state()` returns `null` in free mode. In road mode it supplies
`gear`, `speed_kmh`, `shifting`, `shift_refused` and `shift_count` for the last
received block. Overspeed protection may reject a request: do not overwrite the
requested gear with the actual gear on every reply. After selecting N while
moving, successive + commands can therefore reach a safe gear. A rejected
request cannot engage later without a fresh command.

To return to free mode, create another engine after switching off and stopping
the vehicle. Changing transmission presence, requesting an out-of-range gear or
braking in free mode is rejected before mutation. `reset()` retains mode and
controls while recreating the stopped context.

## Choose the gearing

Each profile exposes its original values in `profile.gearing`: `ratios` lists
the gears from first to last, and `final_drive` is the final-drive ratio. Without
an override, these values and the bench output remain unchanged.
`engine.gearing` describes the configuration actually in use.

For shorter gearing, supply a configuration when creating the road engine.
Fragment after opening `library`:

```sx
var gearing = Engines.Gearing(ratios:[4.0, 2.5, 1.8, 1.3, 1.0], final_drive:4.5)
var engine = library.engine("454", transmission:Engines.Transmission.manual, gearing:gearing)
```

Ratios and final drive accept finite `float64` values in 0.05..20. A gearbox
contains 1..12 strictly decreasing ratios. Neutral remains command 0, with no
entry in the list. `validate()` checks a configuration; `library.engine()` also
validates it before creating an engine. An override requires a rebuilt v2
native bank. Existing v1 banks remain usable with stock gearing and reject
custom configurations.

A larger numeric ratio shortens the gearing: at the same wheel speed with the
clutch engaged, engine RPM increases. Behavior also depends on engine torque,
the vehicle and drag; a taller gear does not guarantee more acceleration or
speed. Automatic shifting uses the configured gearbox. The stock gear count
remains available as `profile.gears`.

The configuration is fixed at creation and retained by `reset()`. Create another
engine to change it. The demo stages edits until “Appliquer la démultiplication”,
with the engine and vehicle stopped. It also restores stock ratios. Demo edits
use 0.001 precision; the API accepts `float64` values directly.

## Produce blocks without blocking the interface

The fixed format is 44,100 Hz stereo. `Engine` implements `Synthesis.Generator`.
`render()` fills complete frames in the supplied slice, in internal blocks of
at most 480 frames. It waits for calculation; use it offline or in a production
context that can wait.

For an interface, `enqueue(depth:4)` requests up to four blocks of 480 frames.
`render_ready()` fills a 960-sample slice and returns `false` if the next block
is not available. Do not wait in a polling loop inside a graphical frame.
`pending_blocks()` reports outstanding advance. Replenish the chosen depth after
receiving blocks. Retain partial writes to the audio stream before consuming
the next block.

Do not combine `render()` with outstanding asynchronous requests. Partial frames,
depths outside 1..4 and incompatible path changes are rejected before consumption.
Output processing occurs on reception, matching the original bench. Simulation
controls are captured when requests are queued; audio advance therefore adds an
explicit control delay.

`current_rpm()` and `is_starting()` describe the last received block. `reset()`
cancels requests, recreates the simulation and clears histories while retaining
controls. It is immediate and may interrupt the sound. For natural shutdown,
set `running` to `false` and keep rendering the tail. Releasing the last engine
closes its input and releases its renderer process.

## Scope of this extraction

Comparison with the original bench preserves PCM bit for bit for all eight
profiles, including start, throttle, exhaust/texture/load changes, volume,
ambience and shutdown. The old bench remains an independent witness.

This version retains the full simulator and one process per engine. It allocates
and uses IPC; it is unsuitable for a real-time audio callback. Heavy-application
qualification and direct game-provided RPM control remain open. This extraction
has been built and executed on macOS ARM64; other targets remain to be prepared
and tested. Installing the package alone does not yet supply prebuilt native
banks for every OS.
