#pragma once
#include <cstdint>
#include <vector>
#include <engine.h>
#include <piston_engine_simulator.h>
#include <transmission.h>
#include <vehicle.h>

// -----------------------------------------------------------------------------

struct DriveSettings {
    double idle;
    double mass;
    double area;
    double drag;
    double diff;
    double wheel;
    double shift;
    double starter;
    int strokes;
    double audioCutoff;
    std::vector<double> ratios;
    double launchRpm { 0 };
};

// -----------------------------------------------------------------------------

class RoadVehicle : public Vehicle {

    // -------------------------------------------------------------------------
    // API

    public: void attachBrake(atg_scs::RigidBodySystem* system);
    public: void setBrake(double amount);

    // -------------------------------------------------------------------------
    // INTERNALS

    private: atg_scs::RotationFrictionConstraint brake;
};

// -----------------------------------------------------------------------------

class DriveController {

    // -------------------------------------------------------------------------
    // LIFECYCLE

    public: DriveController(const DriveSettings& settings, Engine& engine,
        Transmission& transmission, RoadVehicle& vehicle, bool bench = false, double launchClutchFraction = 1.0);

    // -------------------------------------------------------------------------
    // API

    public: double update(bool running, double pedal, int mode, int requestedGear,
        double braking, double dt, std::uint64_t gearRequest = 0);
    public: int currentGear() const { return gear; }
    public: int shiftCount() const { return shifts; }
    public: int flags() const;

    // -------------------------------------------------------------------------
    // INTERNALS

    private: const DriveSettings& settings;
    private: Engine& engine;
    private: Transmission& transmission;
    private: RoadVehicle& vehicle;
    private: const bool bench;
    private: const double launchClutchFraction;
    private: std::uint64_t lastGearRequest { 0 };
    private: bool cutThrottleDuringShift { true };
    private: int gear { 0 };
    private: int shifts { 0 };
    private: int rejectedGear { -1 };
    private: double shiftRemaining { 0 };
    private: double cooldown { 0 };
    private: double rejection { 0 };
};
