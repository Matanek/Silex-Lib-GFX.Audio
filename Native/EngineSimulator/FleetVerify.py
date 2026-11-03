#!/usr/bin/env python3
"""Vérifier les profils, la boîte et les transitions du témoin natif."""
import argparse
import array
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def render(binary, runtime, profile, index, commands):
    result = subprocess.run([str(binary), str(runtime / ('Profile-' + profile['key'] + '.mr')),
        str(runtime / ('Impulse-' + profile['key'] + '.pcm')), 'unused', 'drive', str(index)],
        cwd=runtime, input=''.join(commands).encode(), capture_output=True, timeout=90, check=True)
    size = 32 + 960 * 2
    assert len(result.stdout) == size * len(commands), 'Taille de paquets'
    rows, samples = [], array.array('h')
    for offset in range(0, len(result.stdout), size):
        magic, frames, rpm, starting, gear, speed, flags, shifts = struct.unpack_from('<8I', result.stdout, offset)
        assert magic == 0x36563845 and frames == 960 and starting in (0, 1)
        assert 0 <= gear <= len(profile['ratios']) and flags <= 3
        assert rpm < profile['ceiling'] * 1300 and speed < 600000, 'Télémétrie bornée'
        rows.append(dict(rpm=rpm / 1000, gear=gear, speed=speed / 1000, flags=flags, shifts=shifts))
        samples.frombytes(result.stdout[offset + 32:offset + size])
    assert max(abs(value) for value in samples) < 32767, 'Écrêtage'
    return rows, samples


def command(contact=1, pedal=0, mode=1, gear=0, brake=0):
    return f'960 {contact} {pedal} 1 1 800 0.2 {mode} {gear} {brake}\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--profile', help='Limiter la vérification à une clé du catalogue')
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    binary, runtime = args.binary.resolve(), args.runtime.resolve()
    profiles = json.loads(Path(__file__).with_name('Profiles.json').read_text())['profiles']
    report = dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), profiles=[])
    for index, profile in enumerate(profiles):
        if args.profile and profile['key'] != args.profile: continue
        commands = [command(contact=0)] * 12 + [command()] * 190 + [command(pedal=1)] * 1400
        commands += [command(brake=1)] * 700 + [command(contact=0, brake=1)] * 400
        rows, samples = render(binary, runtime, profile, index, commands)
        assert all(x == 0 for x in samples[:12 * 960]), 'Départ silencieux'
        assert 350 < rows[201]['rpm'] < 3500, 'Ralenti autonome'
        moving = rows[202:1602]
        assert max(row['gear'] for row in moving) >= 2 and max(row['speed'] for row in moving) > 25, 'Passages auto et départ'
        assert rows[2301]['speed'] < 0.5, 'Freinage'
        assert rows[-1]['speed'] < 0.5 and rows[-1]['rpm'] < 5, 'Arrêt'
        last_shift = -100
        previous_gear = 0
        for position, row in enumerate(rows):
            if row['gear'] != previous_gear:
                # Normal auto hysteresis; very low speed can change neutral at launch.
                if previous_gear and row['gear']:
                    assert position - last_shift >= 30, 'Pompage de la boîte automatique'
                last_shift, previous_gear = position, row['gear']
        item = dict(key=profile['key'], idle_rpm=rows[201]['rpm'], max_rpm=max(x['rpm'] for x in rows),
            max_gear=max(x['gear'] for x in rows), max_kmh=max(x['speed'] for x in rows),
            peak_pcm=max(abs(x) for x in samples), auto_brake_stop=True)
        report['profiles'].append(item)
        print(json.dumps(item), flush=True)
    # Reach speed in auto, reject first gear, engage a safe upper gear, neutral,
    # brake to rest and restart in first. The command phases define reviewable boundaries.
    commands = [command()] * 180 + [command(pedal=1)] * 1200
    commands += [command(mode=2, gear=1)] * 40
    commands += [command(mode=2, gear=6)] * 40
    commands += [command(mode=2, gear=0)] * 50
    commands += [command(mode=2, gear=0, brake=1)] * 700
    commands += [command(mode=2, gear=1, pedal=1)] * 300
    rows, _ = render(binary, runtime, profiles[0], 0, commands)
    before = rows[1379]
    assert before['speed'] > 100 and before['gear'] >= 3
    assert all(row['gear'] == before['gear'] and row['flags'] >= 2 for row in rows[1380:1420]), 'Rétrogradage protégé'
    assert rows[1459]['gear'] == 6, 'Rapport manuel sûr'
    assert rows[1509]['gear'] == 0 and rows[1509]['speed'] > 60, 'Point mort'
    # Gear changes preserve vehicle kinetic energy; normal braking/drag may change speed.
    assert abs(rows[1420]['speed'] - rows[1419]['speed']) < 1, 'Saut de vitesse au changement de rapport'
    assert rows[2209]['speed'] < 0.5 and rows[-1]['speed'] > 15, 'Arrêt et redépart manuel'
    report['manual'] = dict(unsafe_downshift_rejected=True, neutral=True, continuous_speed=True, stop_restart=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('Fleet native checks passed', flush=True)


if __name__ == '__main__':
    main()
