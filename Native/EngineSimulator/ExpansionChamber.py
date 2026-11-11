"""Calculate the acoustic impulse of a two-stroke pipe from its section profile."""
import array
import math
import sys

RATE = 44_100


def diameters(stations, cell_mm):
    """Sample piecewise conical sections on a one-sample travel grid."""
    result = []
    for (start, inlet), (end, outlet) in zip(stations, stations[1:]):
        if not all(map(math.isfinite, (start, end, inlet, outlet))):
            raise ValueError("Pipe stations must be finite")
        first, last = round(start / cell_mm), round(end / cell_mm)
        if first >= last or inlet <= 0 or outlet <= 0:
            raise ValueError("Pipe sections require positive diameters and resolved lengths")
        count = last - first
        result.extend(inlet + (outlet - inlet) * (i + .5) / count for i in range(count))
    return result


def outlet_filter(radius_m, sound_speed):
    # Silva et al., arXiv:0811.3625, Table 1, causal unflanged approximation.
    # Bilinear transform with s = 2*RATE*(1-z^-1)/(1+z^-1).
    ka = 2 * RATE * radius_m / sound_speed
    inertia = 1.393 * ka
    curvature = .457 * ka * ka
    numerator = (-(1 + .167 * ka), -2., -(1 - .167 * ka))
    denominator = (1 + inertia + curvature, 2 - 2 * curvature, 1 - inertia + curvature)
    return tuple(value / denominator[0] for value in numerator + denominator[1:])


def response(stations_mm, speed_m_s, loss_per_m, frames):
    if (len(stations_mm) < 2 or stations_mm[0][0] != 0
            or not math.isfinite(speed_m_s) or not math.isfinite(loss_per_m)
            or speed_m_s <= 0 or loss_per_m < 0 or frames < 1):
        raise ValueError("Expected a pipe starting at zero, positive wave speed and passive losses")
    cell_m = speed_m_s / RATE
    pipe = diameters(stations_mm, cell_m * 1000)
    if frames <= len(pipe):
        raise ValueError("Response ends before a wave can reach the outlet")
    # Root-power waves make each junction lossless. Z is proportional to
    # 1/area, so a widening gives a negative pressure reflection.
    junctions = [
        ((left * left - right * right) / (left * left + right * right),
         2 * left * right / (left * left + right * right))
        for left, right in zip(pipe, pipe[1:])
    ]
    loss = math.exp(-loss_per_m * cell_m)
    forward = [0.] * len(pipe)
    backward = [0.] * len(pipe)
    forward[0] = 1.
    b0, b1, b2, a1, a2 = outlet_filter(stations_mm[-1][1] / 2000, speed_m_s)
    x1 = x2 = y1 = y2 = 0.
    inlet, outlet = [], []
    for _ in range(frames):
        incident = forward[-1]
        reflected = b0 * incident + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x1, x2 = incident, x1
        y1, y2 = reflected, y1
        inlet.append(backward[0])
        outlet.append(incident + reflected)

        # A matched inlet absorbs the returning wave. The calculated outlet
        # response feeds the audio renderer; it does not feed cylinder flow.
        next_forward = [0.] * len(pipe)
        next_backward = [0.] * len(pipe)
        next_backward[-1] = loss * reflected
        for i, (r, t) in enumerate(junctions):
            incoming_left, incoming_right = forward[i], backward[i + 1]
            next_backward[i] = loss * (r * incoming_left + t * incoming_right)
            next_forward[i + 1] = loss * (t * incoming_left - r * incoming_right)
        forward, backward = next_forward, next_backward
    return inlet, outlet


def prepare(geometry):
    frames = round(geometry["response_ms"] * RATE / 1000)
    _, signal = response(geometry["stations_mm"], geometry["speed_m_s"], geometry["loss_per_m"], frames)
    # Truncate only the tail of the calculated response before PCM16 transport.
    taper = frames // 4
    for i in range(taper if taper > 1 else 0):
        signal[frames - taper + i] *= .5 + .5 * math.cos(math.pi * i / (taper - 1))
    scale = 32760 / max(map(abs, signal))
    result = array.array("h", (round(value * scale) for value in signal))
    if sys.byteorder != "little":
        result.byteswap()
    return result.tobytes()
