#!/usr/bin/env python3
"""Check cycle-driven intake packets without altering the exhaust simulation."""
import argparse
import array
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def render(binary, runtime, road, intake):
    commands = []
    for block in range(1600):
        contact = int(80 <= block < 850)
        pedal = int(400 <= block < 650)
        # Irregular packet sizes exercise phase continuity across quantum boundaries.
        frames = (113, 960, 367)[block % 3]
        command = f'{frames} {contact} {pedal} 1 1 800 0.2'
        if road:
            command += ' 2 0 0'  # neutral, so ignition cut can coast to rest
        commands.append(command + '\n')
    mode = ('drive' if road else 'serve') + ('-intake' if intake else '')
    result = subprocess.run([str(binary), str(runtime / 'Profile-cross4.mr'),
        str(runtime / 'Impulse-cross4.pcm'), 'unused', mode, '6'], cwd=runtime,
        input=''.join(commands).encode(), capture_output=True, check=True, timeout=90)
    headers, pressure, flow = [], array.array('h'), array.array('H')
    position = 0
    header_size = 32 if road else 16
    width = 4 if intake else 2
    magic = (0x39563845 if road else 0x38563845) if intake else (0x36563845 if road else 0x34563845)
    bounds = [0]
    for command in commands:
        frames = int(command.split()[0])
        header = struct.unpack_from('<' + 'I' * (header_size // 4), result.stdout, position)
        assert header[0] == magic and header[1] == frames
        headers.append(header[1:])
        position += header_size
        for offset in range(position, position + frames * width, width):
            pressure.append(struct.unpack_from('<h', result.stdout, offset)[0])
            if intake:
                flow.append(struct.unpack_from('<H', result.stdout, offset + 2)[0])
        position += frames * width
        bounds.append(len(pressure))
    assert position == len(result.stdout), 'Unexpected trailing bytes'
    return headers, pressure, flow, bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    binary, runtime = args.binary.resolve(), args.runtime.resolve()
    report = dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), modes=[])
    for road in (False, True):
        old_headers, old_pressure, _, _ = render(binary, runtime, road, False)
        headers, pressure, flow, bounds = render(binary, runtime, road, True)
        assert headers == old_headers and pressure == old_pressure, 'Intake capture changed physics or exhaust PCM'
        assert not any(flow[:bounds[80]]), 'Flow before starter'
        idle = flow[bounds[250]:bounds[390]]
        throttle = flow[bounds[450]:bounds[620]]
        coast = flow[bounds[850]:bounds[875]]
        stopped = flow[bounds[1500]:]
        mean = lambda values: sum(values) / len(values) * 0.25 / 65535
        assert mean(idle) > 0.0001 and mean(throttle) > mean(idle) * 2, 'Flow response to throttle'
        assert sum(value == 0 for value in idle) > len(idle) * 0.4 and max(idle) > 4 * sum(idle) / len(idle), 'Pulsed intake'
        assert max(coast) > 100 and headers[850][1] > 5000, 'Aspiration persists during ignition-off coast'
        assert headers[-1][1] < 5000 and mean(stopped) < mean(idle) * 0.02, 'Intake settles with mechanical stop'
        report['modes'].append(dict(mode='drive-intake' if road else 'serve-intake',
            frames=len(flow), exhaust_and_telemetry_bit_exact=True,
            idle_m3_s=mean(idle), throttle_m3_s=mean(throttle), stopped_m3_s=mean(stopped),
            idle_zero_fraction=sum(value == 0 for value in idle) / len(idle),
            saturated_fraction=sum(value == 65535 for value in flow) / len(flow)))
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
