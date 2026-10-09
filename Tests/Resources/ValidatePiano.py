"""Private macOS ARM64 piano allocation gate with positive controls."""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import subprocess

fixture = Path(__file__).resolve().parent
owner = fixture.parents[1]
workspace = owner.parents[1]
if Path.cwd().resolve() != workspace:
    raise SystemExit("Run from SilexProject or the Spec Worktree group root")
if platform.system() != "Darwin" or platform.machine() != "arm64":
    raise SystemExit("This allocation gate covers macOS ARM64 only")
cache = workspace / ".silex"
compiler = Path(os.environ.get("SILEX_EXECUTABLE", workspace / "Silex/Toolchain/zig-out/bin/silex"))
env = dict(os.environ, SDL_AUDIODRIVER="dummy", SDL_VIDEODRIVER="dummy", ZIG_GLOBAL_CACHE_DIR=str(cache / "zig-global"), ZIG_LOCAL_CACHE_DIR=str(cache / "zig-local"))
library = cache / "audio-heap-probe.dylib"
subprocess.run(["clang", "-dynamiclib", "-arch", "arm64", "-arch", "x86_64", "-O2", "-fno-builtin", "-Wall", "-Wextra", "-Werror", str(fixture / "HeapProbe.c"), "-o", str(library)], check=True)
pattern = re.compile(r"AUDIO_HEAP allocations=(\d+) bytes=(\d+) copies=(\d+) copy_bytes=(\d+)")
report = dict(host=platform.platform(), compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(), modes={})
for mode in ["debug", "release"]:
    binary = cache / f"piano-heap-{mode}"
    subprocess.run([str(compiler), "compile", str(fixture / "PianoHeap.sx"), f"--{mode}", "--nocache", "-o", str(binary)], cwd=workspace, env=env, check=True, timeout=120)
    run = subprocess.run([str(binary)], cwd=workspace, env=dict(env, DYLD_INSERT_LIBRARIES=str(library)), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    (cache / f"piano-heap-{mode}.log").write_text(run.stdout)
    run.check_returncode()
    rows = []; label = ""
    for line in run.stdout.splitlines():
        match = pattern.fullmatch(line)
        if match:
            rows.append(dict(phase=label, **dict(zip(["allocations", "bytes", "copies", "copy_bytes"], map(int, match.groups())))))
        else:
            label = line
    assert len(rows) == 23, rows
    assert rows[0]["allocations"] == 0 and rows[0]["copies"] == 0
    assert rows[1]["allocations"] > 0 and rows[2]["copies"] > 0
    for row in rows[3:]:
        if row["phase"].startswith("preparation"):
            assert row["allocations"] > 0
        else:
            assert row["allocations"] == 0 and row["copies"] == 0, row
    report["modes"][mode] = rows
    print(f"{mode}: positive controls valid; piano strike/render/control/reset allocation-free", flush=True)
(cache / "piano-resource-validation.json").write_text(json.dumps(report, indent=2) + "\n")
