"""Extract short periodic excitations from a supplied PCM reference (stdlib only).

This is a sampled acoustic voice, not a diesel combustion simulation. The
source time range identifies the excerpt; it does not identify a vehicle.
"""
import argparse
import array
import cmath
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import wave


def prepare(source, destination, original=None):
    with wave.open(str(source), 'rb') as recording:
        assert recording.getframerate() == 44100 and recording.getsampwidth() == 2
        channels = recording.getnchannels()
        pcm = array.array('h', recording.readframes(recording.getnframes()))
    if sys.byteorder != 'little':
        pcm.byteswap()
    mono = [sum(pcm[i:i+channels]) / (32768 * channels) for i in range(0, len(pcm), channels)]
    tables, origins = [], []
    for centre in [8.3, 8.46, 8.62, 8.78, 8.94, 9.1, 9.26, 9.42]:
        start = round((centre - 0.08) * 44100)
        # Low-pass/downsample only for estimating the periodic component.
        low = 0.0
        reduced = []
        for i, sample in enumerate(mono[start:start+8192]):
            low += 0.09 * (sample - low)
            if i % 8 == 0:
                reduced.append(low)
        mean = sum(reduced) / len(reduced)
        reduced = [x-mean for x in reduced]
        correlations = []
        for lag in range(25, 230):
            a, b = reduced[:600], reduced[lag:lag+600]
            norm = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b)) or 1
            correlations.append((sum(x*y for x,y in zip(a,b)) / norm, lag))
        peaks = [(score, lag) for j, (score, lag) in enumerate(correlations[1:-1], 1)
                 if score >= correlations[j-1][0] and score > correlations[j+1][0]]
        assert peaks, 'reference has no periodic excitation'
        score, lag = max(peaks)
        period = lag * 8
        cycle = mono[start:start+period]
        # Resample a single repeat, close its endpoints, remove DC, and retain
        # at most 128 harmonics so the runtime's 160 Hz ceiling cannot alias.
        values = []
        for i in range(1024):
            position = i * (period-1) / 1023
            index = int(position)
            value = cycle[index] if index+1 == period else cycle[index] + (position-index)*(cycle[index+1]-cycle[index])
            value -= cycle[0] + i/1023*(cycle[-1]-cycle[0])
            values.append(value)
        harmonics = [sum(value * cmath.exp(-2j*math.pi*k*i/1024) for i,value in enumerate(values))/1024 for k in range(1,129)]
        values = [2*sum((coefficient*cmath.exp(2j*math.pi*k*i/1024)).real for k,coefficient in enumerate(harmonics,1)) for i in range(1024)]
        zero = min(range(1024), key=lambda i: abs(values[i]))
        values = values[zero:] + values[:zero]
        rms = math.sqrt(sum(value*value for value in values)/1024)
        scale = min(0.25/rms, 0.9/max(abs(value) for value in values))
        tables.extend(round(value*scale*32767) for value in values)
        origins.append({'centre_seconds': centre, 'estimated_period_samples': period,
                        'periodicity': round(score, 4)})
    data = struct.pack('<' + 'h'*len(tables), *tables)
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'Diesel.pcm').write_bytes(data)
    report = {'kind': 'sampled-acoustic-excitation', 'source_wav_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_recording_sha256': hashlib.sha256(original.read_bytes()).hexdigest() if original else None,
              'source_description': 'User-supplied TDI comparison, excerpt 8.22..9.53 s; vehicle identity unconfirmed',
              'tables': 8, 'samples_per_table': 1024, 'format': 'signed PCM16 little endian',
              'max_harmonic': 128, 'sha256': hashlib.sha256(data).hexdigest(), 'excerpts': origins}
    (destination/'Diesel.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_wav', type=Path)
    parser.add_argument('output_directory', type=Path)
    parser.add_argument('--source-recording', type=Path, help='original recording for provenance, never modified')
    args = parser.parse_args()
    prepare(args.reference_wav, args.output_directory, args.source_recording)
