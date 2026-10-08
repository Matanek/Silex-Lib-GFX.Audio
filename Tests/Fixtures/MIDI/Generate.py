"""Deterministic partitions for parser/timing and audible consumer qualification."""
from fractions import Fraction
from pathlib import Path
import struct

root = Path(__file__).parent

def vlq(value):
    data = [value & 127]
    while value >> 7:
        value >>= 7
        data.insert(0, 128 | (value & 127))
    return bytes(data)

def track(events):
    result = bytearray(); previous = 0
    for tick, message in events:
        assert tick >= previous
        result += vlq(tick - previous) + bytes(message); previous = tick
    return b'MTrk' + struct.pack('>I', len(result)) + result

def write(name, tracks, format=1, ppqn=480):
    result = b'MThd' + struct.pack('>IHHH', 6, format, len(tracks), ppqn) + b''.join(track(events) for events in tracks)
    (root / name).write_bytes(result)

# Tempo-map changes precede musical events at the same tick after track merge.
write('Tempo.mid', [
    [(0,[255,81,3,7,161,32]), (0,[192,0]), (0,[176,10,32]), (0,[144,45,72]),
     (480,[45,0]), (480,[144,48,66]), (960,[48,0]), (960,[144,50,70]),
     (1440,[50,0]), (1440,[144,52,72]), (1920,[255,81,3,6,26,128]),
     (1920,[144,52,0]), (1920,[144,53,70]), (2400,[53,0]), (2400,[144,52,66]),
     (2880,[52,0]), (2880,[144,48,68]), (3360,[48,0]), (3360,[144,45,72]),
     (3840,[45,0]), (3840,[255,47,0])],
    [(0,[193,1]), (0,[177,10,96]), (0,[145,69,80]), (240,[69,0]),
     (480,[145,72,84]), (720,[72,0]), (960,[145,74,88]), (1200,[74,0]),
     (1440,[145,76,90]), (1680,[76,0]), (1920,[193,2]), (1920,[177,64,127]),
     (1920,[145,77,86]), (2160,[77,0]), (2400,[145,76,82]), (2640,[76,0]),
     (2880,[177,11,80]), (2880,[145,72,80]), (3120,[72,0]),
     (3360,[145,69,78]), (3600,[69,0]), (3840,[177,64,0]), (3840,[255,47,0])]])
# Small independent oracle: 96 PPQN, half-second then three-quarter-second beat.
write('TwoTracks.mid', [
    [(0,[255,81,3,7,161,32]), (96,[255,81,3,11,113,176]), (288,[255,47,0])],
    [(0,[192,0]), (0,[144,69,127]), (96,[69,0]), (96,[144,72,64]),
     (192,[72,0]), (288,[255,47,0])]], ppqn=96)
# Published RP-001 example, reconstructed bytes rather than an external asset.
write('Standard0.mid', [[(0,[255,88,4,4,2,24,8]), (0,[255,81,3,7,161,32]),
    (0,[192,5]), (0,[193,46]), (0,[194,70]), (0,[146,48,96]), (0,[60,96]),
    (96,[145,67,64]), (192,[144,76,32]), (384,[130,48,64]), (384,[60,64]),
    (384,[129,67,64]), (384,[128,76,64]), (384,[255,47,0])]], format=0, ppqn=96)
write('Standard1.mid', [
    [(0,[255,88,4,4,2,24,8]),(0,[255,81,3,7,161,32]),(384,[255,47,0])],
    [(0,[192,5]),(192,[144,76,32]),(384,[76,0]),(384,[255,47,0])],
    [(0,[193,46]),(96,[145,67,64]),(384,[67,0]),(384,[255,47,0])],
    [(0,[194,70]),(0,[146,48,96]),(0,[60,96]),(384,[48,0]),(384,[60,0]),(384,[255,47,0])]], ppqn=96)
# Exact absolute timing for audible score: tempo changes at tick1920.
for tick in [0,240,480,960,1440,1920,2160,2400,2880,3360,3840]:
    seconds = Fraction(min(tick,1920)*500000 + max(0,tick-1920)*400000,480*1000000)
    frame = (seconds*48000 + Fraction(1,2)).numerator // (seconds*48000 + Fraction(1,2)).denominator
    print(tick, frame)
assert (root/'Tempo.mid').stat().st_size < 512

# A tick is one frame at 8000 Hz. Releasing channel 1 before channel 0 distinguishes identities.
write('ChannelIdentity.mid', [[(0,[192,99]),(0,[176,64,127]),(0,[224,0,80]),
    (0,[208,45]),(0,[144,69,127]),(1,[145,69,100]),(2,[129,69,0]),
    (3,[128,69,0]),(4,[255,47,0])]], format=0, ppqn=4000)
# Three hours of metadata, two notes, no corresponding PCM materialization at startup.
write('Long.mid', [[(0,[144,69,100]),(96,[128,69,0]),(2073600,[255,47,0])]], format=0, ppqn=96)
