#include <crankshaft.h>
#include <function.h>
#include <ignition_module.h>
#include <cstdio>
#include <stdexcept>

// -----------------------------------------------------------------------------

static int countSparks(int strokes) {
    Crankshaft shaft;
    shaft.cycleRadians = strokes * constants::pi;
    shaft.m_body.theta = -0.123;
    shaft.m_body.v_theta = -units::rpm(3000);
    Function timing;
    timing.initialize(1, 1);
    timing.addSample(0, 0);
    IgnitionModule ignition;
    IgnitionModule::Parameters parameters;
    parameters.cylinderCount = 1;
    parameters.crankshaft = &shaft;
    parameters.timingCurve = &timing;
    ignition.initialize(parameters);
    ignition.setFiringOrder(0, 0);
    ignition.m_enabled = true;
    ignition.reset();
    int sparks = 0;
    for (int step = 0; step < 20000; ++step) {
        shaft.m_body.theta -= 2 * constants::pi / 1000;
        ignition.resetIgnitionEvents();
        ignition.update(1.0 / 50000);
        if (ignition.getIgnitionEvent(0)) ++sparks;
    }
    ignition.destroy();
    timing.destroy();
    return sparks;
}

// -----------------------------------------------------------------------------

int main() {
    const int two = countSparks(2);
    const int four = countSparks(4);
    if (two != 20 || four != 10) throw std::runtime_error("Ignition cycle mismatch");
    std::printf("Cycle checks passed: 20 crank revolutions, 2T=%d sparks, 4T=%d sparks\n", two, four);
}
