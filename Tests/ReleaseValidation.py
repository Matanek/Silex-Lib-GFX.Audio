"""Run public PCM oracles in Release, or compose them for another target."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--target")
parser.add_argument("--execute", action="store_true", help="also execute an explicitly selected host-compatible target")
options = parser.parse_args()
owner = Path(__file__).resolve().parents[1]
workspace = owner.parents[1]
compiler = Path(os.environ.get("SILEX_EXECUTABLE", str(workspace / "Silex/Toolchain/zig-out/bin/silex")))
sources = ["Tests/Processing.sx", "Tests/Consumer/Tests/Production.sx", "Tests/Consumer/Tests/StreamGroups.sx", "Tests/Consumer/Tests/Synthesis.sx", "Tests/Consumer/Tests/Waveforms.sx"]
environment = dict(os.environ, SDL_AUDIODRIVER="__silex_no_audio_driver__")
count = 0
with tempfile.TemporaryDirectory(prefix="ReleaseValidation_", dir=owner / "Tests") as temporary:
    for index, relative in enumerate(sources):
        original = owner / relative
        cases = []
        def replace(match):
            name = f"release_case_{len(cases)}"
            cases.append(name)
            return f"func {name}() {{"
        source = re.sub(r'^test "[^"\n]+"\s*\{', replace, original.read_text(), flags=re.MULTILINE)
        if not cases:
            raise AssertionError(f"no test cases in {relative}")
        source += "\nfunc main() {\n" + "".join(f"    {case}()\n" for case in cases) + "}\n"
        entry = Path(temporary) / f"Oracles{index}.sx"
        entry.write_text(source)
        artifact = Path(temporary) / f"oracles{index}"
        arguments = [str(compiler), "compile", str(entry), "--release", "--nocache", "-o", str(artifact)]
        if options.target:
            arguments += ["--target", options.target]
        subprocess.run(arguments, cwd=workspace, env=environment, check=True, timeout=90)
        if not options.target or options.execute:
            subprocess.run([str(artifact)], cwd=workspace, env=environment, check=True, timeout=45)
        count += len(cases)
        print(f"ok - {relative}: {len(cases)} Release oracles", flush=True)
print(f"{count} Release oracles {'executed' if not options.target or options.execute else 'linked'}")
