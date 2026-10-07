"""Verify that waiting cannot silently hang an offline renderer."""
import os
from pathlib import Path
import subprocess
import tempfile
owner = Path(__file__).resolve().parents[1]
workspace = owner.parents[1]
compiler = Path(os.environ.get("SILEX_EXECUTABLE", str(workspace / "Silex/Toolchain/zig-out/bin/silex")))
with tempfile.TemporaryDirectory(prefix="OfflineValidation_", dir=owner / "Tests") as temporary:
    source = Path(temporary) / "Wait.sx"
    source.write_text('''use GFX.Audio
func main() {
    match Audio.offline(sample_rate:48_000) {
        failure(error) => { panic(error.detail) }
        success(var audio) => {
            var samples:float32[] = [0.25 as float32]
            let sound = audio.create(@samples[0:1], sample_rate:48_000)
            let playing = audio.play(sound)
            audio.wait(playing)
        }
    }
}
''')
    result = subprocess.run([str(compiler), "run", str(source), "--release", "--nocache"], cwd=workspace,
                            env=dict(os.environ, SDL_AUDIODRIVER="__silex_no_audio_driver__"),
                            capture_output=True, text=True, timeout=45)
    output = result.stdout + result.stderr
    if result.returncode == 0 or "runtime error: GFX.Audio offline playback progresses through render, not wait" not in output:
        raise AssertionError(output)
print("ok - offline wait reports a diagnostic instead of hanging")
