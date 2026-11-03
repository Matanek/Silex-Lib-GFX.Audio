# Prepared audio resource gate

The procedural engine has a focused macOS ARM64 gate:

```sh
python3 Packages/GFX.Audio/Tests/Resources/ValidateEngine.py
```

It checks an empty phase and a positive allocation control, then preparation,
the first block, 1,000 render/control updates and reset in Debug and Release.
It writes `.silex/engine-resource-validation.json`. The marked scope is prepared
engine DSP on the application thread; PCM transfer, SDL and UI are excluded.

From the SilexProject root, or the owning Spec Worktree group:

```sh
python3 Packages/GFX.Audio/Tests/Resources/Validate.py
```

This private consumer requires macOS ARM64, Clang and the active local Silex
toolchain. It uses the workspace package links. `SILEX_EXECUTABLE` may select
another compiler. It writes binaries, logs and `audio-resource-validation.json`
under the shared `.silex` directory. The fixture's System boundary and the C
interposer are test instrumentation; neither is an installed audio provider.

The empty phase and a growing Silex array validate the allocation counter.
Debug and Release then check a prepared oscillator, 16/64 sine voices with five
effects at 128/512 stereo frames, valid commands, scheduled events, a MIDI file
including end/release, and reset. Assertions also check levels, clocks and silence.
No timing threshold belongs to this deterministic gate.

The phase marker is `getppid`. Interposed malloc/calloc/realloc/mmap and
memcpy/memmove count only the marked thread, using atomic owner/enable state.
Bookkeeping does not allocate. Thread-local bookkeeping would recurse during
TLS initialization in allocator hooks. Inline stores/copies and other threads
are outside the counter; this is not a measurement of resident memory.

PCM writes are measured separately, with a partial first write and 100 drains
outside the measured regions. Copies provide a positive copy control. Allocations
in this transfer are reported, not concealed behind the DSP gate: `Audio.write`
packs native float32 samples, and SDL manages its queue. Thus `StreamProducer.pump`
is not allocation-free. Offline `Audio.render` also returns an owned array.

macOS X64 uses direct mmap syscalls for Silex heap allocation; its growing-array
control is invisible to libc interposition. The validator refuses that host rather
than treating zero counts as evidence. Linux/Windows need their own valid counter.
See the [resource qualification](../../Docs/EN/Resources.md) for measured scope.

## Musical authoring and managed playback

```sh
python3 Packages/GFX.Audio/Tests/Resources/GenerateMusicFixture.py
python3 Packages/GFX.Audio/Tests/Resources/ValidateMusic.py
```

The first command checks or generates the 157-byte, three-hour SMF fixture:
16 held notes and 32 note commands. The second qualifies preparation, 100
prepared play/stop pairs, eight overlapping plays, MIDI parsing, player creation,
prefill, controls, stop/replay and 100 managed-feed/offline blocks in Debug and
Release. A counted application instrument proves that replaying a prepared sound
does not synthesize it again. Public-path allocations are reported separately
from 100 allocation-free instrument DSP blocks.

For the private retro recipe, the script creates a disposable package copy with
mechanical markers around valid command application, block rendering and reset.
A test-only System provider supplies the phase marker. No production source or
provider is changed. The workspace Audio link temporarily points to this copy;
do not run another Audio-dependent compilation concurrently. A `finally` restores
the original owner even on failure; the script verifies restored links and source
bytes. Each mode covers at least 100 recipe blocks and 16 valid commands.

`music-resource-validation.json` retains phases, source and binary hashes.
Controls, finite levels and the queue-plus-block production bound are assertions;
no timing threshold is used. Allocation and copy controls have the same ARM64
limits as the advanced gate above. See [musical resource costs](../../Docs/EN/MusicResources.md).

## Piano

`ValidatePiano.py` exerce le piano en Debug et Release macOS ARM64 avec témoins
d’allocation et copie : 16/64 voix stéréo, blocs 128/512, frappes, rendu,
vols de voix, contrôles, pédale et reset. Le compteur du thread appelant ne
mesure ni une latence maximale, ni le transfert PCM natif du player.
Depuis la racine workspace : `python3 Packages/GFX.Audio/Tests/Resources/ValidatePiano.py`.

## Engine-part assemblies

Run `python3 Packages/GFX.Audio/Tests/Resources/ValidateEngineAssembly.py` from
the workspace or Spec group root. The macOS ARM64 counter checks Debug/Release
first-block rendering, 1,000 blocks with state/mix changes, prepared part
crossfades and reset. Empty/growing-array controls must succeed. Preparation and
part replacement are separately counted as allocating operations. Output and
binary identities are retained in `.silex/engine-assembly-resource-validation.json`.
Audio device, streaming transfer, UI and other threads are excluded.

## Engine workshop reserve witness

On macOS, from the workspace or owning Spec group, compile the private fixture
and run it with SDL's silent driver:

```sh
silex compile Packages/GFX.Audio/Tests/Resources/EngineStreamReserve.sx --release -o Build/EngineStreamReserve
SDL_AUDIO_DRIVER=dummy Build/EngineStreamReserve
```

It deliberately leaves 45 ms between refills. A 1,440-frame reserve at 48 kHz
must exhibit empty-queue observations; the 4,800-frame reserve must not. Run on
an otherwise available host: OS scheduling stalls longer than 100 ms invalidate
that second condition. This witness exercises the real device-consumption path
without speakers; it does not certify uninterrupted playback under arbitrary
load or count historical native underruns. The fixture's `usleep` boundary is
macOS-only test instrumentation, never part of the installed package.
