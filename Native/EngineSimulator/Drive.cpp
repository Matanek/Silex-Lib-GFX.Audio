#include <Drive.hpp>
#include <algorithm>
#include <cmath>

// -----------------------------------------------------------------------------

void RoadVehicle::attachBrake(atg_scs::RigidBodySystem* system) {
    brake.setBody(m_rotatingMass);
    system->addConstraint(&brake);
}

void RoadVehicle::setBrake(double amount) {
    const double torque = linearForceToVirtualTorque(amount * getMass() * 9.0);
    brake.m_minTorque = -torque;
    brake.m_maxTorque = torque;
}

// -----------------------------------------------------------------------------

DriveController::DriveController(const DriveSettings& settings, Engine& engine,
    Transmission& transmission, RoadVehicle& vehicle, bool bench)
    : settings(settings), engine(engine), transmission(transmission), vehicle(vehicle), bench(bench) {}

// -----------------------------------------------------------------------------

int DriveController::flags() const {
    return (shiftRemaining > 0 ? 1 : 0) | (rejection > 0 ? 2 : 0);
}

double DriveController::update(bool running, double pedal, int mode, int requestedGear,
    double braking, double dt) {
    shiftRemaining = std::max(0.0, shiftRemaining - dt);
    cooldown = std::max(0.0, cooldown - dt);
    rejection = std::max(0.0, rejection - dt);
    vehicle.setBrake(braking);
    const double rpm = engine.getRpm();
    if (mode == 1 || requestedGear != rejectedGear) rejectedGear = -1;
    int target = gear;
    if (mode == 1) {
        if (running && pedal > 0 && gear == 0 && rpm > settings.idle * 0.8) target = 1;
        else if (gear > 0 && cooldown == 0 && shiftRemaining == 0) {
            if (rpm > units::toRpm(engine.getRedline()) * 0.84 && pedal > 0 && gear < static_cast<int>(settings.ratios.size())) target = gear + 1;
            else if (rpm < std::max(settings.idle * 1.5, units::toRpm(engine.getRedline()) * 0.32) && gear > 1) target = gear - 1;
        }
    } else if (requestedGear != rejectedGear) target = requestedGear;
    else rejection = 0.6;
    if (target != gear && shiftRemaining == 0) {
        double coupledRpm = 0;
        if (target > 0) coupledRpm = units::toRpm(vehicle.getSpeed() / settings.wheel * settings.diff * settings.ratios[target - 1]);
        if (target > 0 && coupledRpm > units::toRpm(engine.getRedline()) * 1.02) {
            rejection = 0.6;
            if (mode != 1) rejectedGear = target;
        }
        else {
            transmission.setClutchPressure(0);
            transmission.changeGear(target - 1);
            // Selecting a gear from neutral is a clutch engagement, with the pedal still active.
            cutThrottleDuringShift = !bench || (gear > 0 && target > 0);
            gear = target;
            shiftRemaining = settings.shift;
            cooldown = 0.75;
            ++shifts;
        }
    }
    double clutch = 0;
    if (gear > 0) {
        const double releaseRpm = settings.idle * (bench ? 0.90 : 0.55);
        const double clutchRange = settings.idle * (bench ? 0.85 : 0.60);
        const double antiStall = std::clamp((rpm - releaseRpm) / clutchRange, 0.0, 1.0);
        double launch = vehicle.getSpeed() > 3.0 ? 1.0 : std::clamp((rpm - settings.idle * 0.8) / settings.idle, 0.0, 1.0);
        if (settings.strokes == 2) {
            // A small two-stroke launches above idle with a slipping clutch.
            const double launchRpm = units::toRpm(engine.getRedline()) * 0.45;
            const double coupledRpm = units::toRpm(vehicle.getSpeed() / settings.wheel * settings.diff * settings.ratios[gear - 1]);
            launch = coupledRpm > launchRpm ? 1.0 : std::clamp((rpm - launchRpm) / 1500, 0.0, 1.0);
        }
        clutch = std::min(antiStall, launch);
        if (vehicle.getSpeed() < 1.0 && pedal == 0) clutch = 0;
        if (shiftRemaining > 0) {
            const double engagement = cutThrottleDuringShift ? settings.shift * 0.45 : settings.shift;
            clutch *= std::clamp(1.0 - shiftRemaining / engagement, 0.0, 1.0);
        }
    }
    transmission.setClutchPressure(clutch);
    if (cutThrottleDuringShift && shiftRemaining > settings.shift * 0.45) return 0;
    return pedal;
}
