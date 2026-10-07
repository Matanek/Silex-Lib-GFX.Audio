#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 4 ]]; then
    echo "usage: $0 <SDL-source> <SDL_mixer-source> <target> <output-directory>" >&2
    exit 2
fi

audio_native_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
audio_package_dir="$(cd -- "$audio_native_dir/.." && pwd)"
sdl_source="$(cd -- "$1" && pwd)"
mixer_source="$(cd -- "$2" && pwd)"
target="$3"
output_dir="$4"
patch_file="$audio_package_dir/Boundary/SDL3_mixer-3.2.4-silex.5.patch"
expected_patch_sha256="3823c540c6d9df625e47625e7eb10113c145f1b00d7d86b2023af2fc20a91990"

if command -v sha256sum >/dev/null 2>&1; then
    actual_patch_sha256="$(sha256sum "$patch_file" | cut -d ' ' -f 1)"
else
    actual_patch_sha256="$(shasum -a 256 "$patch_file" | cut -d ' ' -f 1)"
fi
if [[ "$actual_patch_sha256" != "$expected_patch_sha256" ]]; then
    echo "SDL3_mixer patch checksum mismatch" >&2
    exit 1
fi

case "$target" in
    macos-x64)
        [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "x86_64" ]] || {
            echo "macos-x64 must be built on a native macOS X64 host" >&2
            exit 1
        }
        archive_name="SDL3_mixer-3.2.4-macos-x64.a"
        target_c_flags=""
        cmake_target_arguments=(
            -DCMAKE_OSX_ARCHITECTURES=x86_64
            -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0
        )
        ;;
    linux-arm64)
        [[ "$(uname -s)" == "Linux" ]] || {
            echo "linux-arm64 must be built on Linux" >&2
            exit 1
        }
        case "$(uname -m)" in
            aarch64|arm64) ;;
            *) echo "linux-arm64 must be built on a native ARM64 host" >&2; exit 1 ;;
        esac
        archive_name="SDL3_mixer-3.2.4-linux-arm64.a"
        target_c_flags="-mno-outline-atomics"
        cmake_target_arguments=(
            -DSDL_UNIX_CONSOLE_BUILD=ON
        )
        ;;
    *)
        echo "unsupported SDL3_mixer target: $target" >&2
        exit 1
        ;;
esac

build_root="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/silex-audio-$target"
sdl_build="$build_root/sdl-build"
mixer_build="$build_root/mixer-build"
patched_mixer="$build_root/SDL3_mixer-3.2.4"
rm -rf -- "$build_root"
mkdir -p "$build_root" "$patched_mixer"
cp -R "$mixer_source/." "$patched_mixer"
patch -d "$patched_mixer" -p1 < "$patch_file"

export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1

common_c_flags="$target_c_flags -O3 -g0 -DNDEBUG -ffile-prefix-map=$build_root=/silex-build -ffile-prefix-map=$sdl_source=/sources/sdl -ffile-prefix-map=$mixer_source=/sources/sdl-mixer -ffile-prefix-map=$audio_package_dir=/sources/gfx-audio"

cmake -S "$sdl_source" -B "$sdl_build" -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="$common_c_flags" \
    -DSDL_EXAMPLES=OFF \
    -DSDL_INSTALL=OFF \
    -DSDL_INSTALL_DOCS=OFF \
    -DSDL_SHARED=OFF \
    -DSDL_STATIC=ON \
    -DSDL_TESTS=OFF \
    -DSDL_TEST_LIBRARY=OFF \
    "${cmake_target_arguments[@]}"

cmake -S "$patched_mixer" -B "$mixer_build" -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="$common_c_flags" \
    -DSDL3_DIR="$sdl_build" \
    -DBUILD_SHARED_LIBS=OFF \
    -DSDLMIXER_INSTALL=OFF \
    -DSDLMIXER_DEPS_SHARED=OFF \
    -DSDLMIXER_VENDORED=OFF \
    -DSDLMIXER_TESTS=OFF \
    -DSDLMIXER_EXAMPLES=OFF \
    -DSDLMIXER_FLAC=ON \
    -DSDLMIXER_FLAC_LIBFLAC=OFF \
    -DSDLMIXER_FLAC_DRFLAC=ON \
    -DSDLMIXER_GME=OFF \
    -DSDLMIXER_MOD=OFF \
    -DSDLMIXER_MP3=ON \
    -DSDLMIXER_MP3_DRMP3=ON \
    -DSDLMIXER_MP3_MPG123=OFF \
    -DSDLMIXER_MIDI=OFF \
    -DSDLMIXER_OPUS=OFF \
    -DSDLMIXER_VORBIS_STB=ON \
    -DSDLMIXER_VORBIS_VORBISFILE=OFF \
    -DSDLMIXER_VORBIS_TREMOR=OFF \
    -DSDLMIXER_WAVPACK=OFF \
    "${cmake_target_arguments[@]}"
cmake --build "$mixer_build" --config Release --parallel 4 --target SDL3_mixer-static

archive="$(find "$mixer_build" -type f -name 'libSDL3_mixer.a' -print -quit)"
if [[ -z "$archive" ]]; then
    echo "SDL3_mixer static archive was not produced" >&2
    exit 1
fi

mkdir -p "$output_dir"
output="$output_dir/$archive_name"
cp "$archive" "$output"

if [[ "$target" == "macos-x64" ]]; then
    archive_header="$build_root/archive-header.txt"
    lipo -info "$output" > "$archive_header"
    grep -Fq 'architecture: x86_64' "$archive_header"
else
    archive_header="$build_root/archive-header.txt"
    readelf -h "$output" > "$archive_header"
    grep -Fq 'Machine:                           AArch64' "$archive_header"
fi

symbols="$build_root/exported-symbols.txt"
nm -g "$output" > "$symbols"
for symbol in MIX_CreateMixer MIX_LoadAudio_IO MIX_PlayTrack Silex_MIX_CloseTrackStream Silex_MIX_TrackDrained; do
    grep -Eq "(^|[[:space:]_])${symbol}$" "$symbols" || {
        echo "missing required SDL3_mixer symbol: $symbol" >&2
        exit 1
    }
done

file "$output"
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$output"
else
    shasum -a 256 "$output"
fi
