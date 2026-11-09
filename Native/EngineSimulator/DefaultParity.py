#!/usr/bin/env python3
"""Check bundled renderer packets independently of Silex PCM processing."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def unpack(package, output):
    asset = package / 'Assets/Engines/macos-arm64'
    manifest = json.loads((asset / 'Manifest.json').read_text())
    packed = (asset / 'Library.bin').read_bytes()
    assert hashlib.sha256(packed).hexdigest() == manifest['sha256']
    library = output / 'library'
    for entry in manifest['files']:
        path = library / entry['path']
        assert path.resolve().is_relative_to(library.resolve())
        data = packed[entry['offset']:entry['offset'] + entry['size']]
        assert len(data) == entry['size']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (library / 'RenderReference').chmod(0o700)
    return library


def render(library, profile, slot):
    key = profile['key']
    runtime = library / 'Runtime'
    mode = 'follow-intake' if key == 'cross4' else 'follow'
    commands = ''.join(f'480 1 {load} 1 1 {rpm} 0\n' * 40
                       for rpm, load in [(850, 0.1), (2500, 0.8), (1200, 0)])
    result = subprocess.run([str(library / 'RenderReference'),
                             str(runtime / ('Profile-' + key + '.mr')),
                             str(runtime / ('Impulse-' + key + '.pcm')),
                             'unused', mode, str(slot)], cwd=runtime,
                            input=commands.encode(), capture_output=True,
                            timeout=90, check=True)
    size = 16 + 480 * (4 if key == 'cross4' else 2)
    assert len(result.stdout) == 120 * size
    for offset in range(0, len(result.stdout), size):
        magic, frames, rpm, flags = struct.unpack_from('<4I', result.stdout, offset)
        assert magic == (0x42563845 if key == 'cross4' else 0x41563845)
        assert frames == 480 and flags == 0
    return result.stdout, size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    assert args.repetitions >= 2
    package = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    library = unpack(package, output)
    profiles = json.loads(Path(__file__).with_name('Profiles.json').read_text())['profiles']
    report = {'renderer_sha256': hashlib.sha256((library / 'RenderReference').read_bytes()).hexdigest(),
              'repetitions': args.repetitions, 'profiles': []}
    for slot, profile in enumerate(profiles):
        baseline, size = render(library, profile, slot)
        for repeat in range(1, args.repetitions):
            actual, _ = render(library, profile, slot)
            if actual != baseline:
                (output / (profile['key'] + '-baseline.bin')).write_bytes(baseline)
                (output / (profile['key'] + '-actual.bin')).write_bytes(actual)
                offset = next(i for i, pair in enumerate(zip(baseline, actual)) if pair[0] != pair[1])
                raise AssertionError(f"Native packet mismatch profile={profile['key']} repeat={repeat} block={offset // size} byte={offset % size}: {baseline[offset]} != {actual[offset]}")
        report['profiles'].append({'key': profile['key'], 'packet_sha256': hashlib.sha256(baseline).hexdigest()})
        print('PASS native packet parity ' + profile['key'], flush=True)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
