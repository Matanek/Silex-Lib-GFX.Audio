#ifdef ARCHIVE_PROBE
#include "../CaptureTap.h"
#else
#include "../CaptureTap.c"
#endif
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#define CHECK(expression) do { if (!(expression)) { fprintf(stderr, "line %d: %s (%s)\n", __LINE__, #expression, SDL_GetError()); exit(1); } } while (0)

#ifndef ARCHIVE_PROBE
static void ring_test(void)
{
    CaptureTap tap = {0};
    tap.spec = (SDL_AudioSpec){ SDL_AUDIO_F32, 2, 48000 };
    tap.capacity = 193;
    tap.samples = SDL_calloc(193 * 2, sizeof(float));
    CHECK(tap.samples);
    atomic_init(&tap.written, 0); atomic_init(&tap.read, 0);
    atomic_init(&tap.produced, 0); atomic_init(&tap.dropped, 0);
    atomic_init(&tap.error, 0); atomic_init(&tap.running, 1);
    atomic_init(&tap.first_ns, 0); atomic_init(&tap.stop_ns, 0);
    atomic_init(&tap.peak, 0); atomic_init(&tap.max_block, 0);
    float input[388], output[386];
    for (int i = 0; i < 100; ++i) { input[i*2] = (float)i; input[i*2+1] = -(float)i; }
    CapturePostMix(&tap, NULL, &tap.spec, input, 200);
    CHECK(Silex_MIX_CaptureRead(&tap, output, 37) == 37);
    for (int i = 0; i < 37; ++i) { CHECK(output[i*2] == (float)i); CHECK(output[i*2+1] == -(float)i); }
    for (int i = 0; i < 120; ++i) { input[i*2] = (float)(100+i); input[i*2+1] = -(float)(100+i); }
    CapturePostMix(&tap, NULL, &tap.spec, input, 240);
    CHECK(Silex_MIX_CaptureAvailable(&tap) == 183);
    CHECK(Silex_MIX_CapturePeak(&tap) == 183);
    CHECK(Silex_MIX_CaptureMaxBlock(&tap) == 120);
    CHECK(Silex_MIX_CaptureRead(&tap, output, 193) == 183);
    for (int i = 0; i < 183; ++i) { CHECK(output[i*2] == (float)(37+i)); CHECK(output[i*2+1] == -(float)(37+i)); }
    CHECK(Silex_MIX_CaptureRead(&tap, NULL, 0) == 0);
    CHECK(Silex_MIX_CaptureRead(&tap, output, 1) == 0);
    CapturePostMix(&tap, NULL, &tap.spec, input, 388);
    CHECK(Silex_MIX_CaptureError(&tap) == 1);
    CHECK(Silex_MIX_CaptureDropped(&tap) == 194);
    CapturePostMix(&tap, NULL, &tap.spec, input, 2);
    CHECK(Silex_MIX_CaptureProduced(&tap) == 415);
    CHECK(Silex_MIX_CaptureDropped(&tap) == 195);
    CHECK(Silex_MIX_CaptureAvailable(&tap) == 0);
    SDL_free(tap.samples);
    puts("{\"case\":\"ring-wrap-overflow\",\"frames_read\":220,\"produced\":415,\"dropped\":195,\"capacity\":193}");
}

#endif

static void offline_test(void)
{
    SDL_AudioSpec spec = { SDL_AUDIO_F32, 2, 48000 };
    MIX_Mixer *mixer = MIX_CreateMixer(&spec);
    CHECK(mixer);
    float input[16384];
    for (int i = 0; i < 8192; ++i) { input[i*2] = (float)(i % 251) / 251.0f; input[i*2+1] = -input[i*2]; }
    MIX_Audio *audio = MIX_LoadRawAudio(mixer, input, sizeof(input), &spec);
    MIX_Track *track = MIX_CreateTrack(mixer);
    CHECK(audio && track && MIX_SetTrackAudio(track, audio));
    CHECK(MIX_SetMixerGain(mixer, 0.5f));
    CHECK(MIX_PlayTrack(track, 0));
    void *capture = Silex_MIX_CaptureCreate(mixer, 32768);
    CHECK(capture);
    CHECK(Silex_MIX_CaptureActive(mixer));
    CHECK(!Silex_MIX_CaptureCreate(mixer, 32768));
    SDL_ClearError();
    float generated[8192], captured[65536];
    CHECK(MIX_Generate(mixer, generated, sizeof(generated)) >= 0);
    const uint64_t produced = Silex_MIX_CaptureProduced(capture);
    const int count = Silex_MIX_CaptureRead(capture, captured, 32768);
    CHECK(count >= 4096 && (uint64_t)count == produced);
    CHECK(memcmp(generated, captured, sizeof(generated)) == 0);
    for (int i = 0; i < 8192; ++i) CHECK(fabsf(captured[i] - input[i] * 0.5f) < 0.000001f);
    Silex_MIX_CaptureStop(capture);
    CHECK(MIX_Generate(mixer, generated, sizeof(generated)) >= 0);
    CHECK(Silex_MIX_CaptureProduced(capture) == produced);
    CHECK(!Silex_MIX_CaptureActive(mixer));
    void *next = Silex_MIX_CaptureCreate(mixer, 32768);
    CHECK(next);
    Silex_MIX_CaptureDestroy(capture); /* An old stopped handle must not detach next. */
    CHECK(MIX_Generate(mixer, generated, sizeof(generated)) >= 0);
    CHECK(Silex_MIX_CaptureProduced(next) > 0);
    CHECK(Silex_MIX_CaptureError(next) == 0);
    CHECK(Silex_MIX_CaptureActive(mixer));
    Silex_MIX_CaptureDestroy(next);
    MIX_DestroyTrack(track); MIX_DestroyAudio(audio); MIX_DestroyMixer(mixer);
    printf("{\"case\":\"offline-postmix\",\"matched_frames\":4096,\"produced\":%llu,\"gain\":0.5,\"restart\":true}\n", (unsigned long long)produced);
}

static void device_test(bool hardware)
{
    CHECK(SDL_InitSubSystem(SDL_INIT_AUDIO));
    if (!hardware) CHECK(strcmp(SDL_GetCurrentAudioDriver(), "dummy") == 0);
    MIX_Mixer *mixer = MIX_CreateMixerDevice(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, NULL);
    CHECK(mixer);
    SDL_AudioSpec spec;
    CHECK(MIX_GetMixerFormat(mixer, &spec));
    spec.format = SDL_AUDIO_F32;
    const size_t samples = (size_t)spec.freq * (size_t)spec.channels * 10;
    float *input = SDL_malloc(samples * sizeof(float));
    CHECK(input);
    for (size_t i = 0; i < samples; ++i) input[i] = hardware ? 0.0f : 0.5f;
    MIX_Audio *audio = MIX_LoadRawAudio(mixer, input, samples * sizeof(float), &spec);
    SDL_free(input);
    MIX_Track *track = MIX_CreateTrack(mixer);
    CHECK(audio && track && MIX_SetTrackAudio(track, audio));
    CHECK(MIX_SetMixerGain(mixer, 0.5f));
    CHECK(MIX_PlayTrack(track, 0));
    void *capture = Silex_MIX_CaptureCreate(mixer, (uint64_t)spec.freq * 2);
    CHECK(capture);
    float block[4096 * 8];
    uint64_t read = 0;
    double energy = 0;
    const SDL_AudioDeviceID device = (SDL_AudioDeviceID)SDL_GetNumberProperty(MIX_GetMixerProperties(mixer), MIX_PROP_MIXER_DEVICE_NUMBER, 0);
    SDL_AudioSpec physical_spec; int sample_frames = 0;
    CHECK(SDL_GetAudioDeviceFormat(device, &physical_spec, &sample_frames));
    fprintf(stderr,"DRIVER %s physical_rate=%d channels=%d buffer_frames=%d\n",SDL_GetCurrentAudioDriver(),physical_spec.freq,physical_spec.channels,sample_frames);
    const uint64_t start = SDL_GetTicksNS();
    while (SDL_GetTicksNS() - start < 1000000000) {
        const int count = Silex_MIX_CaptureRead(capture, block, 4096);
        CHECK(count >= 0);
        for (int i = 0; i < count * spec.channels; ++i) energy += (double)block[i] * block[i];
        read += (uint64_t)count;
        CHECK(Silex_MIX_CaptureError(capture) == 0);
        SDL_Delay(3);
    }
    const uint64_t elapsed_ns = SDL_GetTicksNS() - start;
    Silex_MIX_CaptureStop(capture);
    const uint64_t produced = Silex_MIX_CaptureProduced(capture);
    CHECK(!Silex_MIX_CaptureRunning(capture));
    const uint64_t stopped = Silex_MIX_CaptureElapsedNS(capture);
    SDL_Delay(3);
    CHECK(Silex_MIX_CaptureElapsedNS(capture) == stopped);
    CHECK(Silex_MIX_CaptureFirstOffsetNS(capture) <= stopped);
    CHECK(Silex_MIX_CapturePeak(capture) <= Silex_MIX_CaptureCapacity(capture));
    fprintf(stderr,"DEVICE rate=%d channels=%d produced=%llu read=%llu position=%lld error=%d\n",spec.freq,spec.channels,(unsigned long long)produced,(unsigned long long)read,(long long)MIX_GetTrackPlaybackPosition(track),Silex_MIX_CaptureError(capture));
    CHECK(read > 0);
    const double rms = sqrt(energy / ((double)read * spec.channels));
    CHECK(fabs(rms - (hardware ? 0.0 : 0.25)) < 0.002);
    Silex_MIX_CaptureDestroy(capture);
    void *small = Silex_MIX_CaptureCreate(mixer, 16);
    CHECK(small);
    uint64_t deadline = SDL_GetTicksNS() + 2000000000;
    while (Silex_MIX_CaptureError(small) == 0 && SDL_GetTicksNS() < deadline) SDL_Delay(3);
    CHECK(Silex_MIX_CaptureError(small) == 1 && Silex_MIX_CaptureDropped(small) > 0);
    CHECK(MIX_TrackPlaying(track));
    const int64_t first = MIX_GetTrackPlaybackPosition(track);
    deadline = SDL_GetTicksNS() + 2000000000;
    while (MIX_GetTrackPlaybackPosition(track) == first && SDL_GetTicksNS() < deadline) SDL_Delay(3);
    const int64_t second = MIX_GetTrackPlaybackPosition(track);
    CHECK(second > first);
    CHECK(Silex_MIX_CaptureProduced(small) > Silex_MIX_CaptureDropped(small) - 1);
    Silex_MIX_CaptureDestroy(small);
    MIX_DestroyTrack(track); MIX_DestroyAudio(audio); MIX_DestroyMixer(mixer);
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
    printf("{\"case\":\"device-postmix\",\"rate\":%d,\"channels\":%d,\"produced\":%llu,\"read\":%llu,\"rms\":%.9f,\"playback_after_overflow\":true,\"elapsed_ns\":%llu}\n", spec.freq, spec.channels, (unsigned long long)produced, (unsigned long long)read, rms, (unsigned long long)elapsed_ns);
}

int main(int argc, char **argv)
{
    #ifndef ARCHIVE_PROBE
    ring_test();
    #endif
    CHECK(MIX_Init());
    offline_test();
    device_test(argc > 1 && strcmp(argv[1], "--hardware") == 0);
    MIX_Quit();
    return 0;
}
