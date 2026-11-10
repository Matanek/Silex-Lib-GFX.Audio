# GFX.Audio

`GFX.Audio` loads reusable sounds, generates procedural tones and noise with
ADSR envelopes, or creates sounds from samples, and controls
playback, repetition, fades, speed, stereo routing, and spatial position,
directly or through GFX.Application.

```text
silex install GFX.Audio
```

## Documentation

- [French documentation](Docs/FR/README.md)
- [English documentation](Docs/EN/README.md)

The package requires Silex 0.48.0 or newer.

[Create retro textures with bitcrushing and sample hold](Docs/EN/Bitcrusher.md).

Play polyphonic notes with [instruments and a frame timeline](Docs/EN/Instruments.md): ADSR, sustain, pitch bend and a composable generator without sound banks.

Play [MIDI scores with application-selected procedural instruments](Docs/EN/MIDI.md), without sound banks.

[Prepare and replay short melodies with customizable timbres or an integrated
instrument](Docs/EN/Music.md), without handling PCM buffers. `Music.Instruments.sine`
configures the polyphonic sine instrument with durations in seconds; application
instruments keep their own musical settings and the existing extension protocol.

[Play a MIDI score and pause, resume, stop or replay it](Docs/EN/MusicPlayer.md). The player owns bounded audio feeding in an application or a standalone program.

[Choose preparation and continuous playback costs](Docs/EN/MusicResources.md), with measured scope and resource limits.

[Play a procedural piano](Docs/EN/Piano.md) with `Music.Instruments.piano`, strike dynamics, natural decay and sustain pedal.

[Play procedural guitar, violin and drums](Docs/EN/Catalogue.md), with named percussion keys and family-specific settings.

[Reuse the validated engine-bench sounds](Docs/EN/Engines.md) through
`GFX.Audio.Engines`: package-owned simulation, profiles, exhaust responses,
intake and output processing. `Library.open()` supplies the standard engines on
macOS ARM64; an external native library is optional.

[Create vehicle variants with the reference sound chain](Docs/EN/Vehicles.md)
through `Engines.Vehicles`, preserving the Chevrolet 454 reference and preparing
17 additional thermal-engine profiles. The vehicle workshop uses this path.
City petrol profiles add quiet exterior rendering; diesel combines the simulator
with a sampled acoustic voice from a TDI reference, identified as hybrid.

The [parts synthesizer](Docs/EN/EngineParts.md), including
`Synthesis.EngineVehicles`, remains a separate experimental prototype.
