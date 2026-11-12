#include <cmath>
#include <numbers>
#include <stdexcept>
#include <CalculatedExhaust.hpp>

// -----------------------------------------------------------------------------

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

// -----------------------------------------------------------------------------

int main() {
    EngineReference::ExhaustResponse settings;
    settings.count = 1;
    settings.bands[0] = { 425.0, 6.0, 6.0 };
    EngineReference::CalculatedExhaust first;
    EngineReference::CalculatedExhaust second;
    require(!first.active(), "unconfigured response must be inactive");
    first.configure(settings, 1.0);
    second.configure(settings, 1.0);
    require(first.active() && second.active(), "configured responses must be active");

    constexpr int rate = 44'100;
    double inputPower = 0;
    double outputPower = 0;
    for (int index = 0; index < rate; ++index) {
        const float input = static_cast<float>(std::sin(2.0 * std::numbers::pi * 425.0 * index / rate));
        const float output = first.process(input);
        require(second.process(0.0f) == 0.0f, "collector filter histories must be independent");
        if (index >= rate / 2) {
            inputPower += input * input;
            outputPower += output * output;
        }
    }
    require(std::abs(10.0 * std::log10(outputPower / inputPower) - 6.0) < 0.01, "gain at center frequency");

    first.configure(settings, 0.5);
    const float initial = second.process(1.0f);
    require(first.process(1.0f) == initial * 0.5f, "configuration resets history and applies collector volume");
}
