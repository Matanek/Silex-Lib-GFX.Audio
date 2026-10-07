# Changelog

## [Unreleased]

- Source format and explicit duration, start/seeking in frames and bounded end observation. Seeking discards converted frames from the previous position.

- Bounded PCM streams: copied blocks, recoverable backpressure, pause/resume, closing with resampler drainage, consumption and discard counters. Private provider rebuilt for six targets; corrected 3D coordinates and multichannel stereo reversal.

- `Audio.try_decode` loads owned encoded bytes; `Audio.try_load` allows handling failures without stopping the program. Handles are scoped to their Audio instance.

- `Audio.create` creates a reusable sound from mono or interleaved `float32`
  samples, with a configurable sample rate and channel count. The sound owns its
  copy and supports the existing playback controls.
