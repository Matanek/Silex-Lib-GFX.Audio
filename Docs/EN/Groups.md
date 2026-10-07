# Control playback groups

Create categories with `audio.group(volume:0.5)` and pass `group` in
`Audio.Playback`. `set_volume`, `pause`, `resume` and `stop` accept either a group
or a playback. [Complete example](../Groups.sx).

Audible gain is individual gain multiplied by group gain and master gain.
Changing group gain preserves individual settings. New playbacks immediately
inherit the current group gain and pause state. Group commands scan members
only when called; they add no work to each rendered frame.

Individual pause and group pause are independent reasons. `resume(group)` keeps
individually paused members paused. `resume(playing)` keeps members paused while
their group is paused. Commands never restart finished playbacks.

`assign_group(playing, group)` returns `Result<void, Error>`. Pass `null` to detach.
Reassignment preserves individual gain and pause, applies the new gain and
removes the old group pause. Invalid, stale and foreign handles are rejected.

`destroy_group(group)` returns `false` for invalid handles. Surviving members are
detached: individual gain remains and only the group pause is removed.
`contains(group)` checks ownership and generation. `Group.is_valid()` only
indicates a nonempty identity, not current validity.

`stop(group, fade_out_seconds:0.0)` stops current members and keeps group settings
for future playbacks. Watched ends retain their [timeline](Timeline.md) reasons.
Groups have no hierarchy. Continuous PCM streams use the same controls.
