# Choose musical playback costs

Prepare a short sound during loading, then reuse its handle when the event occurs.
For a long score, `Music.Player` produces the blocks playback needs. Both paths
accept a timbre or an instrument; storage and startup costs differ.

| Use | Preparation | Triggering and progression |
| --- | --- | --- |
| Victory or notification | `Melody.prepare` computes the complete sound and gives it to Audio | `Audio.play` creates an independent playback without synthesizing it again |
| MIDI score | Parse events and prepare the player, voices and effects | `play` prefills the queue; Audio continues production according to consumption |

`play` still allocates. Preparing a sound avoids recomputation; it does not
eliminate creating a playback in the mixer. In a game, the Audio plugin feeds
players on the application thread. `wait` suits a standalone program and
deliberately blocks that thread.

## Long-score storage

Initial player settings are a 4,800-frame queue and a 512-frame block. At 48 kHz
and speed 1, the queue represents 100 ms. Scratch holds one block; production
progress is bounded by consumption plus the queue and one block. Score metadata,
voices and effect memories are separate from this PCM bound. A larger score
contains more metadata; duration alone does not require prerendering the song.

Qualification uses a three-hour score with 16 held notes, 32 commands and 157 MIDI
bytes. It checks bounded prefill and progression without computing three hours
of PCM. Other oracles cover ending, tails, replay, simultaneous events and partial
writes.

The game must progress the plugin regularly. Adapt queue size to its cadence,
audio rate and speed; a small queue can starve the converter. Observe
`is_starved`, player state and errors.

## Measured allocations

The macOS ARM64 counter passes empty, allocation and copy controls in Debug and
Release. Prepared block computation for the sine instrument with five effects
and the retro recipe performs no observed libc allocation or copy in covered
phases. Valid recipe commands and reset are also checked. The [advanced gate](Resources.md)
separately covers the foundation's instruments, effects, events and reset.

Native transfer packs samples and SDL manages its queue. Offline rendering
returns an owned array. These paths allocate even when prepared DSP does not.
Here are Release observations in cumulative bytes requested from the allocator,
using `MusicHeap.sx` at 48 kHz stereo:

| Phase | Allocations | Cumulative bytes |
| --- | ---: | ---: |
| Prepare the four-note retro sound | 106 | 1,408,419 |
| 100 prepared plays, each followed by a stop | 4,405 | 371,284 |
| Eight overlapping plays, including a handle collection | 441 | 1,180,216 |
| Parse the three-hour MIDI | 17 | 14,208 |
| Prepare sine instrument + five effects + player | 541 | 1,058,794 |
| Prepare retro recipe + player, without effects | 653 | 307,810 |
| Start/prefill, each of the two players | 106 | 1,423,523 |
| 100 managed feeds and offline outputs, instrument + effects | 1,809 | 15,789,352 |
| 100 managed feeds and offline outputs, recipe without effects | 1,807 | 15,772,968 |
| Instrument replay after stopping | 155 | 1,641,285 |

Pause/resume and stop request zero observed allocations in these phases.
Repeated plays include their stops here; the eight-handle collection is included
in the overlap phase. Cumulative bytes include buffer growth and temporaries:
they represent neither resident memory nor peak memory. Inline copies and other
threads are outside coverage. The x64 allocation control is invisible to this
interposer; no allocation-free verdict is inferred for that target.

## Durations and headroom

Release, Apple M3 Pro, macOS 26.6.2. Each workload holds 16 low notes
(48..63, velocity 32/127), amplitude 0.025 and five effects: 8 kHz low-pass,
960±240-frame chorus at 0.7 Hz, feedback 0.1, wet 0.25; reverb
size 0.5, decay 1.5 s, damping 0.5, wet 0.3; initial compressor and −3 dB limiter.
Seven repetitions in rotating order, 64 warmup blocks then 1,000 blocks per
repetition. The table measures complete managed-feed/offline rendering, including
native transfer and output allocation; DSP alone is separated below.

| Target | Realization | Frames | Median (ms) | p95 (ms) | Max (ms) |
| --- | --- | ---: | ---: | ---: | ---: |
| ARM64 | Sine + 5 FX | 128 | 2.633 | 4.922 | 5.568 |
| ARM64 | Sine + 5 FX | 512 | 5.152 | 8.029 | 9.838 |
| ARM64 | Retro + 5 FX | 128 | 10.443 | 13.514 | 17.655 |
| ARM64 | Retro + 5 FX | 512 | 34.330 | 38.768 | 68.048 |
| x64/Rosetta | Sine + 5 FX | 128 | 5.080 | 8.172 | 638.870 |
| x64/Rosetta | Sine + 5 FX | 512 | 11.920 | 15.129 | 147.115 |
| x64/Rosetta | Retro + 5 FX | 128 | 20.999 | 24.679 | 41.839 |
| x64/Rosetta | Retro + 5 FX | 512 | 68.577 | 76.315 | 112.216 |

At 48 kHz the budget is 2.667 ms for 128 frames and 10.667 ms for 512.
On ARM64, sine/512 uses 48% of the budget at median, 75% at p95 and
92% at maximum. Sine/128 exceeds the budget at p95; the dense retro workload
already exceeds it at median. These workloads do not automatically qualify a
loaded game. Reduce polyphony or choose a less costly realization, then measure
the game's path on its machine.

Sine DSP with five effects, measured inside the instrument, takes on ARM64
0.748/1.649/2.329 ms (median/p95/max, 128 frames) and
3.309/5.797/6.856 ms (512). Under Rosetta:
1.919/3.704/66.141 ms (128) and 8.248/11.843/145.138 ms (512).
This includes the probe's clock reads. Retro-recipe DSP time is not isolated
in this timing campaign.

Preparing the short sound takes a median of 94.493 ms on ARM64 and 183.562 ms
under Rosetta (seven observations). Prepared play, excluding stop, takes
median/p95/max 24/30/172 µs on ARM64 and 15/56/215 µs under Rosetta
(700 observations). Repeated plays measured for allocations also include stops;
these two metrics therefore have different boundaries.

Repetition medians range from 2.369 to 2.867 ms for ARM64 sine/128,
and from 3.659 to 5.612 ms under Rosetta; retro/512 ranges from 33.547 to
34.900 ms and from 64.514 to 71.349 ms. Rosetta shows drift and a 639 ms peak:
no stationary estimate or positive headroom is inferred from it. It does not
represent native Intel/AMD processor performance. No task-owned compilation
accompanies timing, but other host activities are not isolated. Level checks
and observation collection stay outside the interval. Offline timing measures
neither the device nor a game's scheduling. No fragile timing threshold or hard
real-time certification is added.


## Reproduce and adapt

From the workspace root or the Spec Worktree group root:

```sh
python3 Packages/GFX.Audio/Tests/Resources/ValidateMusic.py
```

The gate requires macOS ARM64 and Clang. It creates a temporary package copy to
instrument the private recipe and restores the workspace link in `finally`.
Do not run another Audio-dependent compilation during this gate. The owner and
its provider remain intact. See the [fixture instructions](../../Tests/Resources/README.md).

Measured production sources are those of Audio
`d1ce09a0b9887d58ce3a89ea584a34b3d0dc57c2`, using Silex
`b8b81e996181b138283f6186360efe22d5845335`. Qualification additions do not
change these sources. All six targets are qualified separately through linking;
allocations and durations above do not prove resource behavior on Linux or Windows.

[Prepare a melody](Music.md) · [Control MIDI playback](MusicPlayer.md) ·
[Verify audio paths](Validation.md)
