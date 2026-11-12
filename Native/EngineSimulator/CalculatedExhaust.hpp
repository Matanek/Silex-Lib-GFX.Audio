#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <fstream>
#include <numbers>
#include <stdexcept>
#include <string>

namespace EngineReference {

// -----------------------------------------------------------------------------

struct ExhaustBand {
    double frequencyHz;
    double quality;
    double gainDb;
};

struct ExhaustResponse {
    static constexpr std::size_t maxBands = 24;
    std::array<ExhaustBand, maxBands> bands {};
    std::size_t count { 0 };
    double gainDb { 0 };
};

// -----------------------------------------------------------------------------

[[nodiscard]] inline ExhaustResponse readExhaustResponse(const char* path) {
    std::ifstream input(path);
    std::string marker;
    ExhaustResponse response;
    if (!(input >> marker >> response.count >> response.gainDb) ||
        marker != "exhaust-response-v1" || response.count == 0 ||
        response.count > response.bands.size() ||
        !(response.gainDb >= -80.0 && response.gainDb <= 50.0)) {
        throw std::runtime_error("Invalid calculated exhaust response header");
    }
    double peakGainDb = response.gainDb;
    for (std::size_t index = 0; index < response.count; ++index) {
        auto& band = response.bands[index];
        if (!(input >> band.frequencyHz >> band.quality >> band.gainDb) ||
            !(band.frequencyHz >= 10.0 && band.frequencyHz <= 20'000.0 &&
              band.quality >= 0.1 && band.quality <= 50.0 &&
              band.gainDb >= -40.0 && band.gainDb <= 40.0)) {
            throw std::runtime_error("Invalid calculated exhaust response band");
        }
        if (band.gainDb > 0.0) peakGainDb += band.gainDb;
    }
    if (peakGainDb > 200.0) throw std::runtime_error("Excessive calculated exhaust response gain");
    std::string trailing;
    if (input >> trailing) throw std::runtime_error("Unexpected data after calculated exhaust response");
    return response;
}

// -----------------------------------------------------------------------------

class CalculatedExhaust {

    // -------------------------------------------------------------------------
    // API

    public: void configure(const ExhaustResponse& response, double volume) noexcept;
    public: [[nodiscard]] bool active() const noexcept { return count > 0; }
    public: [[nodiscard]] float process(float input) noexcept;

    // -------------------------------------------------------------------------
    // INTERNALS

    private: struct Section {
        double b0;
        double b1;
        double b2;
        double a1;
        double a2;
        double z1 { 0 };
        double z2 { 0 };
    };

    private: std::array<Section, ExhaustResponse::maxBands> sections {};
    private: std::size_t count { 0 };
    private: double gain { 1 };
};

// -----------------------------------------------------------------------------

inline void CalculatedExhaust::configure(const ExhaustResponse& response, double volume) noexcept {
    gain = volume * std::pow(10.0, response.gainDb / 20.0);
    count = response.count;
    for (std::size_t index = 0; index < count; ++index) {
        const auto& band = response.bands[index];
        const double a = std::pow(10.0, band.gainDb / 40.0);
        const double angle = 2.0 * std::numbers::pi * band.frequencyHz / 44'100.0;
        const double alpha = std::sin(angle) / (2.0 * band.quality);
        const double norm = 1.0 / (1.0 + alpha / a);
        const double firstOrder = -2.0 * std::cos(angle) * norm;
        sections[index] = {
            (1.0 + alpha * a) * norm,
            firstOrder,
            (1.0 - alpha * a) * norm,
            firstOrder,
            (1.0 - alpha / a) * norm
        };
    }
}

inline float CalculatedExhaust::process(float input) noexcept {
    double sample = input;
    for (std::size_t index = 0; index < count; ++index) {
        auto& band = sections[index];
        const double output = band.b0 * sample + band.z1;
        band.z1 = band.b1 * sample - band.a1 * output + band.z2;
        band.z2 = band.b2 * sample - band.a2 * output;
        sample = output;
    }
    return static_cast<float>(gain * sample);
}

// -----------------------------------------------------------------------------

} // namespace EngineReference
