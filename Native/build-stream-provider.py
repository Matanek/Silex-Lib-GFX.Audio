"""Build the private streaming and output capture provider from verified upstream source archives.

Requires Python 3.12+ and Zig 0.16.0. No SDL device or SDL build is needed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

SDL_SHA = "12b34280415ec8418c864408b93d008a20a6530687ee613d60bfbd20411f2785"
MIXER_SHA = "182a07c745375e113dc740d43964ff21b0be29f29f59876c4dbc4db3d32f6901"
TARGETS = {
    "macos-arm64": "aarch64-macos-none",
    "macos-x64": "x86_64-macos-none",
    "linux-x64": "x86_64-linux-gnu",
    "linux-arm64": "aarch64-linux-gnu",
    "windows-x64": "x86_64-windows-gnu",
    "windows-arm64": "aarch64-windows-gnu",
}
FEATURES = ["WAV", "AIFF", "AU", "VOC", "FLAC_DRFLAC", "MP3_DRMP3", "OGGVORBIS_STB"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdl_archive", type=Path)
    parser.add_argument("mixer_archive", type=Path)
    parser.add_argument("target", choices=TARGETS)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    zig = os.environ.get("ZIG", "zig")
    if subprocess.check_output([zig, "version"], text=True).strip() != "0.16.0":
        parser.error("Zig 0.16.0 is required for the recorded provider build")
    for path, expected in [(args.sdl_archive, SDL_SHA), (args.mixer_archive, MIXER_SHA)]:
        if digest(path) != expected:
            parser.error(f"upstream checksum mismatch: {path}")
    package = Path(__file__).resolve().parents[1]
    patch = package / "Boundary/SDL3_mixer-3.2.4-silex.6.patch"
    metadata = package / "Boundary" / args.target / "Artifact.SDL3_mixer.json"
    # The artifact metadata pins the complete patch, including the existing spatial fix.
    if digest(patch) != json.loads(metadata.read_text())["patch_sha256"]:
        parser.error("private provider patch checksum mismatch")
    capture_source = package / "Native/CaptureTap.c"
    capture_header = package / "Native/CaptureTap.h"
    recorded = json.loads(metadata.read_text())
    if digest(capture_source) != recorded["capture_source_sha256"] or digest(capture_header) != recorded["capture_header_sha256"]:
        parser.error("private capture adapter checksum mismatch")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gfx-audio-provider-") as temporary:
        root = Path(temporary)
        for path in [args.sdl_archive, args.mixer_archive]:
            with tarfile.open(path) as archive:
                archive.extractall(root, filter="data")
        sdl = root / "SDL3-3.4.10"
        mixer = root / "SDL3_mixer-3.2.4"
        subprocess.run(["patch", "-s", "-d", str(mixer), "-p1", "-i", str(patch)], check=True)
        shutil.copyfile(capture_source, mixer / "src/Silex_audio_capture.c")
        shutil.copyfile(capture_header, mixer / "src/CaptureTap.h")
        flags = ["-target", TARGETS[args.target], "-O3", "-g0", "-DNDEBUG", "-DBUILD_SDL",
                 "-DSDL_BUILD_MAJOR_VERSION=3", "-DSDL_BUILD_MINOR_VERSION=2", "-DSDL_BUILD_MICRO_VERSION=4",
                 f"-ffile-prefix-map={root}=/silex-audio-provider"]
        if args.target.startswith("macos-"):
            flags += ["-mmacosx-version-min=11.0"]
        if args.target == "linux-arm64":
            flags += ["-mno-outline-atomics"]
        flags += ["-DDECODER_" + feature for feature in FEATURES]
        for include in [sdl / "include", mixer / "include", mixer / "src", mixer / "src/codecs"]:
            flags += ["-I", str(include)]
        objects = []
        environment = dict(os.environ, ZERO_AR_DATE="1", SOURCE_DATE_EPOCH="0")
        for source in sorted((mixer / "src").glob("*.c")):
            obj = root / (source.name + ".o")
            source_flags = []
            if args.target.startswith("windows-"):
                # COFF source and CodeView object records must not contain Zig temporary names.
                source_flags = ["-Xclang", "-main-file-name", "-Xclang", source.name,
                                "-Xclang", "-object-file-name", "-Xclang", source.name + ".o"]
            subprocess.run([zig, "cc", *flags, *source_flags, "-c", str(source), "-o", str(obj)], check=True, env=environment)
            objects.append(str(obj))
        archive_output = root / output.name
        subprocess.run([zig, "ar", "rcsD", str(archive_output), *objects], check=True, env=environment)
        shutil.copyfile(archive_output, output)
    print(f"{digest(output)}  {output}")


if __name__ == "__main__":
    main()
