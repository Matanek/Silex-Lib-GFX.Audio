#!/usr/bin/env python3
"""Check bundled renderer packets independently of Silex PCM processing."""
import argparse
import hashlib
import json
from pathlib import Path
import select
import struct
import subprocess
import time


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


def read_exact(stream, size, deadline):
    data = bytearray()
    while len(data) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([stream], [], [], remaining)[0]:
            raise TimeoutError('Native renderer packet deadline')
        part = stream.read(size - len(data))
        if not part:
            raise RuntimeError('Native renderer closed an incomplete packet')
        data.extend(part)
    return bytes(data)


def render(library, profile, slot):
    key = profile['key']
    runtime = library / 'Runtime'
    mode = 'follow-intake' if key == 'cross4' else 'follow'
    command = [str(library / 'RenderReference'),
               str(runtime / ('Profile-' + key + '.mr')),
               str(runtime / ('Impulse-' + key + '.pcm')),
               'unused', mode, str(slot)]
    size = 16 + 480 * (4 if key == 'cross4' else 2)
    children = []
    streams = [bytearray(), bytearray()]
    try:
        for _ in range(2):
            children.append(subprocess.Popen(command, cwd=runtime, stdin=subprocess.PIPE,
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                              bufsize=0))
        deadline = time.monotonic() + 90
        for rpm, load in [(850, 0.1), (2500, 0.8), (1200, 0)]:
            request = f'480 1 {load} 1 1 {rpm} 0\n'.encode()
            for _ in range(40):
                # Match the consumer: enqueue the asynchronous renderer first,
                # render synchronously, then collect the asynchronous packet.
                for index in [1, 0]:
                    children[index].stdin.write(request)
                    children[index].stdin.flush()
                for index in [0, 1]:
                    packet = read_exact(children[index].stdout, size, deadline)
                    magic, frames, current_rpm, flags = struct.unpack_from('<4I', packet)
                    assert magic == (0x42563845 if key == 'cross4' else 0x41563845)
                    assert frames == 480 and flags == 0
                    streams[index].extend(packet)
        for child in children:
            child.stdin.close()
            assert child.wait(timeout=5) == 0, child.stderr.read().decode(errors='replace')
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
            for pipe in [child.stdin, child.stdout, child.stderr]:
                pipe.close()
    return bytes(streams[0]), bytes(streams[1]), size


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
              'repetitions': args.repetitions, 'protocol': 'paired per-block requests', 'profiles': []}
    for slot, profile in enumerate(profiles):
        baseline = None
        for repeat in range(args.repetitions):
            synchronous, asynchronous, size = render(library, profile, slot)
            if baseline is None:
                baseline = synchronous
            for label, actual in [('synchronous', synchronous), ('asynchronous', asynchronous)]:
                if actual != baseline:
                    (output / (profile['key'] + '-baseline.bin')).write_bytes(baseline)
                    (output / (profile['key'] + '-actual.bin')).write_bytes(actual)
                    offset = next(i for i, pair in enumerate(zip(baseline, actual)) if pair[0] != pair[1])
                    raise AssertionError(f"Native packet mismatch profile={profile['key']} repeat={repeat} renderer={label} block={offset // size} byte={offset % size}: {baseline[offset]} != {actual[offset]}")
        report['profiles'].append({'key': profile['key'], 'packet_sha256': hashlib.sha256(baseline).hexdigest()})
        print('PASS native paired packet parity ' + profile['key'], flush=True)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
