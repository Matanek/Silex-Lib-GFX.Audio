# Validated engine sound library

This directory owns the renderer previously proven in Silex-Examples' autonomous
engine bench, its native build adapters, engine definitions and impulse-response
preparation. The old bench remains an independent, frozen comparison witness.
`Module/Engines` owns the Silex-facing protocol, intake-flow sound and output mix.
No source in this package imports Silex-Examples.

Build on macOS ARM64 with Xcode/Clang/Flex, CMake and Bison 3.2 or newer:

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
