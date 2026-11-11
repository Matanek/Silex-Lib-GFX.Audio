# Reuse the validated engine-bench sounds

`GFX.Audio.Engines` retains the first bench's sound chain: engine simulation,
profiles, exhaust responses, four-stroke intake and output mixing. Consumers
copy neither its calculations nor the demo's filters. The eight profiles and
existing controls are preserved independently of the experimental parts workshop.

For a vehicle catalogue with customizable displacement, see
[`Engines.Vehicles`](Vehicles.md). Its reference Chevrolet uses exactly the
standard factory described here.

## Use the supplied engines

`Library.open()` opens the eight standard profiles with their simulator and
resources included in the package. The application needs no native preparation
or library path. From the workspace root:

```sh
silex run Packages/GFX.Audio/Examples/EngineLibrary.sx
```

This example produces sound offline, without a window or audio device. The
compiled program contains the required resources and works without the package
sources or its original working directory. The package automatically prepares
its files in a temporary directory owned by the library and retains them while
any engine uses them, including across `reset()`. Releasing them cleans up that
directory. Execution performs no download or native build.

The standard engine is currently supplied and verified on macOS ARM64. On other
targets, `Library.open()` returns `unsupported`; explicit library loading remains
available with the qualification limits below.

## Load a custom library

An external directory remains an advanced option: `Library.open(directory)`
opens a library explicitly supplied by the application. Its absolute path or
path relative to the current directory must be valid; no replacement directory
is searched. Deploy the whole directory with the application.
The [native preparation tools](../../Native/EngineSimulator/README.md) rebuild
the simulator and its resources. They serve package maintenance or preparation
of a custom library.

## Select an engine and its controls

Fragment after `use GFX.Audio.Engines`:

```sx
var library = Engines.Library.open()
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

The single-cylinder 250 two-stroke `cross2` uses an exhaust response calculated
from pipe geometry. The simulator generates pressure from combustion and port
flow. A one-dimensional waveguide calculates reflections at diameter changes.
The geometry is generic and scavenging is simplified. Reflected pressure does
not feed back into the cylinder. `Silex-Examples/Sources/EngineLibrary` plays
this profile and exports two loads at fixed RPM.

`controls()` returns a copy. `set_controls()` validates every value before
mutation and rejects non-finite values. Controls retain the validated bench's
meaning:

| Control | Effect |
| --- | --- |
| `running` | Ignition and starter; switching off retains rotation and acoustic tails |
| `accelerating` | Open or released throttle with the native engine response |
| `throttle` | Optional continuous pedal 0..1; overrides `accelerating` when supplied, `null` retains the historical command |
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

To return to free mode, create another engine. The demo allows this as soon as
ignition is off, without waiting for deceleration: the new context resets RPM
and vehicle speed. Changing transmission presence on an existing engine,
requesting an out-of-range gear or
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

## Supply RPM from a game

When the game already owns engine state, use `driven_engine` instead of the free
bench or its road vehicle. This path requires a v3 bank:

```sx
var engine = library.driven_engine("454")
engine.set_state(Engines.OperatingState(rpm:2_500.0, load:0.65, running:true))
```

`OperatingState` supplies crankshaft RPM, positive combustion effort `load` in
0..1, and ignition `running`. Load controls intake and audible effort at a given
RPM: 0 means released throttle, 1 means maximum requested effort. Engine braking
follows falling RPM and load; there is no contradictory acceleration command.
Values must be finite, with RPM in 0..`profile.ceiling`. Invalid input is rejected
before mutation. `state()` returns the requested state.

Creation starts at zero RPM with ignition off. The game supplies startup,
running and stopping phases. Cutting ignition retains pumping noise while the
game imposes rotation; zero RPM with ignition off lets the acoustic tail decay.
`current_rpm()` reports measured crank speed in the last received block.

The same thermal simulator, profiles and bench processing produce the sound.
A rotation constraint follows the supplied RPM with a slew limit of 20,000 RPM
per second. Phases and histories persist across commands. This path simulates
neither another gearbox nor another vehicle. `render`, `enqueue`, `render_ready`,
`pending_blocks` and `reset` follow the rules below; `reset()` retains the target
state. Existing v1/v2 banks still support the previous benches and reject
`driven_engine`.

The Silex-Examples MonsterTruck demo uses this input with the standard engine
supplied by the package. It passes physical engine RPM and normalized combustion
torque without simulating a second gearbox.

## Produce blocks without blocking the interface

The fixed format is 44,100 Hz stereo. `Engine` and `DrivenEngine` implement
`Synthesis.Generator`.
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

The original extraction was verified bit for bit across eight profiles,
including start, throttle, exhaust, texture and load changes, volume, ambience
and shutdown. The calculated chamber subsequently changed `cross2`'s timbre.

This version retains the full simulator and one process per engine. It allocates
and uses IPC; it is unsuitable for a real-time audio callback. External RPM has
an offline-tested path; listening quality and heavy-application qualification
remain open. This extraction has been built and executed on macOS ARM64; other targets remain to be prepared
and tested. The embedded standard library retains this qualification scope.
