"""Generate a three-hour SMF with 16 held notes and 32 note commands."""
from pathlib import Path
import struct


def vlq(value):
    result = [value & 127]
    value >>= 7
    while value:
        result.insert(0, 128 | (value & 127))
        value >>= 7
    return bytes(result)


track = b"".join(bytes([0, 0x90, key, 32]) for key in range(48, 64))
for index, key in enumerate(range(48, 64)):
    track += vlq(10_368_000 if index == 0 else 0) + bytes([0x80, key, 0])
track += bytes([0, 0xFF, 0x2F, 0])
data = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
data += b"MTrk" + struct.pack(">I", len(track)) + track
path = Path(__file__).with_name("PolyphonicLong.mid")
if path.exists():
    assert path.read_bytes() == data, "Existing qualification fixture differs"
else:
    path.write_bytes(data)
print(f"{len(data)} bytes: 16 notes, 32 commands, 3 hours at 120 BPM")
