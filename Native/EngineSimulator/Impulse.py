"""Préparer la présence et la durée d'une réponse d'échappement de profil."""
import array
import math
import sys


def prepare(pcm, treble_db=0, tail_ms=0, bass_db=0, mid_decay_ms=0, high_decay_ms=0):
    if treble_db == 0 and tail_ms == 0 and bass_db == 0 and mid_decay_ms == 0 and high_decay_ms == 0:
        return pcm
    values = array.array('h')
    values.frombytes(pcm)
    if sys.byteorder != 'little':
        values.byteswap()
    # RBJ shelves, slope 1. Bake broad body/presence into the chosen impulse.
    def shelf(data, db, hz, high):
        if db == 0:
            return data
        gain = 10 ** (db / 40)
        w = 2 * math.pi * hz / 44100
        c, alpha = math.cos(w), math.sin(w) / math.sqrt(2)
        root = 2 * math.sqrt(gain) * alpha
        if high:
            b = [gain * ((gain + 1) + (gain - 1) * c + root),
                 -2 * gain * ((gain - 1) + (gain + 1) * c),
                 gain * ((gain + 1) + (gain - 1) * c - root)]
            a = [(gain + 1) - (gain - 1) * c + root,
                 2 * ((gain - 1) - (gain + 1) * c),
                 (gain + 1) - (gain - 1) * c - root]
        else:
            b = [gain * ((gain + 1) - (gain - 1) * c + root),
                 2 * gain * ((gain - 1) - (gain + 1) * c),
                 gain * ((gain + 1) - (gain - 1) * c - root)]
            a = [(gain + 1) + (gain - 1) * c + root,
                 -2 * ((gain - 1) + (gain + 1) * c),
                 (gain + 1) + (gain - 1) * c - root]
        x1 = x2 = y1 = y2 = 0.0
        output = []
        for x in data:
            y = (b[0] * x + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2) / a[0]
            x2, x1, y2, y1 = x1, x, y1, y
            output.append(y)
        return output
    filtered = shelf(shelf(values, bass_db, 250, False), treble_db, 2000, True)
    if mid_decay_ms or high_decay_ms:
        # Frequency-dependent absorption: keep the low body, shorten ringing
        # mids/highs. Two-pole split avoids keeping a long bright tail in the body.
        low_alpha = 1 - math.exp(-2 * math.pi * 350 / 44100)
        upper_alpha = 1 - math.exp(-2 * math.pi * 1800 / 44100)
        low1 = low2 = upper1 = upper2 = 0.0
        damped = []
        for i, x in enumerate(filtered):
            low1 += low_alpha * (x - low1)
            low2 += low_alpha * (low1 - low2)
            upper1 += upper_alpha * (x - upper1)
            upper2 += upper_alpha * (upper1 - upper2)
            t_ms = i / 44.1
            mid = math.exp(-t_ms / mid_decay_ms) if mid_decay_ms else 1.0
            high = math.exp(-t_ms / high_decay_ms) if high_decay_ms else 1.0
            damped.append(low2 + mid * (upper2 - low2) + high * (x - upper2))
        filtered = damped
    result = []
    count = len(values) if tail_ms == 0 else min(len(values), round(tail_ms * 44.1))
    for i, y in enumerate(filtered[:count]):
        # Taper only the final quarter; retain the early pressure attack.
        fade = max(0.0, (i / count - 0.75) / 0.25) if tail_ms else 0.0
        result.append(y * (0.5 + 0.5 * math.cos(math.pi * fade)))
    scale = 32760 / max(1.0, max(abs(x) for x in result))
    output = array.array('h', [round(x * scale) for x in result])
    if sys.byteorder != 'little':
        output.byteswap()
    return output.tobytes()
