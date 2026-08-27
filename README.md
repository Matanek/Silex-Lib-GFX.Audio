# GFX.Audio

GFX.Audio loads reusable sounds and controls playback, repetition, fades,
speed, stereo routing and spatial position. It can be used directly or through
its `GFX.Application` plugin.

```text
silex install GFX.Audio
```

```sx
use GFX.Audio as GFXAudio

func main() {
    var audio = GFXAudio.Audio()
    let sound = audio.load("Assets/Audio/Notification.wav")
    let playing = audio.play(sound, GFXAudio.Playback(volume:0.5))
    audio.wait(playing)
}
```

The package owns its portable Audio API, application plugin, tests, sample
asset and complete SDL3_mixer boundary. Its private `SDL3_mixer`
provider requires the `GFX.SDL3` provider; SDL types and handles never enter the
public API.

GFX.Audio contributes its plugin and resource views to `GFX.Plugins` and
`GFX.Resources`. `Tests/Consumer` is an anonymous application fixture with its
own manifest; it verifies those declarations and the native provider dependency
from outside the package.

See [Docs/README.md](Docs/README.md) for the complete API contract.
The moving spatial-audio application belongs to the central
[Silex-Examples](https://github.com/Matanek/Silex-Examples/blob/main/Sources/SpatialAudio.sx)
catalogue.
