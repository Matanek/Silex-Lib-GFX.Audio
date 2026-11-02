"""Qualify prepared engine + room DSP allocations with a positive control."""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess

fixture = Path(__file__).resolve().parent
workspace = fixture.parents[3]
if Path.cwd().resolve() != workspace:
    raise SystemExit("Run from SilexProject or the owning Spec Worktree group")
if platform.system() != "Darwin" or platform.machine() != "arm64":
    raise SystemExit("This allocation counter is qualified for macOS ARM64 only")
compiler = Path(os.environ.get("SILEX_EXECUTABLE", shutil.which("silex") or "silex")).resolve()
cache = workspace / ".silex"
cache.mkdir(exist_ok=True)
environment = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(cache / "zig-global"))
library = cache / "engine-heap-probe.dylib"
subprocess.run(["clang", "-dynamiclib", "-arch", "arm64", "-O2", "-fno-builtin",
                "-Wall", "-Wextra", "-Werror", str(fixture / "HeapProbe.c"),
                "-o", str(library)], check=True)
pattern = re.compile(r"AUDIO_HEAP allocations=(\d+) bytes=(\d+) copies=(\d+) copy_bytes=(\d+)")
report = {"host": platform.platform(), "target": "macos-arm64",
          "compiler_sha256": hashlib.sha256(compiler.read_bytes()).hexdigest(),
          "scope": "Prepared Engine and composed Reverb DSP on the marked thread; excludes Audio.write, SDL and UI",
          "modes": {}}
for mode in ["debug", "release"]:
    binary = cache / f"engine-heap-{mode}"
    subprocess.run([str(compiler), "compile", str(fixture / "EngineHeap.sx"),
                    f"--{mode}", "-o", str(binary)], cwd=workspace,
                   env=environment, check=True, timeout=120)
    run = subprocess.run([str(binary)], cwd=workspace,
                         env=dict(environment, DYLD_INSERT_LIBRARIES=str(library)),
                         text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    (cache / f"engine-heap-{mode}.log").write_text(run.stdout)
    run.check_returncode()
    rows = []
    label = ""
    for line in run.stdout.splitlines():
        match = pattern.fullmatch(line)
        if match:
            rows.append({"phase": label, **dict(zip(
                ["allocations", "bytes", "copies", "copy_bytes"], map(int, match.groups())))})
        else:
            label = line
    assert len(rows) == 6, rows
    assert rows[0]["allocations"] == 0 and rows[1]["allocations"] > 0
    assert rows[2]["allocations"] > 0
    for row in [rows[0], *rows[3:]]:
        assert row["allocations"] == 0, row
    report["modes"][mode] = rows
    print(f"{mode}: positive control valid; engine + room render, controls and reset allocation-free")
(cache / "engine-resource-validation.json").write_text(json.dumps(report, indent=2) + "\n")
