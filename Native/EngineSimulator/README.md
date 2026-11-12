# Validated engine sound library

This directory owns the renderer previously proven in Silex-Examples' autonomous
engine bench, its native build adapters, engine definitions and impulse-response
preparation. The old bench remains an independent, frozen comparison witness.
`Module/Engines` owns the Silex-facing protocol, intake-flow sound and output mix.
No source in this package imports Silex-Examples.

`Module/Engines/Vehicles.sx` and its private `VehicleDefinition` prepare vehicle
variants from these deployed definitions or generated crank/valve/gas graphs.
They reuse the unchanged renderer and existing impulses. Geometry edits belong
to a private temporary deployment; stock `454` goes through `Library.engine`
without any edit. `Tests/Consumer/Tests/VehicleEngines.sx` protects that PCM parity
and exercises every variant. Run it after changing the pinned source templates,
their parameter spelling, or the bundled resources. The parts-based pulse
synthesizer is not an acoustic substitute for this chain.

City profiles have their own intake/valve/exhaust definition and private
`VehicleVoice` exterior processing. `city-diesel` additionally uses a sampled
acoustic voice, not a new diesel combustion solver. Its eight short excitations
are derived from a user-supplied TDI recording; `Assets/Engines/Voices/Diesel.json`
records source hashes, extraction positions, periodicity and the PCM checksum.
Engine identity is unconfirmed. No consumer reads the original recording.

Rebuild the voice from the same decoded 44.1 kHz PCM16 WAV with
`PrepareDieselVoice.py reference.wav output-directory --source-recording original.mp3`.
The tool reads those inputs and writes only the destination. It removes DC,
closes each repeat and limits it to 128 harmonics. Playback is capped at 160 Hz
firing frequency, keeping retained harmonics below Nyquist. Run
`python3 Packages/GFX.Audio/Native/EngineSimulator/VehicleVoiceChecks.py` and the
consumer vehicle tests after modifying this resource. The native renderer and
the original engine bank remain unchanged.

Qualify an acoustic label against a recording with an explicit listening
perspective. Shared simulation, cylinder count and displacement do not establish
vehicle identity. Nonzero PCM, reset and parity tests prove operation and
preservation; recognition and realism require listening. Preserve relative
levels when comparing quiet production exhausts with open sports exhausts.

This is the package-maintenance build path. Ordinary consumers call
`Engines.Library.open()` without preparing a directory.

`DefaultParity.py --output /tmp/engine-packet-parity` extracts and verifies the
bundled library, then compares repeated native packets for all eight profiles
using the consumer's three operating states and two concurrent renderers with
the same per-block request order. It bypasses Silex PCM decoding and mixing;
a failure records both packet streams and the first differing byte. The public
consumer independently checks exact processed PCM without instrumentation.

Rebuild the existing renderer on macOS ARM64 with Xcode/Clang/Flex, CMake and
Bison 3.2 or newer:

```sh
python3 Packages/GFX.Audio/Native/EngineSimulator/Catalog.py --check
python3 Packages/GFX.Audio/Native/EngineSimulator/Build.py \
  --source /path/to/engine-sim --output Build/EngineSimulator-Build --bison /path/to/bison
python3 Packages/GFX.Audio/Native/EngineSimulator/PackageLibrary.py \
  --from-build Build/EngineSimulator-Build --output Build/EngineLibrary
```

The engine-sim checkout must contain revision
`85f7c3b959a908ed5232ede4f1a4ac7eafe6b630` and the submodule revisions pinned in
`Build.py`. It archives these exact revisions, applies the preserved portability,
2T and exhaust-blend adapters, and compiles serially. It does not modify the
upstream checkout. `Provenance.json` records the renderer/source identity.
`PackageLibrary.py` verifies this identity, then stages only the executable,
profile scripts, impulses and license. `Library-Manifest.json` records deployed
file hashes. It refuses an existing destination. No app-specific path is built
into the public API. The source build also contains a valid library marker, so
it can be used directly during development.

New builds advertise `gearing-v1` in their provenance and use the
`silex-engine-library-v2` marker. They accept a cold road-mode override after
the profile index: `--gearing FINAL_DRIVE FIRST_RATIO ... LAST_RATIO` (1..12
strictly decreasing ratios, each value finite and in 0.05..20). The streaming
protocol and stock settings are unchanged. The Silex API retains v1-bank
compatibility for stock gearing and rejects overrides before spawning a v1
renderer. Keep the executable, provenance and marker from the same build.

Builds with `following-v1` use the `silex-engine-library-v3` marker and add
`follow` / `follow-intake` modes. The existing seven-field request carries frame
count, ignition, combustion effort (0..1), texture, convolution, external RPM
(0..12000), and a reserved zero. Replies use magic `0x41563845` or `0x42563845`
with the free-mode header and sample layout. An added rotational constraint
tracks RPM without resetting crank angles; its requested rate changes by at
most 200 RPM per 10 ms quantum. The regular free/road paths are unchanged.
The public API validates the narrower profile-specific RPM ceiling and rejects
older banks before launching an unsupported mode.

Source builds with `calculated-exhaust-v1` provide `serve-calculated` and
`follow-calculated` for offline comparisons. The second argument is a text
response file. Its first line contains `exhaust-response-v1`, the band count
(1–24) and the overall gain in dB. Each subsequent line contains the center
frequency in Hz, the quality factor and the gain in dB. The renderer calculates
each filter at startup and applies an independent filter history to each
collector, before the output leveler. The request and reply layout matches
`serve` or `follow` respectively. The convolution field sets the amount of
calculated response in the mix.

Builds with `combustion-v1` advertise it in `CombustionTelemetry.txt`.
They accept `serve-combustion` and `serve-intake-combustion`. Replies set
bit 30 of the corresponding magic and append sixteen little-endian
16-bit combustion offsets to the header. An offset of zero marks an
inactive cylinder in the packet. Other values give the one-based audio
frame of that cylinder's latest successful combustion in the packet.
Requests and PCM payloads retain their existing formats.

Builds with `bench-transmission-v1` advertise it in `BenchTransmission.txt`.
The `bench-combustion` and `bench-intake-combustion` modes accept the
existing drive requests and add combustion offsets after the drive header.
The same engine runs the bench load model in neutral and couples to the
vehicle under a selected gear.

For a streaming comparison, pass `collectors=/path/to/capture.f32` in place
of the output prefix. The capture contains the 44.1 kHz input of the
synthesizer, as interleaved native float32 samples in collector order. Each
write covers a whole simulated quantum. `unused` disables the capture.

`Catalog.py` maintains the Silex profile projection from `Profiles.json`.
Keep profile ordering aligned with the native renderer. The original profiles,
impulses and full thermal simulation are retained: this is an extraction, not a
reduced DSP replacement. Deployment currently uses a helper process per engine;
this path allocates and performs IPC and is not a real-time audio callback.
Only macOS ARM64 has been built and executed for this extraction. Build and
runtime packaging for other targets remain to be qualified; no additional
provider is selected unconditionally by the portable SDL audio package.

The upstream renderer and assets are covered by `LICENSE.engine-sim`; generated
banks include that license. Sources and pinned provenance are retained so a bank
can be rebuilt without the old demo. See the public Engines guide for use.

## Refresh the default embedded library

From the workspace root, after a successful v3 build:

```sh
python3 Packages/GFX.Audio/Native/EngineSimulator/BundleLibrary.py \
  --from-build .silex/engine-simulator-build
```

The bundler verifies renderer provenance and architecture, stages the existing
complete library, and concatenates its files without changing any byte. It
writes `Assets/Engines/macos-arm64/Library.bin`, its per-file SHA-256 manifest
and the target fragment that embeds and restores those exact byte ranges.
The asset and its checksum manifest are included in Git. The `embed_bytes`
reference makes it a package resource, so publication includes it in the package
snapshot and ordinary installation supplies it automatically. Do not also declare
this same file under `artifacts`: it already belongs to the source resources.
The Silex wrapper owns temporary deployment and lifetime; no acoustic code changes.
Other targets explicitly retain their previous unqualified status.
