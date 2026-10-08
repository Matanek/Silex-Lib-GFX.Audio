# Verify audio paths

Run these commands from the `SilexProject` root with the local toolchain that
includes the mutable method-view correction. Verified archives must be present
under `Boundary/`; `Package.json` records paths and hashes. The
[provider guide](../../Native/README.md) covers rebuilding and separate publication.

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy silex test Packages/GFX.Audio/Tests --nocache
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py
python3 Packages/GFX.Audio/Tests/Resources/Validate.py
python3 Packages/GFX.Audio/Tests/SynthesisSpectrum.py
python3 Packages/GFX.Audio/Tests/SynthesisSpectrum.py --debug
python3 Packages/GFX.Audio/Tests/GeneratedSamplesValidation.py
python3 Packages/GFX.Audio/Tests/OfflineValidation.py
```

The suite covers memory loading, handles and owners, timeline, groups and pause,
stream capacity, silence/resume, draining, device-free rendering, processing
and levels. The dummy driver supports playback control checks; PCM comparisons
support mixing and processing guarantees. The dummy video driver also enables
the SDL window coexistence test without desktop access. Rejection checks require a diagnostic
and failure exit code, with timeouts to detect waits that cannot progress.

`ReleaseValidation.py` runs the 86 public `Processing`, `Production`,
`StreamGroups`, `Synthesis`, `Waveforms`, `Composition`, `Bitcrusher`, `Distortion`, `StereoPan`, `ModulatedDelay`, `Reverb` and `Dynamics` oracles
in Release. It selects a deliberately
nonexistent driver:
these oracles use offline rendering and require no device. They cover the
stateful chain and the same scalar producer as a complete source and stream,
including 24→48 kHz conversion, absolute 10⁻⁶ tolerance and frame counters.
Synthesis oracles cover sine waves, reproducible noise, ADSR levels, invalid
blocks, and protocol conformances from an external consumer.

`SynthesisSpectrum.py` uses only Python's standard library and an independent
FFT. Fifteen fixtures at 375, 3,000 and 9,000 Hz check triangle, 25/50/75%
square and sawtooth harmonics: power outside the harmonic bins below 10⁻⁷
and complex spectral error below 2×10⁻⁵ against a separately filtered ideal
waveform. A naive 9 kHz sawtooth fails the aliasing control. Across 131,072
frames at 48 kHz, pink noise must have a density slope between −1.2 and −0.8
and a maximum octave-power ratio below 2.5, between 187.5 and 6,000 Hz; white
noise serves as a control. Run both modes explicitly: `compile` defaults to
Release, while `--debug` selects Debug.

```sh
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target macos-x64 --execute
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target linux-x64
```

`--target` composes and links without execution; `--execute` also runs the
artifact and requires a host-compatible target. Package targets are
`macos-arm64`, `macos-x64`, `linux-arm64`, `linux-x64`, `windows-arm64` and
`windows-x64`. Linking for a target does not prove execution on its system.
The retained qualification below covers the 13 baseline oracles; it does not
automatically qualify synthesis additions for those targets.

`GeneratedTone`, `MemorySound`, `StreamingTone`, `Timeline`, `Groups`, `Offline`,
`ProcessedTone`, `ProceduralSounds` and `WaveformPalette` are executable sources under `Docs/`.
For example:

```sh
SDL_AUDIODRIVER=dummy silex run Packages/GFX.Audio/Docs/ProcessedTone.sx --release --nocache
SDL_AUDIODRIVER=__silex_no_audio_driver__ silex run Packages/GFX.Audio/Docs/Offline.sx --release --nocache
```

These proofs cover PCM and logical mixer state. Counters do not measure the
exact speaker presentation time. Processing runs on the application thread;
the provider never calls a Silex callback on its audio thread. Data and
primitives remain independent of instruments, sequencing or MIDI.

## Synthesis qualification of October 8, 2026

The DSP in Audio `ada2c3570df1ffa3ac7065a11ab9892abff40af7` is unchanged.
With Silex `60d90abf1d7a689eef421b54fb9bd58b09d2313e`, all 143 Release oracles
for processing, synthesis, instruments, streams and MIDI pass on macOS ARM64
and X64 under Rosetta. They also compose and link for Linux and Windows,
in ARM64 and X64; none of those executables ran on those two systems during
this qualification.

The [resource gate](Resources.md) adds a positively controlled Debug/Release
allocation counter on macOS ARM64 and a measured 16/64-voice workload with
five effects. This gate requires Clang and does not cover other hosts. Link
results are not performance or allocation measurements.

## Retained qualification from October 7, 2026

The local audio production delivery was qualified on GFX.Audio
`a821c4a8776151761eea8a062540271b987e1166` and Silex
`4e1dfdbe339c3972f86684a5898030bbea404c72`. The latter provides the mutable
method-view correction. Dependencies were GFX
`46d14c329b6acae53a1fb70038fb8496e3b080bc` and STD
`4112bb54390c55d39e85a5414991359abdff15dc`.

The five deliveries below were integrated into the local `main` branches.
This table retains the commits from the `gfx-audio-production` receipts after
retirement of its capsule; it does not automatically qualify a future commit.

| Delivered receipt | GFX.Audio | Silex |
| --- | --- | --- |
| `memory-stream-core` | `d5efc07170c11c59da5708f1f31889aabe78fd27` | — |
| `timeline-groups` | `7405034b8a8f1cbbd96005c6c8abf2abfeeaeaf5` | — |
| `offline-render` | `9c5a0d97567db074960d576b2cf35c723d99628d` | — |
| `block-processing` | `78fcbe478706ac1e3a7e6459a3b5a0fad899bf7b` | `4e1dfdbe339c3972f86684a5898030bbea404c72` |
| `production-final` | `a821c4a8776151761eea8a062540271b987e1166` | `4e1dfdbe339c3972f86684a5898030bbea404c72` |

The audio suite passed **53 of 53 tests across 19 files**, including after
integration from the workspace root. The **13 Release PCM oracles** ran on
macOS ARM64 and X64 through Rosetta without an audio driver; they composed
and linked for all six targets. Linux and Windows were not executed. The seven
examples listed above passed in Release; the ten rejection cases in
`GeneratedSamplesValidation.py` and the offline wait rejection in
`OfflineValidation.py` produced the expected explicit failures.

Compiler gates `zig build test` and `zig build check` passed: 244 language
tests across 93 files, 84 optimizer admission tests and 28 programs.
`Tests/ControlFlow/MutableViewCalls.sx` also ran through interpretation,
ARM64 Debug/Release and X64 Release, returning `2.25`.

All six `SDL3_mixer-3.2.4-silex.6` provider archives were rebuilt twice with
identical results. Manifest, artifact metadata,
[SHA256SUMS](../../Boundary/SHA256SUMS.txt) and
[patch](../../Boundary/SDL3_mixer-3.2.4-silex.6.patch) hashes agreed at final
delivery. Local archives are retained; their reserved URLs do not constitute
publication.

The user had authorized reintegration subject to passing tests and no known
defect. They explicitly accepted closure on October 7, 2026: “on clos la spec,
puisque tout est ok, et réintégré dans les branch main locale” (close the Spec,
since everything is fine and integrated into the local main branches).
Tests, scripts, examples and explanations remain in the repositories. This
closure publishes no remote branch, tag or release.

## Composition and modulation

The `Tests/Consumer/Tests/Composition.sx` consumer adds seven cases: weighted
mix and independent state, ordered custom treatments, analytical curve,
stereo AM, FM phase integration, invalid parameters/blocks and error propagation.
They also run as Release oracles. `SynthesisSpectrum.py` checks the three
analytical AM components and FM against a closed-form discrete sine sum in
Debug and Release. The selected FM (3 kHz carrier, 375 Hz control and 750 Hz
deviation at 48 kHz) qualifies a musical regime far from Nyquist; it does not
constitute universal alias suppression.

## Bitcrusher and retro recipe

The `Tests/Consumer/Tests/Bitcrusher.sx` consumer adds six oracles: the full
256-code grid and an 8-bit ramp, rounding ties and saturation, sample hold
at 24 bits and independent channel values, exact chunking in 1/2/8 channels,
reset, mixing, bypass, changes, invalid input without state advancement,
then composition with a consumer-defined generator and processor.
`ReleaseValidation.py` repeats them in Release. `RetroSounds.sx` compares
six recipes without assets; listening complements PCM proof for timbre
and transitions.

## Saturation and distortion

Six `Distortion.sx` consumer oracles cover soft/hard curves, large float32
values and a subnormal drive, wet/bypass, settings/reset, chunking in 1/2/8
channels, invalid input before writes, and composition order with a custom
processor. They repeat in Release. `SaturatedSounds.sx` compares four timbres
without assets.

## Stereo pan

Six `StereoPan.sx` consumer oracles cover both channel bases, center and poles,
sine/cosine halfway gains, mixing, bypass, changes/reset, exact chunking,
formats and blocks rejected before writes, the failing frame preserved on
overflow, then composition order with a consumer-defined generator and effect.
`StereoSounds.sx` plays left/center/right then movement across blocks.

The ten modulated-delay oracles check causal fractional delay, signed echoes, modulation shared across channels, tone cancellation, decaying tail, exact chunking, settings/bypass, invalid input, overflow and consumer composition.

The twelve reverb oracles cover analytical first echoes, filtered feedback and decay, independent channels, exact chunking, mix/bypass, changes/reset, rejection, atomic frame overflow, tail energy and color, extreme formats and consumer composition.

The twelve dynamics oracles cover dB curves and explicit makeup, float64 attack/release references, linked channel peaks, chunking/reset, wet/bypass, settings/rejection, atomic frame overflow, float32 extremes and composition with external generators/effects.

The sixteen `Instruments.sx` oracles cover sine sum/velocity/ADSR, identities, stealing/rejection, sample continuity, sustain/stop, phase-preserving bend and atomic rejection, invalid input, simultaneous ordering/boundaries/empty blocks, bit-exact score in 1/2/8 channels, ownership/late events/capacity, prefix on failure, a user instrument with a limiter, the clock beyond 2²⁴, extreme capacities/rates, then absolute float64 conversion. `ReleaseValidation.py` repeats them. `PolyphonicMelody.sx` produces four bars without assets; listening complements numerical proof.

The thirteen Continuous.sx oracles cover ramp targets/retargeting/reset, invalid input, FM phase and bend with float64 references, bit-exact automation, partial writes without duplicate commands, pause/starvation/resume/stop, channels and final short block, zero duration and bounds, source/PCM errors, foreign writes/closure, lifetime and an effect tail compared with memory rendering. They repeat in Release. ContinuousSounds.sx plays two single streams with evolving controls; listening to actual output complements the proof.

The twelve MIDIFile oracles cover formats0/1, RP-001 examples, tempo/stable merge, running status, frame fractions without drift, extensions/ignored events, truncation/lengths/EOT, unsupported input, capacities, long integer clock/overflow and file reading. The sixteen MIDISynth oracles cover frequency/velocity/float64 PCM, FIFO/programs, sustain/stops, volume/expression/balance/bend, ignored input/errors, preparation, bit-exact memory/stream output, user instrument, end/reset, rejection without consumption, ignored counters and format. Smoothing regressions cover expression continuity on a held voice, retargeting during a ramp, stereo levels, independent channels, programs sharing a channel, blocks/reset and bounds. ReleaseValidation repeats them. MIDIMelody plays a stereo score without banks; listening complements numerical checks.
