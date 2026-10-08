# Changelog

## [Unreleased]

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

- `Audio.try_decode` loads owned encoded bytes; `Audio.try_load` allows handling failures without stopping the program. Handles are scoped to their Audio instance.

- `Audio.create` creates a reusable sound from mono or interleaved `float32`
  samples, with a configurable sample rate and channel count. The sound owns its
  copy and supports the existing playback controls.
