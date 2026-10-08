# Prepared audio resource gate

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
