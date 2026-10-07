# Verify audio paths

Run these commands from the `SilexProject` root with the local toolchain that
includes the mutable method-view correction. Verified archives must be present
under `Boundary/`; `Package.json` records paths and hashes. The
[provider guide](../../Native/README.md) covers rebuilding and separate publication.

```sh
SDL_AUDIODRIVER=dummy silex test Packages/GFX.Audio/Tests --nocache
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py
python3 Packages/GFX.Audio/Tests/GeneratedSamplesValidation.py
python3 Packages/GFX.Audio/Tests/OfflineValidation.py
```

The suite covers memory loading, handles and owners, timeline, groups and pause,
stream capacity, silence/resume, draining, device-free rendering, processing
and levels. The dummy driver supports playback control checks; PCM comparisons
support mixing and processing guarantees. Rejection checks require a diagnostic
and failure exit code, with timeouts to detect waits that cannot progress.

`ReleaseValidation.py` runs the 13 public `Processing`, `Production` and
`StreamGroups` oracles in Release. It selects a deliberately nonexistent driver:
these oracles use offline rendering and require no device. They cover the
stateful chain and the same scalar producer as a complete source and stream,
including 24→48 kHz conversion, absolute 10⁻⁶ tolerance and frame counters.

```sh
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target macos-x64 --execute
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target linux-x64
```

`--target` composes and links without execution; `--execute` also runs the
artifact and requires a host-compatible target. Package targets are
`macos-arm64`, `macos-x64`, `linux-arm64`, `linux-x64`, `windows-arm64` and
`windows-x64`. Linking for a target does not prove execution on its system.
Local qualification executed the oracles on macOS ARM64 and X64 through Rosetta; the other
systems were checked for composition and linkage.

`GeneratedTone`, `MemorySound`, `StreamingTone`, `Timeline`, `Groups`, `Offline`
and `ProcessedTone` are executable sources under `Docs/`. For example:

```sh
SDL_AUDIODRIVER=dummy silex run Packages/GFX.Audio/Docs/ProcessedTone.sx --release --nocache
SDL_AUDIODRIVER=__silex_no_audio_driver__ silex run Packages/GFX.Audio/Docs/Offline.sx --release --nocache
```

These proofs cover PCM and logical mixer state. Counters do not measure the
exact speaker presentation time. Processing runs on the application thread;
the provider never calls a Silex callback on its audio thread. Data and
primitives remain independent of instruments, sequencing or MIDI.
