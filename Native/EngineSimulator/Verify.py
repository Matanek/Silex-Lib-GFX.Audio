#!/usr/bin/env python3
"""Vérifier le protocole, la répétabilité et le transfert PCM du témoin natif."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import time
import wave


def render(binary, runtime):
    requests = []
    for block in range(1200):
        contact = int(30 <= block < 950)
        pedal = int(460 <= block < 650)
        requests.append(f'480 {contact} {pedal} 1 1 800 0.2\n')
    start = time.perf_counter()
    result = subprocess.run([str(binary), str(runtime / 'Profile454.mr'), str(runtime / 'Impulse.pcm'), 'unused', 'serve'],
        cwd=runtime, input=''.join(requests).encode(), capture_output=True, timeout=60, check=True)
    elapsed = time.perf_counter() - start
    data = result.stdout
    position = 0
    samples = array.array('h')
    rpms = []
    for _ in range(1200):
        if position + 16 > len(data):
            raise RuntimeError('Paquet tronqué')
        magic, frames, rpm, starting = struct.unpack_from('<IIII', data, position)
        if magic != 0x34563845 or frames != 480 or starting not in (0, 1):
            raise RuntimeError('En-tête invalide')
        position += 16
        samples.frombytes(data[position:position + frames * 2])
        position += frames * 2
        rpms.append(rpm)
    if position != len(data) or len(samples) != 1200 * 480:
        raise RuntimeError('Longueur PCM invalide')
    return samples, rpms, elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--scalar-binary', type=Path)
    parser.add_argument('--bridge-wave', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    binary, runtime = args.binary.resolve(), args.runtime.resolve()
    samples, rpms, elapsed = render(binary, runtime)
    repeated, repeated_rpms, _ = render(binary, runtime)
    assert samples == repeated and rpms == repeated_rpms, 'Rendu non répétable'
    assert all(value == 0 for value in samples[:30 * 480]), 'Départ moteur éteint'
    assert rpms[30] < 100000 and 650000 < rpms[420] < 1300000, 'Démarreur et ralenti'
    assert max(rpms) > 4000000 and rpms[950] > 200000 and rpms[-1] < 5000, 'Régime et inertie'
    assert max(abs(value) for value in samples) < 32767, 'Écrêtage'
    assert max(abs(value) for value in samples[-4800:]) <= 1, 'Silence final'
    invalid = subprocess.run([str(binary), str(runtime / 'Profile454.mr'), str(runtime / 'Impulse.pcm'), 'unused', 'serve'],
        cwd=runtime, input=b'961 0 0 1 1 800 0.2\n', capture_output=True, timeout=5)
    assert invalid.returncode == 1 and not invalid.stdout, 'Rejet des commandes invalides'
    report = dict(repeat_bit_exact=True, frames=len(samples), sample_rate=44100,
        elapsed_seconds=elapsed, rpm_max=max(rpms) / 1000, peak_pcm=max(abs(value) for value in samples),
        invalid_request_rejected=True, binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    if args.scalar_binary:
        scalar, scalar_rpms, _ = render(args.scalar_binary.resolve(), runtime)
        error = [a - b for a, b in zip(samples, scalar)]
        rms = math.sqrt(sum(value * value for value in error) / len(error)) / 32768
        maximum = max(abs(value) for value in error)
        assert scalar_rpms == rpms and maximum <= 32 and rms <= 1e-4, 'Équivalence FIR'
        report['scalar_error'] = dict(max_pcm=maximum, rms_full_scale=rms, rpm_identical=True)
    if args.bridge_wave:
        with wave.open(str(args.bridge_wave), 'rb') as stream:
            assert (stream.getnchannels(), stream.getframerate(), stream.getsampwidth()) == (2, 44100, 2)
            bridge = array.array('h', stream.readframes(stream.getnframes()))
        assert len(bridge) == len(samples) * 2
        maximum = 0
        for index, sample in enumerate(samples):
            expected = round(sample * 0.7 * 32767 / 32768)
            left, right = bridge[index * 2:index * 2 + 2]
            assert left == right, 'Copie mono vers stéréo'
            maximum = max(maximum, abs(left - expected))
        assert maximum <= 1, 'Transfert PCM Silex altéré'
        report['bridge_error_max_pcm'] = maximum
    text = json.dumps(report, indent=2) + '\n'
    print(text)
    if args.report:
        args.report.write_text(text)


if __name__ == '__main__':
    main()
