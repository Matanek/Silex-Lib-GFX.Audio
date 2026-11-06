"""macOS ARM64 native regression; no Silex or Python code runs on the audio thread."""
from pathlib import Path
import argparse, json, os, subprocess, tempfile
parser = argparse.ArgumentParser()
parser.add_argument("sdl_source", type=Path)
parser.add_argument("mixer_source", type=Path)
parser.add_argument("--hardware", action="store_true", help="CoreAudio with silent PCM; default: dummy with known samples")
parser.add_argument("--archive", action="store_true", help="link the provider instead of including the adapter for white-box ring checks")
args = parser.parse_args()
package = Path(__file__).resolve().parents[2]
gfx = package.parent / "GFX"
frameworks = json.loads((gfx / "Package.json").read_text())["boundary"]["macos-arm64"]["providers"]["SDL3"]["frameworks"]
with tempfile.TemporaryDirectory(prefix="gfx-audio-capture-test-") as directory:
    executable = Path(directory) / "capture"
    command = ["/usr/bin/clang", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-mmacosx-version-min=13.0"]
    if args.archive: command.append("-DARCHIVE_PROBE")
    command += ["-I" + str(args.sdl_source.resolve() / "include"), "-I" + str(args.mixer_source.resolve() / "include"), str(package / "Native/Tests/CaptureTap.c"), str(package / "Boundary/macos-arm64/libSDL3_mixer.a"), str(gfx / "Boundary/macos-arm64/libSDL3.a")]
    for framework in frameworks: command += ["-framework", framework]
    command += ["-lobjc", "-o", str(executable)]
    subprocess.run(command, check=True)
    environment = dict(os.environ)
    if args.hardware: environment.pop("SDL_AUDIODRIVER", None)
    else: environment["SDL_AUDIODRIVER"] = "dummy"
    subprocess.run([str(executable)] + (["--hardware"] if args.hardware else []), env=environment, timeout=30, check=True)
