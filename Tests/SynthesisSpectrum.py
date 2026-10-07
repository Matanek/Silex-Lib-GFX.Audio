"""Independent PCM spectral checks; uses only the Python standard library."""
import argparse
import cmath
import math
import os
from pathlib import Path
import subprocess
import tempfile


def fft(values):
    values = list(map(complex, values))
    n = len(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            values[i], values[j] = values[j], values[i]
    width = 2
    while width <= n:
        step = cmath.exp(-2j * math.pi / width)
        for start in range(0, n, width):
            phase = 1
            for offset in range(width // 2):
                a = start + offset
                b = a + width // 2
                value = phase * values[b]
                values[b] = values[a] - value
                values[a] += value
                phase *= step
        width *= 2
    return values


def ideal(shape, phase, duty):
    if shape == 'triangle':
        return 4 * abs((phase - .25) % 1 - .5) - 1
    if shape == 'sawtooth':
        return 0 if phase == 0 else 2 * phase - 1
    if phase in (0, duty):
        return 0
    return 1 if phase < duty else -1


def power(samples):
    width = 8192
    bins = [0.0] * (width // 2 + 1)
    window = [.5 - .5 * math.cos(2 * math.pi * i / (width - 1)) for i in range(width)]
    for start in range(0, len(samples), width):
        spectrum = fft([x * w for x, w in zip(samples[start:start + width], window)])
        for i in range(len(bins)):
            bins[i] += abs(spectrum[i]) ** 2
    return bins


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--debug", action="store_true")
options = parser.parse_args()

owner = Path(__file__).resolve().parents[1]
workspace = owner.parents[1]
compiler = os.environ.get('SILEX_EXECUTABLE', str(workspace / 'Silex/Toolchain/zig-out/bin/silex'))
cases = []
for shape in ('triangle', 'square', 'sawtooth'):
    for frequency in (375, 3000, 9000):
        for duty in ((.25, .5, .75) if shape == 'square' else (.5,)):
            cases.append((shape, frequency, duty, 4096))
for shape in ('white', 'pink'):
    cases.append((shape, 0, .5, 131072))
for shape in ('am', 'fm'):
    cases.append((shape, 3000, .5, 4096))
source = '''use GFX.Audio.Synthesis
use GFX.Audio.Processing
func dump(source:Synthesis.Generator, count:int) {
    var samples:float32[] = []
    var i = 0
    while i < count { samples.append(0.0); i++ }
    match source.render(&samples[0:count]) { failure(error) => { panic(error.detail) }; success => {} }
    for sample in samples { print(sample) }
}
func main() {
    let format = Processing.Format(sample_rate:48_000, channels:1)
'''
for shape, frequency, duty, count in cases:
    if shape in ('am', 'fm'):
        source += '    match Synthesis.Oscillator.create(format, frequency_hz:375.0) { failure(error) => { panic(error.detail) }; success(var control) => {\n'
        if shape == 'am':
            source += '        match Synthesis.Oscillator.create(format, frequency_hz:3000.0) { failure(error) => { panic(error.detail) }; success(var carrier) => {\n'
            source += '            match Synthesis.AmplitudeModulation.create(carrier, control) { failure(error) => { panic(error.detail) }; success(value) => { dump(value, 4096) } }\n        } }\n'
        else:
            source += '        match Synthesis.FrequencyModulation.create(format, control, frequency_hz:3000.0, deviation_hz:750.0, phase:0.125) { failure(error) => { panic(error.detail) }; success(value) => { dump(value, 4096) } }\n'
        source += '    } }\n'
        continue
    if shape in ('white', 'pink'):
        expression = f'Synthesis.{"WhiteNoise" if shape == "white" else "PinkNoise"}.create(format, seed:42)'
    else:
        expression = f'Synthesis.Oscillator.create(format, frequency_hz:{frequency}.0, waveform:Synthesis.Waveform.{shape}, duty_cycle:{duty})'
    source += f'    match {expression} {{ failure(error) => {{ panic(error.detail) }}; success(value) => {{ dump(value, {count}) }} }}\n'
source += '}\n'
with tempfile.TemporaryDirectory(prefix='SynthesisSpectrum_', dir=owner / 'Tests') as temporary:
    entry = Path(temporary) / 'Spectrum.sx'
    entry.write_text(source)
    artifact = Path(temporary) / 'spectrum'
    subprocess.run([compiler, 'compile', str(entry), '--nocache', '-o', str(artifact)] + (['--debug'] if options.debug else ['--release']), cwd=workspace, check=True, timeout=90)
    environment = dict(os.environ, SDL_AUDIODRIVER='__silex_no_audio_driver__')
    result = subprocess.run([str(artifact)], cwd=workspace, env=environment, capture_output=True, text=True, check=True, timeout=60)
values = list(map(float, result.stdout.splitlines()))
assert len(values) == sum(case[3] for case in cases)
position = 0
noise = {}
references = {}
for shape, frequency, duty, count in cases:
    samples = values[position:position + count]
    position += count
    assert all(math.isfinite(x) and abs(x) <= 1 for x in samples)
    if shape in ('white', 'pink'):
        noise[shape] = samples
        continue
    spectrum = fft(samples)
    if shape == 'am':
        allowed = {224, 256, 288}
        expected = {224: .125, 256: -.25j, 288: -.125}
        total = sum(abs(x) ** 2 for x in spectrum[:count // 2 + 1])
        unwanted = sum(abs(x) ** 2 for k, x in enumerate(spectrum[:count // 2 + 1]) if k not in allowed)
        assert unwanted / total < 1e-7
        for k, value in expected.items():
            assert abs(spectrum[k] / count - value) < 2e-5, (k, spectrum[k] / count, value)
        print(f'ok - AM analytical carrier and sidebands, unwanted power {unwanted / total:.3g}')
        continue
    if shape == 'fm':
        # Closed-form discrete sine sum: independent of the render phase loop.
        omega = 2 * math.pi * 375 / 48000
        reference = [math.sin(2 * math.pi * (.125 + 3000 * n / 48000 + 750 / 48000 *
                     math.sin(n * omega / 2) * math.sin((n - 1) * omega / 2) / math.sin(omega / 2)))
                     for n in range(count)]
        rms_error = math.sqrt(sum((a - b) ** 2 for a, b in zip(samples, reference)) / count)
        assert rms_error < 4e-5, rms_error
        expected = fft(reference)
        assert max(abs(a - b) / count for a, b in zip(spectrum, expected)) < 2e-5
        total = sum(abs(x) ** 2 for x in spectrum[:count // 2 + 1])
        high = sum(abs(x) ** 2 for x in spectrum[768:count // 2 + 1]) / total
        assert high < 1e-7, high
        assert abs(spectrum[224]) / count > .1 and abs(spectrum[288]) / count > .1
        print(f'ok - FM closed-form phase and sidebands, RMS error {rms_error:.3g}, power above 9 kHz {high:.3g}')
        continue
    fundamental = frequency * count // 48000
    harmonics = min(64, (24000 - 1) // frequency)
    allowed = {0} | {k * fundamental for k in range(1, harmonics + 1)}
    total = sum(abs(x) ** 2 for x in spectrum[:count // 2 + 1])
    unwanted = sum(abs(x) ** 2 for k, x in enumerate(spectrum[:count // 2 + 1]) if k not in allowed)
    assert unwanted / total < 1e-7, (shape, frequency, duty, unwanted / total)
    key = (shape, duty)
    if key not in references:
        size = 65536
        references[key] = fft([ideal(shape, i / size, duty) for i in range(size)])
    reference = references[key]
    # Reference from dense integration of the ideal time-domain shape, not DSP coefficients.
    for k in range(0, harmonics + 1):
        expected = reference[k] / 65536 * (1 - k / (harmonics + 1)) * .99999
        actual = spectrum[k * fundamental] / count
        assert abs(actual - expected) < 2e-5, (shape, frequency, duty, k, actual, expected)
    print(f'ok - {shape} {frequency} Hz duty={duty}: reference and out-of-band ratio {unwanted / total:.3g}')
# Demonstrate that the anti-alias oracle discriminates a naive discontinuous saw.
naive = [2 * ((i * 9000 / 48000) % 1) - 1 for i in range(4096)]
spectrum = fft(naive)
allowed = {0, 768, 1536}
ratio = sum(abs(x) ** 2 for k, x in enumerate(spectrum[:2049]) if k not in allowed) / sum(abs(x) ** 2 for x in spectrum[:2049])
assert ratio > .01
bands = (187.5, 375, 750, 1500, 3000, 6000)
energies = {}
for shape, samples in noise.items():
    bins = power(samples)
    octave = [sum(bins[math.ceil(low * 8192 / 48000):math.ceil(high * 8192 / 48000)]) for low, high in zip(bands, bands[1:])]
    energies[shape] = octave
    density = [energy / (high - low) for energy, low, high in zip(octave, bands, bands[1:])]
    slope = sum((i - 2) * math.log2(value) for i, value in enumerate(density)) / 10
    print(f'{shape}: octave power ratios {[round(x / octave[0], 3) for x in octave]}, PSD slope {slope:.3f}')
    if shape == 'pink':
        assert max(octave) / min(octave) < 2.5, octave
        assert -1.2 < slope < -.8, slope
    else:
        assert -.2 < slope < .2, slope
assert energies['white'][-1] / energies['white'][0] > 8
print('ok - stationary spectra: pink has approximately constant octave power; white has flat density')
