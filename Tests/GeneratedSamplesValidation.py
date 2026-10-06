"""Check Audio.create rejection diagnostics through the public package API."""

import os
from pathlib import Path
import subprocess
import tempfile


owner = Path(__file__).resolve().parents[1]
workspace = owner.parents[1]
compiler = Path(os.environ.get("SILEX_EXECUTABLE", str(workspace / "Silex/Toolchain/zig-out/bin/silex")))
cases = [
    ("empty", "[]", "48_000", "1", "samples must contain at least one complete frame"),
    ("partial_frame", "[0.0 as float32]", "48_000", "2", "samples must contain at least one complete frame"),
    ("zero_rate", "[0.0 as float32]", "0", "1", "sample rate must be between"),
    ("overflow_rate", "[0.0 as float32]", "2_147_483_648", "1", "sample rate must be between"),
    ("zero_channels", "[0.0 as float32]", "48_000", "0", "sample channels must be between"),
    ("excess_channels", "[0.0 as float32]", "48_000", "9", "sample channels must be between"),
    ("positive_amplitude", "[1.1 as float32]", "48_000", "1", "samples must be finite"),
    ("negative_amplitude", "[-1.1 as float32]", "48_000", "1", "samples must be finite"),
    ("nan", "[Math.sqrt(-1.0) as float32]", "48_000", "1", "samples must be finite"),
    ("infinity", "[Math.exp(1_000.0) as float32]", "48_000", "1", "samples must be finite"),
]
environment = dict(os.environ, SDL_AUDIODRIVER="dummy")
with tempfile.TemporaryDirectory(prefix="GeneratedValidation_", dir=owner / "Tests") as temporary:
    for name, samples, rate, channels, diagnostic in cases:
        source = Path(temporary) / f"{name}.sx"
        source.write_text(
            "use GFX.Audio\nuse STD.Math\nfunc main() {\n"
            f"    var samples:float32[] = {samples}\n"
            "    var audio = Audio()\n"
            f"    let sound = audio.create(@samples[0:samples.count()], sample_rate:{rate}, channels:{channels})\n"
            "}\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [str(compiler), "run", str(source), "--nocache"],
            cwd=workspace, env=environment, capture_output=True, text=True, timeout=60,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or f"runtime error: GFX.Audio {diagnostic}" not in output:
            raise AssertionError(f"{name}: expected rejection diagnostic, got:\n{output}")
        print(f"ok - {name}")
print(f"{len(cases)} rejection cases passed")
