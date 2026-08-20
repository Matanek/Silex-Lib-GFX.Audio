# Play game audio

`GFX.Audio` loads reusable sounds and controls each audible playback without
exposing SDL devices, mixers, tracks, channel maps, or sample formats. Install
`GFX.Audio.Plugin` to make the Audio resource available from `startup` until
`shutdown`.

```sx
use GFX.Audio as GFXAudio
use GFX.Application
use STD.Math

func start(audio:&GFXAudio.Audio) {
    let explosion = audio.load("Assets/Audio/Explosion.wav")
    let playing = audio.play(explosion, GFXAudio.Playback(
        volume:0.8,
        repeat:GFXAudio.Repeat.once(),
        position:Math.Vec3(4.0, 1.0, -2.0)
    ))
}

func main() {
    Application()
        ..add_plugin(GFXAudio.Plugin())
        ..add_system(Application.Schedule.startup, start)
        ..run()
}
```

`Audio.load` decodes the complete file and returns a stable `Audio.Sound`
handle. A sound may feed several simultaneous playbacks. `Audio.unload`
invalidates the handle; playbacks already holding that sound may finish safely
because the native mixer retains their input.

The distributed artifacts enable WAV, AIFF, AU, VOC, FLAC, MP3, and Ogg Vorbis
decoding. Support for a format is a property of the artifact, not something
inferred from a filename extension.

## Control one playback

`Audio.play` returns an `Audio.PlayingSound` handle. It identifies that audible
instance rather than the reusable sound:

```sx
audio.set_volume(playing, 0.4)
audio.set_speed(playing, 1.1)
audio.pause(playing)
audio.resume(playing)
audio.stop(playing, fade_out_seconds:0.25)
```

For a direct program without an application loop, `wait` blocks efficiently
until that playback finishes:

```sx
var audio = GFXAudio.Audio()
let sound = audio.load("Assets/Audio/Notification.wav")
let playing = audio.play(sound)
audio.wait(playing)
```

`wait` also remains blocked while the playback is paused. The completed
playback is collected before the call returns.

Volume is a non-negative linear gain. `0.0` is silent and `1.0` preserves the
source level; values above one amplify and can clip or become dangerously loud.
Speed accepts values from `0.01` through `100.0`. It changes playback rate and
pitch together.

Repeat describes total audible plays rather than SDL's extra-loop count:

- `GFXAudio.Repeat.once()` plays once;
- `GFXAudio.Repeat.times(3)` plays three times in total;
- `GFXAudio.Repeat.forever()` repeats until stopped.

`fade_in_seconds` belongs to the initial `GFXAudio.Playback` request. `stop`
accepts a fade-out duration. A released or automatically collected playback
handle becomes stale and cannot control a later playback that reuses its slot.
`release` is an immediate discard operation; calling it during a fade stops the
fade by destroying that playback.

## Place a sound around the listener

Pass a position when playback starts or change it while the sound is active:

```sx
let playing = audio.play(ambience, GFXAudio.Playback(
    repeat:GFXAudio.Repeat.forever(),
    position:Math.Vec3(-3.0, 0.0, -1.0)
))

audio.set_position(playing, Math.Vec3(3.0, 0.0, -1.0))
audio.clear_position(playing)
```

Positions are listener-relative in a right-handed coordinate system: negative
X is left, positive X is right, positive Y is up, and negative Z is forward.
SDL_mixer keeps its listener at the origin. An application with a world-space
camera or character must therefore subtract the listener position and rotate
the result into listener-local coordinates before calling `set_position`.

Spatial playback provides speaker placement and distance attenuation. It does
not currently promise HRTF headphone rendering, Doppler, a configurable
distance model, or configurable rolloff. `clear_position` returns the playback
to ordinary channel mixing.

`set_reverse_stereo` swaps the left and right output channels while preserving
additional surround channels. It does not play samples backwards.

## Lifetime and availability

The plugin opens the default playback device during `startup`, on the main
thread. Device or decoder failures are reported with a `GFX.Audio` diagnostic.
It collects naturally completed playbacks after updates and closes every
remaining playback and sound during `shutdown`.

Applications without a presenting renderer should add
`GFX.Application.FramePacing`. This prevents an unconstrained application loop from
continually contending with the audio callback while changing playback state.

Pinned, checksummed SDL3_mixer artifacts are distributed for `macos-arm64`,
`linux-x64`, `windows-x64`, and `windows-arm64`.
