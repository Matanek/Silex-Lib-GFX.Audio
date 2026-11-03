#!/usr/bin/env python3
"""Vérifier bypass, déterminisme et absorption par bande des réponses préparées."""
import array
import cmath
import math
import sys
import Impulse


def pcm(values):
    result = array.array('h', [round(x * 24000) for x in values])
    if sys.byteorder != 'little':
        result.byteswap()
    return result.tobytes()


def decode(data):
    values = array.array('h'); values.frombytes(data)
    if sys.byteorder != 'little':
        values.byteswap()
    return values


def amplitude(values, frequency, start_ms):
    start, count = round(start_ms * 44.1), round(8 * 44.1)
    return abs(sum(values[start + i] * cmath.exp(-2j * math.pi * frequency * i / 44100)
        for i in range(count))) / count


def main():
    values = [0.55 * math.sin(2 * math.pi * 125 * i / 44100)
        + 0.2 * math.sin(2 * math.pi * 1000 * i / 44100)
        + 0.2 * math.sin(2 * math.pi * 4000 * i / 44100) for i in range(4096)]
    original = pcm(values)
    assert Impulse.prepare(original) == original, 'Bypass exact'
    legacy = Impulse.prepare(original, treble_db=7, tail_ms=45)
    assert legacy == Impulse.prepare(original, treble_db=7, tail_ms=45, mid_decay_ms=0, high_decay_ms=0), 'Recettes existantes conservées'
    processed = Impulse.prepare(original, mid_decay_ms=24, high_decay_ms=14)
    assert processed == Impulse.prepare(original, mid_decay_ms=24, high_decay_ms=14), 'Répétabilité'
    output = decode(processed)
    assert len(output) == len(values) and max(abs(x) for x in output) <= 32760, 'Longueur et marge PCM16'
    ratios = {f: amplitude(output, f, 32) / amplitude(output, f, 0) for f in [125,1000,4000]}
    assert ratios[125] > 0.7, 'Corps grave conservé dans la queue'
    assert ratios[1000] < 0.7 and ratios[4000] < 0.5, 'Résonances médium/aigu absorbées plus vite'
    print('Impulse checks passed: bypass, existing recipes, repeat, bounds, low/mid/high tail ratios', ratios)


if __name__ == '__main__':
    main()
