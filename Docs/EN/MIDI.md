# Play a MIDI score with your own instruments

`GFX.Audio.MIDI` reads a score and controls the application's procedural
instruments. [MIDIMelody.sx](../MIDIMelody.sx) plays two tracks at 120 then
150 BPM, with program change, stereo balance, expression, sustain and an echo
tail. It smooths volume, expression and balance changes over 240 frames
(5 ms at 48 kHz) to avoid level steps. The `.mid` fixture contains events, no sound
bank. From `SilexProject/`:

```sh
silex run Packages/GFX.Audio/Docs/MIDIMelody.sx --release
```

The main path is `Score.parse` or `Score.read`, explicit `Binding` choices,
then `Synthesizer.create` and `Player.create`. Player is a
`Synthesis.Generator`: compose it with effects and the
[stream producer](Continuous.md), or render it into a memory buffer.

## Choose sounds and channels

Fragment with a `score:MIDI.Score` read at 48 kHz and a prepared stereo
`lead:Synthesis.Instrument` at the same rate:

```sx
match MIDI.Synthesizer.create([
    MIDI.Binding(channel:0, program:0, instrument:lead),
], gain:0.25, controller_ramp_frames:240) {
    failure(error) => { panic(error.detail) }
    success(var synth) => {
        match MIDI.Player.create(score, synth) {
            failure(error) => { panic(error.detail) }
            success(var player) => { require(player.render(&samples[0:samples.count()])) }
        }
    }
}
```

The fragment also assumes a stereo `samples` buffer and a
`require(Result<void, Error>)` helper. The complete example includes preparation.
Channels 0..15 and programs 0..127 use protocol values; a channel often displayed
as “1” therefore has value 0. Each channel starts with program 0. Program
selection controls future notes; earlier notes, releases and sustain remain in
their original instrument. Selecting a missing channel/program pair, or sending it a note-on, returns
`unsupported`, without an implicit sound. There is no special percussion-channel handling or
General MIDI mapping.

`Synthesizer.create(bindings, note_capacity:256, bend_range:2, gain:0.2,
controller_ramp_frames:0)` accepts
1..128 distinct bindings, a pool of 1..4,096 held notes, ±0..24 semitones and a
finite gain in 0..1. All instruments must share the same stereo format with an
integer rate in 1..16,777,216 Hz. Use an independent instance per binding;
references to the same class would share voices and controls. Classes share
state with the application; structs copy into the protocol value. Global gain
remains explicit: the sum is not normalized and the application keeps headroom
for Audio output.

## Send messages directly

`send(channel, Message)` returns `true` for a translated message and `false`
for ignored pressure or controllers. Out-of-range values return `invalid_input`
before mutation. A valid message may still be rejected by an instrument,
including for capacity or an unsupported frequency.

| Message | Interpretation |
|---|---|
| `note_on(note, velocity)` | Note 0..127, A4=440 Hz at note69, velocity divided by127; zero becomes note-off |
| `note_off(note, velocity)` | Releases the oldest still-held note of the same channel/pitch; release velocity is validated but ignored |
| `program_change(program)` | Selects an existing binding for future notes |
| `pitch_bend(value)` | 14-bit value 0..16383, center8192; `(value−8192)/8192 * bend_range` semitones |
| `control_change(7, value)` | 7-bit channel volume, initially127 |
| `control_change(11, value)` | 7-bit expression, initially127, multiplied by volume |
| `control_change(10, value)` | Linear balance:0 left,64 center,127 right; only attenuates the opposite channel |
| `control_change(64, value)` | Sustain:0..63 released,64..127 pressed |
| `control_change(123, value)` | Note-off for all keys on the channel, respecting sustain |
| `control_change(120, value)` | Immediately cuts channel instruments through reset, then reapplies channel bend/sustain |

Volume, expression and balance apply after each instrument renders and also
apply to voices from an earlier program. Bend and sustain reach all bindings
on the channel. To avoid a click when changing levels while voices remain
audible, choose `controller_ramp_frames:240` (5 ms at 48 kHz). This duration,
bounded to 0..16,777,216 frames, linearly smooths the stereo gains resulting from
CC7, CC11 and CC10. Zero preserves immediate changes and remains the default.
The first frame keeps the current level; the target is reached after the chosen
duration. A new target starts from the current level, including during a ramp.
All programs on a channel share this progression, advanced once per frame;
reset restores initial levels and cancels ramps. Events keep their exact date:
this smoothing adds no humanization or delay to notes, and no ramp to bend,
sustain or the immediate CC120 cut.
High-resolution gain/balance LSBs are ignored, along with CC0/32
bank select, CC121 reset controllers, RPN/NRPN, modulation and other controllers.
`poly_pressure` and `channel_pressure` are validated then ignored.

Repeated notes have distinct identities and explicit FIFO pairing. The held-note
pool is independent of the instrument's voice pool; stealing a voice does not
remove a still-held MIDI key. An unmatched note-off succeeds without effect.
`held_notes()` counts keys. `finish()` removes sustain and releases all voices
without cutting their tails. `reset()` cuts and restores programs0,
volume/expression127, balance/bend0, pedal released and the initial identity
counter. Commands spanning instruments propagate the first rejection; earlier
instruments may have accepted. There is no implicit rollback of user instruments:
reset/rebuild after an error before replay.

## Read and bound a score

`Score.parse(bytes:@uint8[..], sample_rate, maximum_bytes:1_048_576,
maximum_tracks:64, maximum_events:65_536)` does not retain the input view.
`Score.read(path, sample_rate, ...)` reads bytes through STD.File then uses the
same parser; file errors remain STD.File errors. Prepare outside rendering.
Configurable bounds:14..16,777,216 bytes,1..256 tracks,1..65,536 events.
Every event, including ignored metadata or SysEx, counts before storage;
chunk and payload lengths are checked before reading.

Formats0/1, PPQN division1..32767, channel statuses and running status are
supported. Tracks must finish with end-of-track and declared/actual counts must
match. Format1 tempo outside the first track is rejected. Format2 and SMPTE
division return `unsupported`; truncated data, VLQs longer than four bytes,
invalid lengths and incompatible structure return `invalid_input`, capacity/clock
overflow returns `limit_exceeded`. Unknown chunks are skipped by length;
extended headers are accepted. Unknown metadata and F0/F7 SysEx are skipped
by length and counted in `ignored_events`. Recognized metadata extensions are
skipped after known fields. Meta/SysEx cancel running status. Unrendered pressure
and controllers remain inspectable in `events`.

Score exposes `sample_rate`, `ppqn`, `track_count`, `events`, `end_frame` and
`ignored_events`. Events carry `frame`, `channel`, `message`. Merge orders by
tick, track index, then order within the track; events rounded to the same frame
retain musical order. Default tempo is 500,000 µs per quarter note (120 BPM).
The clock accumulates frame fractions exactly with integers; each absolute
position rounds to nearest, half-frames forward, without adding per-event/block
rounding errors. Frames must fit int64, including after rounding; rejection is
recoverable.

## Render events and tails

`Player.create(score, synth)` requires matching rates. It starts at frame0
without implicitly resetting the synthesizer; use fresh instruments or reset
before replay. Rendering splits at events; `rendered_frames()` gives the produced
position and `ignored_messages()` counts encountered unrendered messages.
An empty block triggers nothing. An event at block end waits for the next
nonempty block. At `end_frame`, after the final events, Player calls finish once.
It then continues rendering releases; add the chosen tail duration to
StreamProducer. `reset()` restores instruments, position and ignored-message count.

A rejection retains the failed event position without consuming it; the prefix
and earlier commands may already have applied. A user rendering error may alter
state and output before rejection. Render source, instruments and producer on
one thread with exclusive ownership of their timeline. Hardware ports, native
Silex callbacks, SDL's MIDI decoder, VST hosting and automatic sound-bank loading
are outside this path.

[Proof](Validation.md) covers timing, formats, controllers, identities, tails,
errors, bounds and memory/stream equality. Parser and routing remain written in
Silex; listening complements audible qualification.

File rules follow [MIDI Association RP-001](https://midi.org/standard-midi-files-specification),
with [channel messages](https://midi.org/expanded-midi-1-0-messages-list) and
[MIDI1.0 controllers](https://midi.org/midi-1-0-control-change-messages).
