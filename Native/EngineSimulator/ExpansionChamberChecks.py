#!/usr/bin/env python3
"""Verify travel time, reflection polarity and the packaged acoustic response."""
import json
from pathlib import Path
import struct

import ExpansionChamber


def main():
    cell_mm = 10
    speed = ExpansionChamber.RATE * cell_mm / 1000
    straight = [[0, 36], [400, 36]]
    inlet, outlet = ExpansionChamber.response(straight, speed, 0.5, 256)
    assert outlet[:39] == [0.] * 39 and outlet[39] > 0
    assert inlet[:79] == [0.] * 79 and inlet[79] < 0, "Open-end reflection arrives after a round trip"
    for diameter, sign in [(80, -1), (18, 1)]:
        cone = [[0, 36], [100, 36], [200, diameter], [400, diameter]]
        inlet, _ = ExpansionChamber.response(cone, speed, 0.5, 256)
        assert inlet[:19] == [0.] * 19 and sign * inlet[19] > 0

    tools = Path(__file__).resolve().parent
    profiles = json.loads((tools / "Profiles.json").read_text())["profiles"]
    geometry = next(profile["expansion_chamber"] for profile in profiles if profile["key"] == "cross2")
    data = ExpansionChamber.prepare(geometry)
    samples = [sample[0] for sample in struct.iter_unpack("<h", data)]
    assert len(samples) == round(geometry["response_ms"] * ExpansionChamber.RATE / 1000)
    assert max(map(abs, samples)) == 32760 and samples[-1] == 0
    assert sum(x * x for x in samples[-220:]) < sum(x * x for x in samples) * .001
    uniform = dict(geometry, stations_mm=[[0, 36], [1000, 36]])
    assert ExpansionChamber.prepare(uniform) != data, "Pipe geometry must affect the response"

    asset = tools.parents[1] / "Assets/Engines/macos-arm64"
    manifest = json.loads((asset / "Manifest.json").read_text())
    entry = next(item for item in manifest["files"] if item["path"] == "Runtime/Impulse-cross2.pcm")
    bank = (asset / "Library.bin").read_bytes()
    assert data == bank[entry["offset"]:entry["offset"] + entry["size"]], "Packaged 2T must use the calculated response"
    print("Expansion chamber checks passed: travel time, cone polarity, decay and packaged bytes")


if __name__ == "__main__":
    main()
