#include "CaptureTap.h"
#include <stdatomic.h>
#include <limits.h>
#include <stddef.h>

#if ATOMIC_LLONG_LOCK_FREE != 2 || ATOMIC_LONG_LOCK_FREE != 2 || ATOMIC_INT_LOCK_FREE != 2
#error Audio capture requires always-lock-free native counters on its target.
#endif

/* One native producer and one consumer. No Silex code, allocation, IO or
   waiting runs from the post-mix callback. Overflow latches a failed capture;
   playback and the production clock continue, with no hole concealed as PCM. */
typedef struct CaptureTap {
    MIX_Mixer *mixer;
    SDL_AudioSpec spec;
    float *samples;
    uint64_t capacity;
    uint64_t start_ns;
    _Atomic uint64_t first_ns;
    _Atomic uint64_t stop_ns;
    _Atomic uint64_t peak;
    _Atomic uint64_t max_block;
    _Atomic uint64_t written;
    _Atomic uint64_t read;
    _Atomic uint64_t produced;
    _Atomic uint64_t dropped;
    _Atomic int error;
    _Atomic int running;
} CaptureTap;

static const char *capture_property = "Silex.GFX.Audio.capture";

static void SDLCALL CapturePostMix(void *userdata, MIX_Mixer *mixer,
                                  const SDL_AudioSpec *spec, float *pcm, int samples)
{
    CaptureTap *tap = userdata;
    (void)mixer;
    if (!atomic_load_explicit(&tap->running, memory_order_relaxed)) return;
    if (samples < 0 || spec->channels != tap->spec.channels ||
        spec->freq != tap->spec.freq || spec->format != SDL_AUDIO_F32 ||
        samples % tap->spec.channels != 0) {
        if (atomic_load_explicit(&tap->error, memory_order_relaxed) == 0) atomic_store_explicit(&tap->error, 2, memory_order_release);
        return;
    }
    const uint64_t frames = (uint64_t)samples / (uint64_t)tap->spec.channels;
    const uint64_t total = atomic_load_explicit(&tap->produced, memory_order_relaxed);
    if (frames > INT64_MAX - total) {
        if (atomic_load_explicit(&tap->error, memory_order_relaxed) == 0) atomic_store_explicit(&tap->error, 3, memory_order_release);
        return;
    }
    if (total == 0 && frames != 0) atomic_store_explicit(&tap->first_ns, SDL_GetTicksNS(), memory_order_relaxed);
    if (frames > atomic_load_explicit(&tap->max_block, memory_order_relaxed)) atomic_store_explicit(&tap->max_block, frames, memory_order_relaxed);
    // Publish production metadata before readable PCM. A consumer acquiring
    // written must never observe more consumed frames than produced frames.
    atomic_store_explicit(&tap->produced, total + frames, memory_order_release);
    const uint64_t written = atomic_load_explicit(&tap->written, memory_order_relaxed);
    const uint64_t read = atomic_load_explicit(&tap->read, memory_order_acquire);
    if (atomic_load_explicit(&tap->error, memory_order_relaxed) != 0 ||
        frames > tap->capacity - (written - read)) {
        if (atomic_load_explicit(&tap->error, memory_order_relaxed) == 0) atomic_store_explicit(&tap->error, 1, memory_order_release);
        const uint64_t dropped = atomic_load_explicit(&tap->dropped, memory_order_relaxed);
        atomic_store_explicit(&tap->dropped, dropped + frames, memory_order_release);
    } else if (frames != 0) {
        const size_t stride = (size_t)tap->spec.channels * sizeof(float);
        const uint64_t offset = written % tap->capacity;
        const uint64_t first = SDL_min(frames, tap->capacity - offset);
        SDL_memcpy(tap->samples + offset * tap->spec.channels, pcm, (size_t)first * stride);
        if (first < frames) SDL_memcpy(tap->samples, pcm + first * tap->spec.channels, (size_t)(frames - first) * stride);
        const uint64_t pending = written + frames - read;
        if (pending > atomic_load_explicit(&tap->peak, memory_order_relaxed)) atomic_store_explicit(&tap->peak, pending, memory_order_relaxed);
        atomic_store_explicit(&tap->written, written + frames, memory_order_release);
    }
}

void *Silex_MIX_CaptureCreate(MIX_Mixer *mixer, uint64_t capacity_frames)
{
    SDL_AudioSpec spec;
    if (!mixer || !capacity_frames || !MIX_GetMixerFormat(mixer, &spec) ||
        spec.channels < 1 || spec.channels > 8 || spec.freq < 1 ||
        capacity_frames > SIZE_MAX / sizeof(float) / (size_t)spec.channels) {
        SDL_SetError("Invalid output capture format or capacity");
        return NULL;
    }
    CaptureTap *tap = SDL_calloc(1, sizeof(*tap));
    if (!tap) return NULL;
    tap->samples = SDL_malloc((size_t)capacity_frames * (size_t)spec.channels * sizeof(float));
    if (!tap->samples) { SDL_free(tap); return NULL; }
    // Commit the payload pages before publishing the observer to the audio thread.
    SDL_memset(tap->samples, 0, (size_t)capacity_frames * (size_t)spec.channels * sizeof(float));
    tap->mixer = mixer;
    tap->spec = spec;
    tap->spec.format = SDL_AUDIO_F32;
    tap->capacity = capacity_frames;
    atomic_init(&tap->first_ns, 0);
    atomic_init(&tap->stop_ns, 0);
    atomic_init(&tap->peak, 0);
    atomic_init(&tap->max_block, 0);
    atomic_init(&tap->written, 0);
    atomic_init(&tap->read, 0);
    atomic_init(&tap->produced, 0);
    atomic_init(&tap->dropped, 0);
    atomic_init(&tap->error, 0);
    atomic_init(&tap->running, 1);
    MIX_LockMixer(mixer);
    const SDL_PropertiesID properties = MIX_GetMixerProperties(mixer);
    bool installed = properties != 0 && SDL_GetPointerProperty(properties, capture_property, NULL) == NULL;
    if (installed) installed = SDL_SetPointerProperty(properties, capture_property, tap);
    if (installed) {
        tap->start_ns = SDL_GetTicksNS();
        installed = MIX_SetPostMixCallback(mixer, CapturePostMix, tap);
        if (!installed) SDL_ClearProperty(properties, capture_property);
    } else SDL_SetError("Mixer already has an output capture, or its properties are unavailable");
    MIX_UnlockMixer(mixer);
    if (!installed) { SDL_free(tap->samples); SDL_free(tap); return NULL; }
    return tap;
}

void Silex_MIX_CaptureStop(void *capture)
{
    CaptureTap *tap = capture;
    if (!tap) return;
    MIX_LockMixer(tap->mixer);
    if (atomic_load_explicit(&tap->running, memory_order_relaxed)) {
        atomic_store_explicit(&tap->running, 0, memory_order_release);
        MIX_SetPostMixCallback(tap->mixer, NULL, NULL);
        atomic_store_explicit(&tap->stop_ns, SDL_GetTicksNS(), memory_order_release);
        SDL_ClearProperty(MIX_GetMixerProperties(tap->mixer), capture_property);
    }
    MIX_UnlockMixer(tap->mixer);
}

void Silex_MIX_CaptureDestroy(void *capture)
{
    CaptureTap *tap = capture;
    if (!tap) return;
    Silex_MIX_CaptureStop(tap);
    SDL_free(tap->samples);
    SDL_free(tap);
}

int Silex_MIX_CaptureRead(void *capture, float *output, int frames)
{
    CaptureTap *tap = capture;
    if (!tap || frames < 0 || (frames != 0 && !output)) return -1;
    const uint64_t read = atomic_load_explicit(&tap->read, memory_order_relaxed);
    const uint64_t written = atomic_load_explicit(&tap->written, memory_order_acquire);
    const uint64_t count = SDL_min((uint64_t)frames, written - read);
    if (count) {
        const size_t stride = (size_t)tap->spec.channels * sizeof(float);
        const uint64_t offset = read % tap->capacity;
        const uint64_t first = SDL_min(count, tap->capacity - offset);
        SDL_memcpy(output, tap->samples + offset * tap->spec.channels, (size_t)first * stride);
        if (first < count) SDL_memcpy(output + first * tap->spec.channels, tap->samples, (size_t)(count - first) * stride);
        atomic_store_explicit(&tap->read, read + count, memory_order_release);
    }
    return (int)count;
}

uint64_t Silex_MIX_CaptureProduced(void *capture) { return atomic_load_explicit(&((CaptureTap *)capture)->produced, memory_order_acquire); }
uint64_t Silex_MIX_CaptureReadFrames(void *capture) { return atomic_load_explicit(&((CaptureTap *)capture)->read, memory_order_acquire); }
uint64_t Silex_MIX_CaptureAvailable(void *capture)
{
    CaptureTap *tap = capture;
    /* Observational snapshot; allocation and consumption use CaptureRead. */
    const uint64_t read = atomic_load_explicit(&tap->read, memory_order_acquire);
    const uint64_t written = atomic_load_explicit(&tap->written, memory_order_acquire);
    return written < read ? 0 : SDL_min(written - read, tap->capacity);
}
uint64_t Silex_MIX_CaptureDropped(void *capture) { return atomic_load_explicit(&((CaptureTap *)capture)->dropped, memory_order_acquire); }
int Silex_MIX_CaptureError(void *capture) { return atomic_load_explicit(&((CaptureTap *)capture)->error, memory_order_acquire); }
int Silex_MIX_CaptureSampleRate(void *capture) { return ((CaptureTap *)capture)->spec.freq; }
int Silex_MIX_CaptureChannels(void *capture) { return ((CaptureTap *)capture)->spec.channels; }

uint64_t Silex_MIX_CaptureFirstOffsetNS(void *capture)
{
    CaptureTap *tap = capture;
    if (atomic_load_explicit(&tap->written, memory_order_acquire) == 0) return 0;
    const uint64_t first = atomic_load_explicit(&tap->first_ns, memory_order_relaxed);
    return first >= tap->start_ns ? first - tap->start_ns : 0;
}
uint64_t Silex_MIX_CaptureElapsedNS(void *capture)
{
    CaptureTap *tap = capture;
    uint64_t now = atomic_load_explicit(&tap->stop_ns, memory_order_acquire);
    if (!now) now = SDL_GetTicksNS();
    return now >= tap->start_ns ? now - tap->start_ns : 0;
}
uint64_t Silex_MIX_CaptureCapacity(void *capture) { return ((CaptureTap *)capture)->capacity; }
uint64_t Silex_MIX_CapturePeak(void *capture) { return atomic_load_explicit(&((CaptureTap *)capture)->peak, memory_order_acquire); }
uint64_t Silex_MIX_CaptureMaxBlock(void *capture) { return atomic_load_explicit(&((CaptureTap *)capture)->max_block, memory_order_acquire); }
int Silex_MIX_CaptureRunning(void *capture) { return atomic_load_explicit(&((CaptureTap *)capture)->running, memory_order_acquire); }

int Silex_MIX_CaptureActive(MIX_Mixer *mixer)
{
    if (!mixer) return 0;
    MIX_LockMixer(mixer);
    const SDL_PropertiesID properties = MIX_GetMixerProperties(mixer);
    const int active = properties && SDL_GetPointerProperty(properties, capture_property, NULL) != NULL;
    MIX_UnlockMixer(mixer);
    return active;
}
