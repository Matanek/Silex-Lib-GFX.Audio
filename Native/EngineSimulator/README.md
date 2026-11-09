# Validated engine sound library

This directory owns the renderer previously proven in Silex-Examples' autonomous
engine bench, its native build adapters, engine definitions and impulse-response
preparation. The old bench remains an independent, frozen comparison witness.
`Module/Engines` owns the Silex-facing protocol, intake-flow sound and output mix.
No source in this package imports Silex-Examples.

This is the package-maintenance build path. Ordinary consumers call
`Engines.Library.open()` without preparing a directory.

`DefaultParity.py --output /tmp/engine-packet-parity` extracts and verifies the
bundled library, then compares repeated native packets for all eight profiles
using the consumer's three operating states. It bypasses Silex PCM decoding and
mixing; a failure records both packet streams and the first differing byte.
The public consumer independently checks exact processed PCM and reports the
profile, operating state, block and sample on a mismatch.

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
