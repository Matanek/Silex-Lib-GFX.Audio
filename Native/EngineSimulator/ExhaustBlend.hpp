#pragma once
#include <algorithm>
#include <cmath>

namespace EngineReference {

// -----------------------------------------------------------------------------

class ExhaustBlend {

    // -------------------------------------------------------------------------
    // LIFECYCLE

    public: explicit ExhaustBlend(double sampleRate = 44100.0)
        : energyStep(1.0 - std::exp(-1.0 / (0.12 * sampleRate))),
          mixStep(1.0 - std::exp(-1.0 / (0.01 * sampleRate))) {}

    // -------------------------------------------------------------------------
    // API

    public: float process(float pressure, float filtered, float amount) {
        rawPower += energyStep * (static_cast<double>(pressure) * pressure - rawPower);
        filteredPower += energyStep * (static_cast<double>(filtered) * filtered - filteredPower);
        mix += mixStep * (static_cast<double>(amount) - mix);
        if (std::abs(mix - amount) < 0.000001) mix = amount;
        if (mix == 1.0) return filtered;
        const double gain = rawPower > 0.000000000001
            ? std::min(16.0, std::sqrt(filteredPower / rawPower)) : 0.0;
        return static_cast<float>(mix * filtered + (1.0 - mix) * pressure * gain);
    }

    // -------------------------------------------------------------------------
    // INTERNALS

    private: double energyStep;
    private: double mixStep;
    private: double rawPower { 0.0 };
    private: double filteredPower { 0.0 };
    private: double mix { 1.0 };
};

// -----------------------------------------------------------------------------

} // namespace EngineReference
