# Play sounds with GFX.Audio

`GFX.Audio` loads reusable sounds or creates them from samples, and controls
every audible playback without exposing SDL devices, mixers, tracks, channel
maps, or native sample formats. The
package works directly or through its `GFX.Application` plugin.

[Lire cette documentation en français.](../FR/README.md)

## Install the package

```text
silex install GFX.Audio
```

GFX.Audio requires Silex 0.44.0 or newer.

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

## Load from memory and handle a failure

`Audio.try_decode(bytes:@uint8[..])` decodes encoded bytes, such as an embedded
WAV. `Audio.try_load(path:str)` loads a file. Both operations return
`Result<Sound, STD.Error.Error>`; `load(path)` retains its panic on failure.

The [complete program](../MemorySound.sx) loads a WAV without a temporary file:

```sx
use GFX.Audio

func main() {
    var audio = Audio()
    let bytes = embed_bytes("../../Assets/Audio/SpatialTone.wav")
    match audio.try_decode(@bytes[0:bytes.count()]) {
        failure(error) => { panic(error.detail) }
        success(sound) => { audio.wait(audio.play(sound)) }
    }
}
```

Full decoding owns its result: source bytes may be changed or released as soon
as the call returns. Empty, truncated or unrecognized bytes produce
`invalid_data`. File opening failures retain the `other` cause currently
provided by STD.File and the provider message; they do not claim to distinguish
missing files from denied access. The error also provides `operation`
(`audio.load` or `audio.decode`) and the file path in `subject`. A failure does
not prevent subsequent loads.

`Sound` and `PlayingSound` handles belong to their Audio instance. Another
instance cannot unload them or control its own playbacks with them. Stale handles
remain rejected after slot reuse or destruction of their owner.

## Create a sound from samples

`Audio.create(samples:@float32[..], sample_rate:int, channels:int = 1)` creates
a reusable `Sound` from a sample view. No file is needed. This program produces
a 440 Hz A tone for a quarter of a second:

```sx
use GFX.Audio
use STD.Math

func main() {
    var samples:float32[] = []
    var frame = 0
    while frame < 12_000 {
        let time = frame as float / 48_000.0
        samples.append((0.1 * Math.sin(2.0 * Math.pi() * 440.0 * time)) as float32)
        frame++
    }

    var audio = Audio()
    let sound = audio.create(@samples[0:samples.count()], sample_rate:48_000)
    samples.clear()
    let playing = audio.play(sound)
    audio.wait(playing)
    assert(audio.unload(sound))
}
```

The [runnable source](../GeneratedTone.sx) contains this program. From
`SilexProject/`, run `silex run Packages/GFX.Audio/Docs/GeneratedTone.sx`.

Each sample must be finite and between `-1.0` and `1.0`; zero represents
silence. `sample_rate` is the number of audio frames per second and must be
between 1 and 2,147,483,647. `channels` defaults to 1 (mono) and accepts 1 to 8
channels. Channels are interleaved: stereo values follow left, right, left,
right order. The buffer must contain at least one complete frame and its
size must be a multiple of `channels`. Invalid input causes a `panic`.

`create` copies the values before returning. The source array can therefore
be changed or released immediately. Sound duration is
`samples.count() / channels / sample_rate` seconds. Like a loaded sound,
it supports simultaneous playbacks and every playback control; `unload`
invalidates its handle without interrupting playbacks that retain it.
Creation consumes a complete buffer and does not provide continuous streaming.

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
