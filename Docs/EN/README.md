# Play sounds with GFX.Audio

`GFX.Audio` loads reusable sounds and controls every audible playback without
exposing SDL devices, mixers, tracks, channel maps, or sample formats. The
package works directly or through its `GFX.Application` plugin.

[Lire cette documentation en français.](../FR/README.md)

## Install the package

```text
silex install GFX.Audio
```

GFX.Audio requires Silex 0.39.0 or newer.

## Play a sound in an application

Install `GFX.Audio.Plugin` to make the Audio resource available from `startup`
until `shutdown`:

```sx
use GFX.Audio as GFXAudio
use GFX.Application
use STD.Math

func start(audio:&GFXAudio.Audio) {
    let explosion = audio.load("Assets/Audio/Explosion.wav")
    let playing = audio.play(explosion, GFXAudio.Playback(
        volume:0.8,
        repeat:GFXAudio.Repeat.once(),
        position:Math.Vec3(4.0, 1.0, -2.0),
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
handle. A sound can feed several simultaneous playbacks. `Audio.unload`
invalidates the handle, but playbacks that already retain it can finish.

Distributed artifacts decode WAV, AIFF, AU, VOC, FLAC, MP3, and Ogg Vorbis.
Support belongs to the artifact and is not inferred from a file extension.

## Control one playback

`Audio.play` returns an `Audio.PlayingSound` that identifies one audible
instance, not the reusable sound:

```sx
audio.set_volume(playing, 0.4)
audio.set_speed(playing, 1.1)
audio.pause(playing)
audio.resume(playing)
audio.stop(playing, fade_out_seconds:0.25)
```

In a direct program without an Application loop, `wait` blocks efficiently
until playback finishes, including while it is paused.

Volume is a non-negative linear gain. `1.0` preserves the source level; higher
values can clip or become dangerously loud. Speed ranges from `0.01` through
`100.0` and changes rate and pitch together.

`Repeat.once()` plays once, `Repeat.times(3)` three times in total, and
`Repeat.forever()` until stopped. `fade_in_seconds` belongs to the initial
request; `stop` accepts a fade-out duration. A released or collected handle
cannot control a later playback that reuses its slot.

## Position a sound

A position can be supplied at startup and then changed:

```sx
let playing = audio.play(ambience, GFXAudio.Playback(
    repeat:GFXAudio.Repeat.forever(),
    position:Math.Vec3(-3.0, 0.0, -1.0),
))

audio.set_position(playing, Math.Vec3(3.0, 0.0, -1.0))
audio.clear_position(playing)
```

Positions are listener-relative in a right-handed coordinate system: negative
X is left, positive X is right, positive Y is up, and negative Z is forward.
A world-space application must subtract the listener position and rotate the
result into listener-local coordinates.

Spatial playback provides speaker placement and distance attenuation. It does
not yet promise HRTF, Doppler, a configurable distance model, or configurable
rolloff. `set_reverse_stereo` swaps left and right channels; it does not play
samples backward.

## Understand lifetime and artifacts

The plugin opens the default output device during `startup` on the main thread,
collects completed playbacks, and closes remaining playbacks and sounds during
`shutdown`. An application without a presenting renderer should add
`GFX.Application.FramePacing`.

The package owns its private SDL3_mixer provider, which requires `GFX.SDL3`.
SDL handles never cross the API. Pinned, checksummed artifacts exist for macOS
ARM64, Linux x64, Windows x64, and Windows ARM64; the latter remains a
recognized experimental target in the Silex matrix.

The [SpatialAudio](https://github.com/Matanek/Silex-Examples/blob/main/Sources/SpatialAudio.sx)
demonstration belongs to Silex-Examples.
