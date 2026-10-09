"""Verify that direct musical-name conversions terminate on invalid input."""
import os
from pathlib import Path
import subprocess
import tempfile

owner = Path(__file__).resolve().parents[1]
workspace = owner.parents[1]
compiler = Path(os.environ.get("SILEX_EXECUTABLE", str(workspace / "Silex/Toolchain/zig-out/bin/silex")))
environment = dict(os.environ,
    ZIG_GLOBAL_CACHE_DIR=str(workspace / ".silex/zig-global"),
    ZIG_LOCAL_CACHE_DIR=str(workspace / ".silex/zig-local"))
cases = [("Single", 'Music.key("NotANote")', "NotANote"),
    ("List", 'Music.keys(["C5", "bad", "G5"])', "bad")]
with tempfile.TemporaryDirectory(prefix="DirectKeys_", dir=owner / "Tests/Consumer") as temporary:
    for name, expression, subject in cases:
        entry = Path(temporary) / (name + ".sx")
        entry.write_text('use GFX.Audio.Music\nfunc main() {\n'
            + '    let value = ' + expression + '\n'
            + '    print("UNEXPECTED COMPLETION")\n}\n')
        artifact = Path(temporary) / name
        for mode in ["interpret", "debug", "release"]:
            if mode == "interpret":
                command = [str(compiler), "interpret", str(entry)]
            else:
                command = [str(compiler), "compile", str(entry), "--nocache", "-o", str(artifact)]
                if mode == "release":
                    command.append("--release")
                subprocess.run(command, cwd=workspace, env=environment, check=True, timeout=90)
                command = [str(artifact)]
            result = subprocess.run(command, cwd=workspace, env=environment, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
            assert result.returncode > 0, (name, mode, result.returncode, result.stdout)
            assert "UNEXPECTED COMPLETION" not in result.stdout, result.stdout
            assert subject in result.stdout and "MIDI 0..127" in result.stdout, result.stdout
            print(f"ok - invalid {name.lower()} input terminates in {mode}", flush=True)
print("6 direct-conversion failure checks passed")
