# Inspect a sound and follow playback

`sound_info(sound)` returns a recoverable result containing sample rate,
channels and `Duration`: `frames(count)`, `unknown` or `infinite`.
`duration_seconds()` provides optional seconds for a finite duration. Duration
describes the source without repeats or speed; format is the initial decoded
format. [Timeline.sx](../Timeline.sx) provides a complete example.

`Playback(start_frame:...)` selects an initial source frame between zero and
the known duration, including its end. Subsequent repeats restart at zero.
`seek_frames(playing, frame)` returns a recoverable result; continuous streams
return `unsupported`. A frame contains one sample per channel. Seeking preserves
pause and speed, discards converted mixer output and resets its filter history.
The device may already hold a small block. Codec seeking may be less precise
than seeking fully decoded PCM.

`playback_info(playing)` reports source position in frames, sample rate, playback
and pause. Speed changes rate and pitch; position restarts on repetition. This
is not a speaker clock. Collected or released handles return `invalid_input`
for these recoverable operations.

## Receive an end without blocking

After `play`, call `watch_end(playing)`, then `drain_end_events()` from application
code. Each `EndEvent` retains the original handle and a `finished`, `stopped` or
`released` reason. `event.playback.matches(playing)` compares identity even after
slot reuse. Notifications occur at most once, after mixer output drains or on
release. The first observed terminal reason is retained: stop requested before
release keeps `stopped`; an already observed natural end keeps `finished`.
Unloading a Sound does not stop its playbacks.

Explicit observation avoids accumulating notifications in existing programs.
The queue and reservations together hold at most 256 events. `watch_end` returns
`would_block` at capacity without stopping playback or losing an accepted event.
Draining frees capacity; repeating an accepted request is idempotent. Requesting
after collection fails; requesting before the next collection can observe an
already ended track. The plugin collects resources but retains notifications
until drained. No user callback executes on the audio thread.

[Return to the Audio guide](README.md)

Seconds are a `float` approximation, including for long sources. Frame duration
and frame positions remain the exact units.
