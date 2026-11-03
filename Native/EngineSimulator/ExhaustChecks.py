#!/usr/bin/env python3
"""Check exhaust slider transitions offline, without opening an audio device."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess


def render(binary, runtime, amount, key='454', index=0):
    commands = [f'480 1 {int(block >= 220)} 1 {1 if block < 400 else amount} 800 0.2\n'
                for block in range(1000)]
    result = subprocess.run([str(binary), str(runtime / f'Profile-{key}.mr'),
        str(runtime / f'Impulse-{key}.pcm'), 'unused', 'serve', str(index)],
        cwd=runtime, input=''.join(commands).encode(), capture_output=True, check=True, timeout=90)
    headers, samples = [], array.array('h')
    position = 0
    for _ in commands:
        magic, frames, rpm, starting = struct.unpack_from('<4I', result.stdout, position)
        assert magic == 0x34563845 and frames == 480 and starting in (0, 1)
        headers.append((rpm, starting))
        position += 16
        samples.frombytes(result.stdout[position:position + frames * 2])
        position += frames * 2
    assert position == len(result.stdout)
    return headers, samples


def metrics(samples):
    power = sum(value * value for value in samples) / len(samples)
    delta = sum((b - a) ** 2 for a, b in zip(samples, samples[1:])) / (len(samples) - 1)
    return dict(rms=math.sqrt(power), peak=max(abs(value) for value in samples),
                clipping=sum(abs(value) >= 32767 for value in samples),
                diff_over_rms=math.sqrt(delta / power) if power else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    binary, baseline, runtime = args.binary.resolve(), args.baseline.resolve(), args.runtime.resolve()
    report = dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                  baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(), profiles=[], mixes=[])
    profiles = json.loads(Path(__file__).with_name('Profiles.json').read_text())['profiles']
    for index, profile in enumerate(profiles):
        expected_headers, expected = render(baseline, runtime, 1, profile['key'], index)
        headers, samples = render(binary, runtime, 1, profile['key'], index)
        assert headers == expected_headers and samples == expected, '100% convolution changed: ' + profile['key']
        report['profiles'].append(dict(key=profile['key'], full_convolution_bit_exact=True))
        print(profile['key'] + ': 100% bit exact', flush=True)
        if index == 0:
            reference_headers, reference = headers, samples
    reference_metrics = metrics(reference[900 * 480:])
    for amount in (0.999, 0.99, 0.9, 0.5, 0.0):
        headers, samples = render(binary, runtime, amount)
        assert headers == reference_headers, 'Exhaust blend changed engine physics'
        phases = [dict(phase=name, **metrics(samples[start * 480:end * 480]))
                  for name, start, end in [('before', 390, 400), ('first', 400, 410), ('settled', 900, 1000)]]
        assert all(phase['clipping'] == 0 for phase in phases), 'Clipped transition'
        assert metrics(samples)['clipping'] == 0, 'Clipped full scenario'
        if amount >= 0.99:
            error = [a - b for a, b in zip(samples[400 * 480:], reference[400 * 480:])]
            relative_error = metrics(error)['rms'] / metrics(reference[400 * 480:])['rms']
            assert relative_error < 0.05, 'Small slider movement caused a large PCM change'
        else:
            relative_error = None
        assert phases[-1]['diff_over_rms'] < reference_metrics['diff_over_rms'] * 1.5, 'Excessive sample-to-sample roughness'
        item = dict(mix=amount, phases=phases, relative_error=relative_error)
        report['mixes'].append(item)
        print(json.dumps(item), flush=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('Exhaust checks passed; perceptual listening still required', flush=True)


if __name__ == '__main__':
    main()
