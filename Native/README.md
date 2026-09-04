# Rebuild the GFX.Audio boundary

GFX.Audio owns its private SDL3_mixer 3.2.4 provider. The source archive is
the official `SDL3_mixer-3.2.4.tar.gz` release with SHA-256
`182a07c745375e113dc740d43964ff21b0be29f29f59876c4dbc4db3d32f6901`.
It is compiled against SDL 3.4.10 from the official release archive with
SHA-256
`12b34280415ec8418c864408b93d008a20a6530687ee613d60bfbd20411f2785`.

`Boundary/SDL3_mixer-3.2.4-silex.2.patch` is applied by the build script. The
result keeps only the built-in AIFF, AU, dr_flac, dr_mp3, stb_vorbis, VOC, and
WAVE decoders, and leaves SDL3 itself under the ownership of GFX.

Run the target build from the package root:

```text
Native/build-sdl3-mixer.sh /path/to/SDL3-3.4.10 /path/to/SDL3_mixer-3.2.4 macos-x64 /path/to/output
Native/build-sdl3-mixer.sh /path/to/SDL3-3.4.10 /path/to/SDL3_mixer-3.2.4 linux-arm64 /path/to/output
```

The script requires the native target host, fixes archive timestamps, remaps
source and build paths, verifies the patch checksum, inspects the architecture
and required mixer symbols, then prints the archive SHA-256.

Both missing archives were reproduced byte for byte by GitHub Actions run
`33908070086`. Their target manifests and hashes are recorded alongside the
four established targets under `Boundary/`. The future `silex.3` release URLs
are declared for packaging, but this validation does not create that release.
