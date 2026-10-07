# Render a mix in memory

`Audio.offline(sample_rate:48_000, channels:2)` returns `Result<Audio, Error>`
without opening a device or initializing an audio driver. Use the same Audio
to load/create sounds, create groups, play and control sources, then call
`render(frames:1024)`. [Standalone example](../Offline.sx).

`render` returns `Result<float32[], Error>` with exactly the requested number
of frames, interleaved using the chosen channel count. Every frame is valid;
frames after sources end contain silence. Zero returns an empty array.
Negative requests, buffers exceeding 2,147,483,647 native bytes, or requests
exceeding the frame counter are rejected before rendering. A device Audio
returns `unsupported`.

Arrays own their storage and survive Audio destruction. Rendering applies no
normalization or clipping; a mix may exceed ±1. Explicitly attenuate before
passing it to `create` or `write`, which accept inputs within ±1. Audible output
retains its provider saturation behavior; both paths match for controlled levels.

Successive calls retain playback and conversion state. `rendered_frames()`
counts output frames, including silence; it stays zero on a device Audio.
Playback positions and start/seek frames use the source format, distinct from
this output timeline. To delay a new source, render the desired prefix, then
play it before rendering the next block. Even infinite repeats produce only
the requested frames. Watched ends are collected after each render. Dry streams
produce silence and can receive more samples later.

`wait` cannot advance offline playback and reports a runtime error if progress
is still needed. Explicitly render blocks until completion. `wait_writable`
returns `resource_busy` for full offline streams requiring a render. No thread
or Application loop is needed. One application owner must call operations
sequentially.

With identical format and commands, one large block or successive blocks
preserve PCM within absolute 10⁻⁶ for qualified unit-level fixtures. Changing
controls between blocks defines a different sequence; spatial transitions can
depend on block size.
