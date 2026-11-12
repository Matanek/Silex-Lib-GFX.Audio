# Choose capacities and a production budget

Prepare instruments, effects and buffers before computing blocks. Events use
an integer frame clock; computation throughput and stream filling determine
the available production headroom. Score tempo stays independent of the
application update rate.

## Prepare, then render

`SineInstrument.create(max_voices:16)` prepares 1 to 64 voices per instrument.
At full capacity, `voice_policy` rejects the note or replaces the oldest voice,
with a configurable transition. A `Processed` chain accepts up to 32 processors.
Delay capacities and reverb size are prepared at creation; their histories persist
between blocks. Changes that rebuild an effect or source belong outside block
computation.

`Sequence` retains up to its chosen capacity of 1 to 65,536 events. `schedule`
can grow its collection: call it outside rendering. Rendering consumes prepared
events without copying them. MIDI also prepares its score and note registers
before playback: up to 128 bindings and 1 to 4,096 retained note identities,
chosen by the application. File, track and event limits are explicit in the
[MIDI guide](MIDI.md).

Pass a mutable view of an owned, prepared buffer to `render`/`process`.
The sine instrument and modulations compute in internal chunks of at most 512
frames; a larger call performs more work. Application memory-rendering helpers
and `Audio.render` instead produce a new owned array. User effects and instruments
remain responsible for their own allocations, durations, levels and errors.

## Computation and PCM transfer

The macOS ARM64 test counter detected **zero allocations** during the first
block, 100 successive blocks, valid commands and reset for the four workloads
below, in Debug and Release. An isolated oscillator, a `Sequence` with notes
inside blocks and a `MIDI.Player` through end/release also pass this check.
An empty phase and a growing array validate the counter. No libc copy calls
are detected in these phases; inline stores or copies are not counted.

This result covers the marked application thread, not SDL threads. The counter
does not cover Silex X64 allocations through direct syscalls; its positive control
fails there. It therefore provides no zero-allocation proof on X64, Linux or
Windows. See the [reproducible test](../../Tests/Resources/README.md).

`Audio.write` packs samples into a temporary native buffer, then SDL manages
its queue. A partial write of 127 stereo frames requests 1,016 bytes for this
buffer; queue refills may add allocations. `StreamProducer.pump` includes this
transfer: **it is not allocation-free**. Call it on the application thread, with
explicit prefill and capacity. Stream capacity and the Silex buffer bound retained
frames; these measurements do not certify SDL's memory details or delays.

## Measured workload

Measured October 8, 2026, Apple M3 Pro (12 cores, 18 GB), macOS 26.6.2,
Release, 48 kHz stereo. Sine voices at `110 + 13 × id` Hz, velocity `0.25 / N`,
default ADSR; 8 kHz low-pass, chorus (960 ± 240 frames, 0.7 Hz, feedback 0.1,
wet 0.25), reverb (size 0.5, 1.5 s, damping 0.5, wet 0.3), default compressor
and −3 dB limiter.

Seven repetitions per workload, 64 warmup blocks followed by 1,000 measured
blocks, rotating workload order. Allocation interception is disabled. Time includes
microsecond-resolution clock reads; storing measurements, numerical checks and
printing happen outside the interval. PCM transfer, SDL, the device and application
scheduling are not measured.

| Voices / frames | Block budget | Native ARM64: median / p95 / max | X64 under Rosetta: median / p95 / max |
|---|---:|---:|---:|
| 16 / 128 | 2,667 µs | 156 / 161 / 236 µs | 348 / 357 / 977 µs |
| 16 / 512 | 10,667 µs | 607 / 620 / 1,367 µs | 1,362 / 1,383 / 1,625 µs |
| 64 / 128 | 2,667 µs | 339 / 346 / 374 µs | 827 / 837 / 1,004 µs |
| 64 / 512 | 10,667 µs | 1,307 / 1,335 / 1,544 µs | 3,207 / 3,229 / 9,027 µs |

Repetition medians range respectively from 155–159, 605–607, 338–340 and
1,302–1,321 µs on ARM64; from 348–352, 1,360–1,364, 827–828 and 3,205–3,210 µs
under Rosetta. The 16-voice workload takes about 6% of the budget at the median
on ARM64; 64 voices take about 12–13%. Under Rosetta these shares rise to 13%
and 30–31%, with an 85% peak at 64 voices/512 frames. That peak leaves little
headroom for a busy application. Rosetta does not represent native Intel or AMD
processor performance.

Preparation requests between 778,048 and 803,920 cumulative bytes from the ARM64
allocator for these workloads. This total includes creation and buffer growth,
not only final sizes; it is not peak resident memory. Physical Silex allocation
can exceed `frames × channels × 4`.

Measured DSP sources are Audio `ada2c3570df1ffa3ac7065a11ab9892abff40af7`, compiled
with Silex `cfc682ca4018081063fef25a6f429868f3dbb655`. Reconciliation with Silex `60d90abf1d7a689eef421b54fb9bd58b09d2313e`
reproduces both timed binaries exactly. Durations are neither a
fixed-threshold pass/fail test nor hard real-time certification. Qualify your
application workload on its machine, with its instruments, effects, commands
and transfer headroom.

[Evolve a sound and feed a stream](Continuous.md) ·
[Validate audio paths](Validation.md)

[Choose musical playback costs](MusicResources.md).
