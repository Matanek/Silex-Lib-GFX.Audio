# Observe the mix during playback

`audio.capture_output()` observes this Audio instance’s final device mix,
after its gain and processing. Playback continues. It captures neither a
microphone, speakers, system audio nor another application.

The public consumer is [OutputCapture.sx](../../Tests/Consumer/Smokes/OutputCapture.sx).
After creating `Audio`, call `capture_output(capacity_frames:96_000)`, then
`read_f32le(max_frames:4096)` on the returned `OutputCapture`. Both return a
`Result` with ordinary STD errors. `Audio.offline` uses `render`/`render_f32le`;
device capture is rejected for offline mixers.

## Blocks and timing

Each `CaptureBlock` owns its bytes; subsequent reads do not change them.
`bytes` contains interleaved IEEE float32 in little-endian order. `frames`
counts channel groups, not individual floating-point values. `output_format()`
gives the sample rate and channel count. The mix is copied without additional
normalization or channel conversion.

`first_frame` locates the block in the capture timeline. The delay before the
first block is converted to frames with cumulative flooring; subsequent blocks
advance by their integer frame counts. This origin is not the physical time
of speaker output. An empty block means no data is available; reads never wait
for new data.

The statistics’ `elapsed_seconds` and `first_frame_seconds` use double precision.
The monotonic period clock and sample counter are distinct. A driver or device
that does not progress at its advertised rate does not establish synchronization
with video. Sample counters advance in blocks, not as interpolated video clocks.

## Resources and concurrency

The `capacity_frames` buffer is allocated and touched before capture starts.
The default 96,000 frames occupy 768,000 bytes for stereo PCM, or two seconds
at 48 kHz. Returned blocks and application sounds require additional memory.
Only one capture may be active per mixer; another request fails with
`resource_busy`. Independent mixers keep independent captures.

Exactly one consumer may call `read_f32le`. It may run on a worker while the
application controls playback. The native observer copies samples and publishes
atomic counters. No Silex code, encoding, file IO, allocation or waiting runs
in this observer on the audio thread. The mixer retains its own costs. With
capture inactive, there is no observation buffer or additional observation work.

`statistics()` reports capacity, pending and peak frames, produced/read/dropped
frames, largest block, times and states. Queue snapshots are observations, not
reservations; the read determines its actual result. Queue counts stay bounded.
A block that does not fit fails capture without blocking playback. This failure
is persistent: reads return `resource_exhausted`, never presenting a discontinuous
stream as complete. Format changes and exhausted counters are also reported.

`stop()` detaches capture and freezes its duration. Remaining captured blocks
can still be read. It is idempotent and does not stop sounds. Detachment
synchronizes with the mixer: call it from the owner or a worker, never from
its own audio callback. Destroying an old stopped handle does not detach a new
capture. The handle retains Audio until destruction, including after `stop`,
to keep the mixer alive during draining and cleanup.

## Primitive limits

This primitive creates neither videos nor files and does not choose an
application’s slow-reader policy. The encoder or video recorder must handle
failure, any boundary silence and the relationship between clocks. Capacity is
not a universal frame-rate or zero-cost promise. Dummy-driver tests qualify
functionality; temporal synchronization is qualified separately on a real
device and decoded artifacts.
