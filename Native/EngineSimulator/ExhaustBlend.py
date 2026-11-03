"""Raccorder une pression brute équilibrée au témoin sans toucher le trajet 100 %."""
def prepare(source,replace):
    replace(source/'include/synthesizer.h','#include "convolution_filter.h"','#include "convolution_filter.h"\n#include <ExhaustBlend.hpp>')
    replace(source/'include/synthesizer.h','ConvolutionFilter convolution;','ConvolutionFilter convolution;\n            EngineReference::ExhaustBlend exhaustBlend;')
    replace(source/'src/synthesizer.cpp','m_filters[i].derivative.m_dt = 1 / m_audioSampleRate;',
        'm_filters[i].exhaustBlend = EngineReference::ExhaustBlend(m_audioSampleRate);\n        m_filters[i].derivative.m_dt = 1 / m_audioSampleRate;')
    replace(source/'src/synthesizer.cpp',
        'convAmount * m_filters[i].convolution.f(v_in)\n            + (1 - convAmount) * v_in;',
        'm_filters[i].exhaustBlend.process(f, m_filters[i].convolution.f(v_in), convAmount);')
