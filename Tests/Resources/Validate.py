"""Check prepared DSP allocations on macOS ARM64 with positive controls."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

fixture = Path(__file__).resolve().parent
workspace = fixture.parents[3]
if Path.cwd().resolve() != workspace:
    raise SystemExit("Run from the SilexProject root or the Spec Worktree group root")
if platform.system() != "Darwin" or platform.machine() != "arm64":
    raise SystemExit("This allocation gate covers macOS ARM64; X64 raw syscalls bypass libc interposition")
cache = workspace / ".silex"
cache.mkdir(exist_ok=True)
compiler = Path(os.environ.get("SILEX_EXECUTABLE", workspace / "Silex/Toolchain/zig-out/bin/silex"))
library = cache / "audio-heap-probe.dylib"
subprocess.run(["clang", "-dynamiclib", "-arch", "arm64", "-arch", "x86_64", "-O2", "-fno-builtin",
                "-Wall", "-Wextra", "-Werror", str(fixture / "HeapProbe.c"), "-o", str(library)], check=True)
environment = dict(os.environ, SDL_AUDIODRIVER="__silex_no_audio_driver__")
pattern = re.compile(r"AUDIO_HEAP allocations=(\d+) bytes=(\d+) copies=(\d+) copy_bytes=(\d+)")
report = {
    "target": "macos-arm64",
    "host": platform.platform(),
    "compiler_path": str(compiler.resolve()),
    "compiler_sha256": hashlib.sha256(compiler.read_bytes()).hexdigest(),
    "counter_sha256": hashlib.sha256((fixture / "HeapProbe.c").read_bytes()).hexdigest(),
    "source_sha256": hashlib.sha256((fixture / "HeapProbe.sx").read_bytes()).hexdigest(),
    "workspace_heads": {
        "GFX.Audio": subprocess.check_output(["git", "-C", str(fixture.parents[1]), "rev-parse", "HEAD"], text=True).strip(),
        "Silex": subprocess.check_output(["git", "-C", str(workspace / "Silex"), "rev-parse", "HEAD"], text=True).strip(),
    },
    "modes": {},
}
for mode in ["debug", "release"]:
    artifact = cache / f"audio-heap-probe-{mode}"
    subprocess.run([str(compiler), "compile", str(fixture / "HeapProbe.sx"), f"--{mode}", "--target", "macos-arm64", "--nocache", "-o", str(artifact)],
                   cwd=workspace, env=environment, check=True, timeout=90)
    executed = subprocess.run([str(artifact)], cwd=workspace, env=dict(environment, DYLD_INSERT_LIBRARIES=str(library)),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=45)
    (cache / f"audio-heap-probe-{mode}.log").write_text(executed.stdout)
    executed.check_returncode()
    rows = []
    label = ""
    workload = "controls"
    for line in executed.stdout.splitlines():
        match = pattern.fullmatch(line)
        if match:
            values = dict(zip(["allocations", "bytes", "copies", "copy_bytes"], map(int, match.groups())))
            rows.append(dict(workload=workload, phase=label, **values))
        else:
            label = line
            if line.startswith("voices="):
                workload = line.removesuffix(" preparation")
            elif line.startswith("PCM"):
                workload = "PCM transfer"
    assert len(rows) == 135, f"Incomplete phase protocol: {len(rows)}"
    assert rows[0]["phase"] == "empty" and rows[0]["allocations"] == 0
    assert rows[1]["phase"] == "positive allocation" and rows[1]["allocations"] > 0
    for row in rows:
        if "preparation" in row["phase"]:
            assert row["allocations"] > 0
        elif row["phase"] != "positive allocation" and row["workload"] != "PCM transfer":
            assert row["allocations"] == 0 and row["copies"] == 0, row
    transfer = [row for row in rows if row["workload"] == "PCM transfer"]
    assert len(transfer) == 101 and any(row["copies"] > 0 for row in transfer), "Missing positive copy control"
    report["modes"][mode] = rows
    print(f"{mode}: controls valid, prepared DSP/commands/reset allocation-free; PCM transfer measured separately", flush=True)
(cache / "audio-resource-validation.json").write_text(json.dumps(report, indent=2) + "\n")
