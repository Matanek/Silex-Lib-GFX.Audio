# Changelog

## [Unreleased]

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
