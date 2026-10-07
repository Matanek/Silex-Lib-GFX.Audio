# Produce sound in blocks

A producer supplies `float32` samples as playback progresses, without preparing
the entire sound. It keeps its own timeline; `GFX.Audio` receives its blocks and
plays them in one continuous playback. [StreamingTone.sx](../StreamingTone.sx)
produces a 440 Hz tone in blocks. From `SilexProject/`, run
`silex run Packages/GFX.Audio/Docs/StreamingTone.sx`.

## Open, fill and play

`Audio.stream(sample_rate:int, channels:int = 1, capacity_frames:int = 4_800)`
returns `Result<Stream, STD.Error.Error>`. Rate and channels remain fixed.
Samples follow the same conventions as `Audio.create`: finite values between
-1 and 1, interleaved channels and complete frames. A frame contains one sample
per channel. Rate accepts 1 through 2,147,483,647 Hz, channels 1 through 8;
capacity must be positive and `capacity_frames * channels * 4` must not exceed
2,147,483,647 bytes.

Fragment after creating `audio`, `stream` and the producer:

```sx
var block = producer.next(256)
match audio.write(stream, @block[0:block.count()]) {
    failure(error) => { panic(error.detail) }
    success(frames) => { assert(frames == 256) }
}
block.clear()
let playing = audio.play(stream)
```

Writing before `play` prefills the source. `play` starts the stream once and
returns a `PlayingSound` for the usual controls: volume, master volume,
pause/resume, speed, position, stereo reversal and fades. Repetition is not
applicable; a value other than `once` panics. A stopped stream cannot restart:
open a new source for a new timeline.

## Respect capacity

`write` does not block. Its result reports copied and accepted frames. It may
accept a prefix; keep the remaining frames and submit them on a later call.
For stereo, advance the view by `accepted_frames * 2` samples. A full queue
returns the recoverable `would_block` cause. An empty block accepts zero frames.
Accepted source samples may be changed or released immediately after return.

In an application, inspect `stream_info` and produce according to available
space on each update. In a direct program,
`wait_writable(stream, minimum_frames:int = 1)` explicitly waits without a busy
loop. Keep this wait outside update systems that must keep running. A full
queue before startup or during a pause returns `resource_busy`, instead of
waiting for impossible progress.

Calls on one Audio instance are serialized by the application. Producers and
their processing run there; the audio thread does not invoke Silex callbacks.
Capacity bounds accepted frames not yet logically consumed. Small internal
conversion and output buffers do not form an unlimited queue of blocks.

## Missing data and end of input

When data runs out, playback stays active, contributes silence and resumes with
new blocks. `StreamInfo.starved` describes a started, open, unstopped and
unpaused source whose logical queue is empty. It does not count past gaps or
measure exact silence presented by the device.

`close(stream)` closes input and drains remaining data, including the resampler
filter tail. Closing is idempotent. Further writes fail with `invalid_input`.
Closing before startup is supported; data plays on the first `play`.

`wait(playing)` waits for the logical end of a closed stream. A lack of data on
an open source does not end this wait. `stop(playing)` deliberately ends the
source; an optional fade can finish with available data, even on an empty
source. Unmixed frames are discarded. `release(stream)` or `release(playing)`
frees playback and invalidates both handles; destroying Audio also frees its
streams. A finished stream playback retains resources until `release` or
destruction to preserve output that has already been prepared.

## Read the timeline

`stream_info(stream)` returns `Result<StreamInfo, STD.Error.Error>`, with format,
capacity, counters and the `started`, `closed`, `drained`, `stopped`, `starved`
states. Counters use source frames:

- `written_frames`: accepted frames since opening;
- `consumed_frames`: frames taken by the mixing track;
- `queued_frames`: written frames still waiting for consumption;
- `discarded_frames`: frames discarded after stopping.

The identity `written = consumed + queued + discarded` holds. `drained` means
a closed source was fully consumed and its prepared mixer output drained; an
early stop is represented by `stopped`.
State updates when calling `stream_info`, `is_playing`, `wait` and plugin
collection. This is not an exact speaker clock: the device may still have a
small amount of prepared sound to present.

Stale or foreign handles and malformed data produce recoverable errors on
`Result` operations. Existing playback controls retain their panic convention
for invalid handles.

[Back to the Audio guide](README.md)

## Groups and end events

Stream playback accepts the same `Playback(group:..., volume:...)` and group
controls as a finite sound. Master, group and individual gains multiply. Group
pause preserves frames; individual pause survives group resume or destruction.

Call `watch_end(playing)` after `play(stream)`, then `drain_end_events()` on the
application thread. An open source that runs out of data does not finish.
Closing and draining produces `finished`, deliberate stopping produces
`stopped`, and releasing active playback produces `released`. Each watched
playback produces at most one event. Its reference stays comparable through
`matches` after release without identifying a new playback at the same index.

[End event contracts](Timeline.md) cover bounded capacity and reservation
errors; [groups](Groups.md) cover detachment.

[Evolve a sound and feed a stream](Continuous.md).
