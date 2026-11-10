"""Check the shipped sampled voice independently from its preparation script."""
import cmath
import hashlib
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parents[2] / 'Assets/Engines/Voices'
data = (root / 'Diesel.pcm').read_bytes()
metadata = json.loads((root / 'Diesel.json').read_text())
assert hashlib.sha256(data).hexdigest() == metadata['sha256']
assert len(data) == 8 * 1024 * 2
assert len(metadata['source_recording_sha256']) == 64
assert all(0.7 < excerpt['periodicity'] <= 1 for excerpt in metadata['excerpts'])
samples = struct.unpack('<8192h', data)
for table in range(8):
    values = [value / 32768 for value in samples[table*1024:(table+1)*1024]]
    assert max(abs(value) for value in values) <= 0.901
    assert abs(sum(values) / 1024) < 0.00001
    assert sum(value*value for value in values) / 1024 > 0.01
    for harmonic in [129, 180, 256, 400]:
        amplitude = abs(sum(value*cmath.exp(-2j*cmath.pi*harmonic*i/1024) for i,value in enumerate(values))) / 1024
        assert amplitude < 0.00001, 'voice exceeds its playback band limit'
print('Vehicle voice checks passed: provenance, eight bounded excitations, DC and harmonic limits')
