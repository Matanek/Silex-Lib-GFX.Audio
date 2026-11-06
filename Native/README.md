# Build the private streaming provider

`build-stream-provider.py` is the recorded portable build for the
`SDL3_mixer-3.2.4-silex.7` candidate. It requires Python 3.12 or newer and
the official Zig **0.16.0** distribution used by the workflow. Its release
checksum is verified there; a separately built Zig can produce different
compiler-identification metadata. Download the upstream source archives from the official releases:

- [SDL 3.4.10](https://github.com/libsdl-org/SDL/releases/download/release-3.4.10/SDL3-3.4.10.tar.gz)
- [SDL_mixer 3.2.4](https://github.com/libsdl-org/SDL_mixer/releases/download/release-3.2.4/SDL3_mixer-3.2.4.tar.gz)

The script checks both upstream hashes, the complete patch hash and CaptureTap.c/.h hashes before
extracting or compiling. For example, from the package directory:

```sh
python3 Native/build-stream-provider.py /tmp/SDL3-3.4.10.tar.gz /tmp/SDL3_mixer-3.2.4.tar.gz macos-arm64 Boundary/macos-arm64/libSDL3_mixer.a
```

Repeat for the six targets listed in `Package.json`; Windows outputs use
`SDL3_mixer.lib`. The builder compiles the SDL_mixer sources, including its
bundled decoders, against SDL headers. It does not rebuild SDL or enable MIDI.
It uses temporary build directories, deterministic archive metadata and stable
COFF source/object names. Set `ZIG` to the recorded official executable.
`Boundary/*/Artifact.SDL3_mixer.json`, `Boundary/SHA256SUMS.txt` and the package
manifest record the resulting checksums.

The manual `build-portability.yml` workflow rebuilds each target twice and
checks byte equality, the recorded manifest hash and the private close, drain and capture symbols.
It uploads workflow artifacts; it does not publish a release. Candidate
`silex.7` URLs are reserved for a subsequent authorized provider publication.
Local development requires the verified archives present at their manifest
paths, or a local rebuild. Do not claim remote installability before that
publication is complete.

`build-sdl3-mixer.sh` retains the native CMake comparison route for macOS X64
and Linux ARM64. It applies the mixer patch without the separate capture adapter, and its toolchain produces separate
checksums; it is a historical comparison, not the source of current provider hashes. The previous
spatial-only provider was reproduced for those two targets by GitHub Actions
run `33908070086`; that historical proof does not qualify this streaming patch.

## What the private patch changes

The patch preserves the existing spatial interpolation correction and adds
`Silex_MIX_CloseTrackStream` and `Silex_MIX_TrackDrained`, used only inside
the Silex binding. A close takes
the track lock, flushes its input and marks explicit EOF. The native mixer
keeps producing silence for an open dry source; for a closed exhausted source
it flushes the output resampler before stopping. No Silex callback runs in the
native audio thread. The new flag is appended to the private track structure.

Cached finite sounds also finalize their resampler at the known last frame.
This prevents the last filter frames from being deferred to another mixer
request. Looping sources preserve the filter state between repeats.
For small mixer requests, the callback fills enough converted output to cover
the resampler lookahead. A stopped track is considered drained only when its
prepared output is empty; explicit stop discards that output. PCM tests cover
small and large requests, the final frame count and equivalence between a
complete source and successive blocks.

Seeking clears the converted output and its filter history while the track is
locked. A prepared block from the previous source position cannot survive a
seek. The regression compares a seek against a fresh playback at that frame.

Once stopped output is flushed, its available converted frames determine
drain completion. Raw filter history may retain an incomplete output frame
after speed conversion; it must not delay an already empty output.

Offline mixers accumulate float samples linearly instead of passing them to
SDL_MixAudio, which clips each addition. Device mixers retain their previous
saturation behavior. A regression requires a rendered amplitude of 2, and
compares block layouts across sample-rate conversion. Offline initialization
calls MIX_Init alone; it never initializes or opens an audio driver.

## Observe the final device mix

`CaptureTap.c` is a separate adapter compiled into the provider alongside the
unchanged `silex.6` mixer patch. Its header and source hashes are pinned in each
artifact record. The post-mix callback copies whole float32 frames to a
preallocated SPSC ring. It uses always-lock-free atomic loads/stores, without
Silex callbacks, allocation, file IO or waiting. An overflow latches failure
while playback and its production counter continue. Stop detaches under the
mixer lock; the binding retains Audio until the capture handle is destroyed.
Only one reader and one capture per mixer are supported.

## Native capture regression (macOS ARM64)

From the workspace or Spec group root, with the extracted, verified upstream
sources used by the builder:

```sh
python3 Packages/GFX.Audio/Native/Tests/run-capture.py /path/SDL3-3.4.10 /path/SDL3_mixer-3.2.4
python3 Packages/GFX.Audio/Native/Tests/run-capture.py /path/SDL3-3.4.10 /path/SDL3_mixer-3.2.4 --archive --hardware
```

The first run includes the adapter for deterministic ring wrap/overflow checks
and exercises known PCM through the dummy device. The second links the actual
provider archive and uses silent PCM through CoreAudio. It checks post-mix
identity, gain, concurrent reads, stop/restart, metadata and continued playback
after overflow. It captures no microphone or system audio. Dummy-device timing
is not a real-time synchronization oracle. Public Silex coverage lives in
`Tests/OutputCapture.sx` and `Tests/Consumer/Smokes/OutputCapture.sx`.
