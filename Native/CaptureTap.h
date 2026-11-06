#ifndef SILEX_MIX_CAPTURE_TAP_H
#define SILEX_MIX_CAPTURE_TAP_H
#include <SDL3/SDL.h>
#include <SDL3_mixer/SDL_mixer.h>
#include <stdint.h>
void *Silex_MIX_CaptureCreate(MIX_Mixer *mixer, uint64_t capacity_frames);
void Silex_MIX_CaptureStop(void *capture);
void Silex_MIX_CaptureDestroy(void *capture);
int Silex_MIX_CaptureRead(void *capture, float *output, int frames);
uint64_t Silex_MIX_CaptureProduced(void *capture);
uint64_t Silex_MIX_CaptureReadFrames(void *capture);
uint64_t Silex_MIX_CaptureAvailable(void *capture);
uint64_t Silex_MIX_CaptureDropped(void *capture);
int Silex_MIX_CaptureError(void *capture);
int Silex_MIX_CaptureSampleRate(void *capture);
int Silex_MIX_CaptureChannels(void *capture);
uint64_t Silex_MIX_CaptureFirstOffsetNS(void *capture);
uint64_t Silex_MIX_CaptureElapsedNS(void *capture);
uint64_t Silex_MIX_CaptureCapacity(void *capture);
uint64_t Silex_MIX_CapturePeak(void *capture);
uint64_t Silex_MIX_CaptureMaxBlock(void *capture);
int Silex_MIX_CaptureRunning(void *capture);
int Silex_MIX_CaptureActive(MIX_Mixer *mixer);
#endif
