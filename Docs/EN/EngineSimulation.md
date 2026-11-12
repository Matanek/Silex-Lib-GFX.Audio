# Simulate a cylinder assembly

`GFX.Audio.EngineSimulation` provides an experimental four-stroke engine
model. Specify each cylinder's geometry and firing phase, then create a
simulator. The starter, ignition, throttle and resisting torque drive the
crankshaft. Set `hold_rpm` to compare sounds at a fixed speed. Releasing it
resumes free rotation from the current speed.

```sx
var engine = EngineSimulation.Simulator.create(
    EngineSimulation.Assembly(cylinders:[
        EngineSimulation.Cylinder(),
        EngineSimulation.Cylinder(firing_degrees:180.0)
    ]))
engine.set_controls(EngineSimulation.Controls(starter:true, ignition:true, throttle:0.2))
```

To shape the exhaust, give `Assembly.exhausts` one to four
`EngineParts.Exhaust` values and assign each cylinder by its zero-based
`exhaust_index`. The pipe dimensions and silencer shape the pressure
release from each group of cylinders. `outlet_level` controls the
outlet's acoustic coupling. An empty list uses the generic resonance
on index zero.

```sx
use GFX.Audio.Synthesis.EngineParts

let first = EngineParts.Exhaust(pipe:EngineParts.Pipe(length_mm:1_180.0, diameter_mm:50.0))
let second = EngineParts.Exhaust(outlet_level:0.35)
var twin = EngineSimulation.Simulator.create(EngineSimulation.Assembly(
    cylinders:[EngineSimulation.Cylinder(), EngineSimulation.Cylinder(firing_degrees:180.0, exhaust_index:1)],
    exhausts:[first, second]))
```

`set_exhaust(paths, cylinder_outlets)` changes the exhaust while the
engine runs. Give a zero-based outlet index for each cylinder in assembly
order. The simulator installs the first setup at startup and crossfades
later changes over 40 ms. Calls during a transition keep the latest
request for the next crossfade. Speed, firing phase, and controls continue
through the change. `reset()` clears the state of the last requested
exhaust.

The simulator is a 48 kHz mono `Synthesis.Generator`. Use `render()` for the
mix or `render_sources()` for the three isolated sources. Each call advances
the engine by the number of frames in the buffer. `cylinder(index)` reports
the phase in degrees within the 720° cycle, piston displacement from top
dead centre and the most recent firing frame when available. `reset()`
restores the initial clock, controls, mechanical state and filters. Drive
and render each instance from the same thread.

The slider-crank geometry determines piston displacement and velocity.
Simplified compression and combustion provide cylinder pressure. The load
through the connecting rod changes sliding friction and moves the piston
skirt laterally within its clearance. Contact with the wall excites the
block's resonances. Intake flow depends on piston movement and a simplified
valve opening. Its pulses excite the plenum's Helmholtz resonance and
the runner's quarter-wave mode, with flow-dependent turbulence and a
travel delay to the intake mouth. The throttle plate attenuates radiation
at small openings. Intake dimensions are estimated from
engine displacement.
At each firing, bounded changes in charge and burn duration affect pressure
and torque. Variation is stronger at low throttle. Each cylinder repeats
its sequence after `reset()`.

Pressure released at exhaust opening excites the third source. Bore
affects burn duration and acoustic coupling. Blowdown lasts longer in
larger cylinders, and pressure shapes the opening front. The generic
outlet's resonances fall as dimensions increase. Configured outlets model
reflections and damping in their pipes. The default parameters describe
a single-cylinder test engine.
