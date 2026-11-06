# Changelog

## [Unreleased]

- `output_format()` exposes the mix sample rate and channels; `render_f32le()` provides owned offline PCM for encoder integrations, without normalization or timeline changes.

- Adds `Engines.Library.driven_engine` and `OperatingState` for game-owned RPM
  and combustion effort. Retains the validated thermal/acoustic chain with
  continuous crank phases and bounded RPM changes, supports the existing FIFO
  rendering path, and keeps stock free/road modes. New native v3 banks expose
  this input; v1/v2 banks remain usable for their previous modes.

- Adds `Engines.Gearing` for per-gear ratios and final drive at road-engine
  creation. Exposes stock and active gearing, validates before spawning,
  preserves configuration on reset, and retains unmodified stock PCM. New
  native banks support gearing overrides; v1 banks remain usable with defaults.

- Exposes the validated bench's optional automatic/manual transmission through
  `Engines.Library.engine`, with gear requests, braking and synchronized road
  telemetry. Preserves neutral, overspeed rejection and safe reengagement;
  free-bench generation remains the default.

- Extracts the validated engine-bench chain into `GFX.Audio.Engines`: deployable
  native engine library, eight profiles, original exhaust responses, measured
  4T intake and output processing. Adds synchronous generation and bounded
  asynchronous requests. The former autonomous bench remains the PCM oracle;
  the parts workshop is experimental. Native bank construction/execution is
  currently qualified on macOS ARM64, not yet distributed for every target.

- Corrects part-based exhaust pressure radiation and smooths pulse attacks;
  adds per-outlet listening levels and preserves unequal bank contributions in
  the V8 preset. Tests distinguish isolated timbre changes from turbo level changes.

- Adds `Synthesis.Engine.assemble` and typed `EngineParts`: block/cycle/firing,
  head, intake, pipes, silencers, mechanics and optional turbo. Game-controlled
  RPM/load/fuel/boost, branch mixing and bounded crossfades for part replacement;
  independent consumer, workshop demo and FR/EN guide. Retains the original
  `Engine.create` prototype and the standalone engine-sim listening bench.

- Adds `Synthesis.Engine`, a prototype four-stroke engine controlled by RPM,
  throttle, load and engine braking: two-exhaust V8 profile, 1–12 cylinders,
  adjustable noise texture and coloration, continuous ramps, RPM- and effort-dependent
  pressure releases, exhaust turbulence, cylinder signatures and slow variation,
  progressive fuel control for future combustion while preserving engaged events,
  reproducible PCM and a standalone example
  with FR/EN guides.

- Adopts one `Result` declaration: an ordinary call returns the value or
  stops the program on failure; `try call()` keeps the `Result`. Existing calls
  storing results and propagating failures are made explicit. This revision
  requires the development toolchain with these `try` semantics; publication
  must coordinate compiler and package versions.
  Recoverable `try_*` variants and direct wrappers with the same signature
  converge under the ordinary name. Boolean, optional, and native variants
  retain their contracts.

- Adds `Music.Instruments.guitar`, `violin` and `drums`: naturally decaying plucked strings, sustained violin with vibrato and a seven-piece `Music.Drum` kit. Shared polyphony/commands, family-specific settings, examples outside Docs, FR/EN guides and numerical/resource oracles.

- Add `Music.Instruments.piano` and `Synthesis.PianoInstrument`: polyphonic procedural piano with strike dynamics, natural decay, brightness and sustain pedal. Share the sine command pool without changing its PCM; piano/MIDI examples, FR/EN guides and numerical validation.

- Add musical constants `Music.Key.C5`, `Cs5`, `Bb4` and direct `Music.key` / `Music.keys` conversions from note names, with `try Music.key(...)` / `try Music.keys(...)` to keep recoverable Results from the same operations; ordinary invalid calls panic. Documented C4=60 convention, accidentals and recoverable errors, with PCM identical to numeric MIDI input.

- Move the 21 runnable examples and their MIDI score to `Examples/`; `Docs/` contains no `.sx` files. Update bilingual links and commands without changing sound sources.

- Qualifies musical-path costs: preparation and repeated playback, long scores and owned feeding; DSP counters separated from native/offline allocations, ARM64 and x64/Rosetta measurements, FR/EN guides and a reproducible protocol.

- Add `Music.Player`: explicit timbre, instrument or MIDI routing; bounded PCM feeding owned by Audio, pause/resume/stop/replay controls, standalone wait, observable state and errors. The Audio plugin preserves a supplied resource and feeds playback on the application thread. Bilingual guide and interactive example without consumer pumping.

- Distinguish sound recipes and instruments in `Music`: `prepare(audio, using:...)` accepts either, and `Music.Instruments.sine` creates the existing polyphonic instrument with durations in seconds and amplitude preserved by reset. The Music candidate's `instrument:` parameter becomes `using:`. Four executable variants and checks for voices, gain, units and errors.
- Add `GFX.Audio.Music`: notes in beats and tempo, customizable retro/triangle/sine timbres, short-sound preparation with internal buffers and independent playbacks; user instruments and effects reuse existing protocols. Qualified limits and FR/EN examples.

- Qualifies synthesis resources: controlled Debug/Release ARM64 allocation gate including MIDI events; stereo 16/64-voice workload with five effects measured separately from PCM transfer, with documented limits and headroom.

- Adds a procedural recipe guide from beeps to MIDI scores, including units, level control and extension contracts.

- Optional MIDI volume, expression and balance smoothing, configured in frames; the melody uses 5 ms to avoid the click caused by an expression drop on sustained voices. Note dates remain unchanged, with continuous targets across blocks and programs.

- MIDI 1.0 control in GFX.Audio: bounded SMF 0/1 PPQN scores, tempo and stable merging without rounding drift, channel/program-selected instruments, FIFO identities, sustain/gain/balance/bend, explicit endings and tails; memory and stream rendering without banks or a system MIDI decoder.

- Continuous gain/pitch controls and ramps: retarget from the current level, preserve phase and use frame commands. A bounded stream producer retains suffixes after partial writes, with distinct counters, chosen duration and explicit lifetime; engine/chord recipes avoid restarting short sounds.

- Polyphonic sine instruments: identities, velocity, ADSR, sustain, bend and bounded voice reassignment with configurable transitions. A frame-clock command score provides stable ordering, recoverable lateness/capacity errors, composable user instruments and a melody without banks.

- Composable compressor and limiter: threshold/ratio, attack/release, explicit makeup, sample ceiling, linked channel peaks and an accent comparison without sound banks.

- Composable algorithmic reverb: prepared room size, adjustable decay and damping, mix/bypass, per-channel history, echo/tail/color oracles and plucked notes without sound banks.

- Composable modulated delay for chorus and flanger: causal interpolation, signed feedback, wet/bypass with advancing history, prepared capacity, impulse/tone oracles and a procedural chord without sound banks.

- Stereo pan transfers the opposite channel with sine/cosine gains, preserving center and exact poles; wet mix/bypass, recoverable overflow and a block-based demonstration.

- Composable soft saturation and hard clipping: drive, output gain, wet mix and bypass, stable float32 evaluation and asset-free examples.

- Composable bitcrusher: 2–24-bit resolution, independent sample hold across blocks, wet mix and bypass; signed 256-level grid at 8 bits, reset and an asset-free retro recipe.

- Composition adds a weighted mix, ordered extensible processing chain, linear curve, amplitude modulation and sine FM with mono controls, persistent state and prepared buffers.

- Synthesis adds triangle, duty-cycle square and sawtooth waves with bounded harmonics below Nyquist, plus reproducible pink noise. An executable palette compares timbres; an independent spectral oracle checks waveforms and noise in Debug and Release.

- `GFX.Audio.Synthesis` adds an extensible generator, sine oscillator, seeded white noise and ADSR envelope. Rendering uses prepared views with persistent block state, recoverable settings and examples without sound banks.

- Stream/group integration preserves independent pauses, stable end identities and handle ownership. Seconds remain available for large source frame durations.

- Stateful block processing adds a low-pass filter, delay/echo, three-band equalizer and peak/RMS analysis, using application-thread mutable views, recoverable settings and explicit reset.

- Audio.offline and render produce owned PCM blocks without a device, normalization or hidden clipping.

- Playback groups compose gains and independent pause reasons, with reassignment and destruction preserving individual settings.

- Source format and explicit duration, start/seeking in frames and bounded end observation. Seeking discards converted frames from the previous position.

- Bounded PCM streams: copied blocks, recoverable backpressure, pause/resume, closing with resampler drainage, consumption and discard counters. Private provider rebuilt for six targets; corrected 3D coordinates and multichannel stereo reversal.

- `Audio.decode` loads owned encoded bytes; `try audio.load(...)` allows handling failures without stopping the program. Handles are scoped to their Audio instance.

- `Audio.create` creates a reusable sound from mono or interleaved `float32`
  samples, with a configurable sample rate and channel count. The sound owns its
  copy and supports the existing playback controls.
