#include <cmath>
#include <iostream>
#include <stdexcept>
#include <ExhaustBlend.hpp>

// -----------------------------------------------------------------------------

static void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

// -----------------------------------------------------------------------------

int main() {
    EngineReference::ExhaustBlend blend;
    double referencePower = 0;
    double nearError = 0;
    double rawPower = 0;
    for (int i = 0; i < 44100 * 4; ++i) {
        const double phase = i * 6.283185307179586 / 44100.0;
        const float filtered = static_cast<float>(0.5 * std::sin(80 * phase));
        const float pressure = static_cast<float>(4000 * std::sin(80 * phase) + 400 * std::sin(800 * phase));
        const float amount = i < 44100 ? 1.0f : i < 88200 ? 0.99f : 0.0f;
        const float value = blend.process(pressure, filtered, amount);
        require(std::isfinite(value) && std::abs(value) < 2, "bounded raw mix");
        if (i < 44100) require(value == filtered, "full convolution must remain exact");
        if (i >= 44100 && i < 88200) {
            referencePower += filtered * filtered;
            nearError += (value - filtered) * (value - filtered);
        }
        if (i >= 132300) rawPower += value * value;
    }
    require(std::sqrt(nearError / referencePower) < 0.02, "one percent must remain a small change");
    require(rawPower / referencePower > 0.8 && rawPower / referencePower < 1.2, "raw and wet levels agree");
    float restored = 0;
    for (int i = 0; i < 10000; ++i) restored = blend.process(4000.0f, 0.5f, 1.0f);
    require(restored == 0.5f, "return to full convolution settles exactly");
    std::cout << "Exhaust blend checks passed\n";
}
