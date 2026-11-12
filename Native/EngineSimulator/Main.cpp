#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>
#include <compiler.h>
#include <impulse_response.h>
#include <piston_engine_simulator.h>
#include <CalculatedExhaust.hpp>
#include <Drive.hpp>
#include <GeneratedProfiles.hpp>

// -----------------------------------------------------------------------------

class CapturingSimulator : public PistonEngineSimulator {

    // -------------------------------------------------------------------------
    // API

    public: std::vector<float> trace;
    public: bool recording { false };
    public: bool captureIntake { false };
    public: std::vector<float> intake;
    public: bool captureCombustion { false };
    public: std::vector<uint32_t> combustion;
    public: void openCollectorCapture(const std::string& path) {
        collectors.open(path, std::ios::binary);
        if (!collectors) throw std::runtime_error("Cannot open collector capture");
    }
    public: void captureCollectorBlock(int frames, int channels) {
        if (!collectors.is_open()) return;
        auto& audio = synthesizer();
        for (int frame = 0; frame < frames; ++frame) {
            for (int channel = 0; channel < channels; ++channel) {
                const float sample = audio.m_inputChannels[channel].transferBuffer[frame];
                collectors.write(reinterpret_cast<const char*>(&sample), sizeof(sample));
            }
        }
        if (!collectors) throw std::runtime_error("Cannot write collector capture");
    }
    private: std::ofstream collectors;
    private: double previousIntakeFlow { 0 };
    private: uint32_t pendingCombustion { 0 };

    // -------------------------------------------------------------------------
    // INTERNALS

    protected: void writeToSynthesizer() override {
        auto& audio = synthesizer();
        const bool capture = captureIntake || captureCombustion;
        const int base = capture ? audio.m_inputChannels[0].data.writeIndex() : 0;
        const double previousOffset = capture ? audio.m_lastInputSampleOffset : 0;
        PistonEngineSimulator::writeToSynthesizer();
        if (captureIntake) {
            double flow = 0;
            for (int i = 0; i < m_engine->getCylinderCount(); ++i) {
                flow += std::max(0.0, m_engine->getChamber(i)->getLastTimestepIntakeFlow());
            }
            // Moles per mechanical step -> m3/s referred to ambient air.
            flow *= constants::R * units::celcius(25) / units::atm / getTimestep();
            // Suppress static gas-equilibration jitter as pumping comes to rest.
            // Contact is deliberately absent: a coasting engine still aspirates.
            flow *= std::clamp(m_engine->getRpm() / 60.0, 0.0, 1.0);
            const double distance = audio.inputDistance(audio.m_inputWriteOffset, previousOffset);
            // Follow exactly the exhaust resampling clock, including its boundary phase.
            for (double t = audio.inputDistance(base, previousOffset); t <= distance; t += 1) {
                const double fraction = t / distance;
                intake.push_back(static_cast<float>(previousIntakeFlow * (1 - fraction) + flow * fraction));
            }
            previousIntakeFlow = flow;
        }
        if (captureCombustion) {
            for (int i = 0; i < m_engine->getCylinderCount(); ++i) {
                if (m_engine->getChamber(i)->popLitLastFrame()) pendingCombustion |= uint32_t{1} << i;
            }
            const double distance = audio.inputDistance(audio.m_inputWriteOffset, previousOffset);
            for (double t = audio.inputDistance(base, previousOffset); t <= distance; t += 1) {
                combustion.push_back(pendingCombustion);
                pendingCombustion = 0;
            }
        }
        if (!recording) return;
        trace.push_back(static_cast<float>(m_engine->getRpm()));
        trace.push_back(static_cast<float>(m_engine->getOutputCrankshaft()->getCycleAngle()));
        for (int index = 0; index < m_engine->getExhaustSystemCount(); ++index) {
            trace.push_back(static_cast<float>(m_exhaustFlowStagingBuffer[index]));
        }
    }
};

// -----------------------------------------------------------------------------

static void writeInteger(std::ostream& stream, uint32_t value, int bytes) {
    for (int index = 0; index < bytes; ++index) {
        stream.put(static_cast<char>((value >> (index * 8)) & 255));
    }
}

static void writeWave(const std::string& path, const std::vector<int16_t>& samples) {
    std::ofstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error("Cannot open output: " + path);
    stream.write("RIFF", 4);
    writeInteger(stream, 36 + samples.size() * 2, 4);
    stream.write("WAVEfmt ", 8);
    writeInteger(stream, 16, 4);
    writeInteger(stream, 1, 2);
    writeInteger(stream, 1, 2);
    writeInteger(stream, 44100, 4);
    writeInteger(stream, 88200, 4);
    writeInteger(stream, 2, 2);
    writeInteger(stream, 16, 2);
    stream.write("data", 4);
    writeInteger(stream, samples.size() * 2, 4);
    for (int16_t sample : samples) writeInteger(stream, static_cast<uint16_t>(sample), 2);
    if (!stream) throw std::runtime_error("Cannot write output: " + path);
}

static std::vector<int16_t> readImpulse(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream || stream.tellg() <= 0 || stream.tellg() % 2 != 0) {
        throw std::runtime_error("Invalid mono PCM16 impulse: " + path);
    }
    std::vector<int16_t> samples(static_cast<size_t>(stream.tellg()) / 2);
    stream.seekg(0);
    stream.read(reinterpret_cast<char*>(samples.data()), samples.size() * 2);
    if (!stream) throw std::runtime_error("Cannot read impulse");
    return samples;
}

// -----------------------------------------------------------------------------

static void renderQuantum(CapturingSimulator& simulator, Engine& engine, std::vector<int16_t>& samples,
    std::vector<uint16_t>* intake = nullptr) {
    simulator.intake.clear();
    simulator.combustion.clear();
    Synthesizer& synthesizer = simulator.synthesizer();
    simulator.startFrame(0.01);
    while (simulator.simulateStep()) {}
    const int available = static_cast<int>(synthesizer.m_inputChannels[0].data.size());
    const auto parameters = synthesizer.getAudioParameters();
    for (int channel = 0; channel < engine.getExhaustSystemCount(); ++channel) {
        synthesizer.m_inputChannels[channel].data.read(available, synthesizer.m_inputChannels[channel].transferBuffer);
        synthesizer.m_filters[channel].jitterFilter.setJitterScale(parameters.inputSampleNoise);
    }
    simulator.captureCollectorBlock(available, engine.getExhaustSystemCount());
    if (intake && simulator.intake.size() != static_cast<size_t>(available)) {
        throw std::runtime_error("Intake/exhaust resampling clocks diverged");
    }
    for (int index = 0; index < available; ++index) {
        samples.push_back(synthesizer.renderAudio(index));
        if (intake) {
            const double flow = std::clamp(static_cast<double>(simulator.intake[index]), 0.0, 0.25);
            intake->push_back(static_cast<uint16_t>(std::round(flow * 65535 / 0.25)));
        }
    }
    for (int channel = 0; channel < engine.getExhaustSystemCount(); ++channel) {
        synthesizer.m_inputChannels[channel].data.removeBeginning(available);
    }
}

static double sweptVolume(const Engine& engine) {
    double volume = 0;
    for (int i = 0; i < engine.getCylinderCount(); ++i) {
        const auto* piston = engine.getPiston(i);
        volume += piston->getCylinderBank()->boreSurfaceArea() * 2 * piston->getRod()->getCrankshaft()->getThrow();
    }
    return volume;
}

static Vehicle::Parameters roadParameters(const DriveSettings& settings) {
    Vehicle::Parameters parameters;
    parameters.mass = settings.mass;
    parameters.diffRatio = settings.diff;
    parameters.tireRadius = settings.wheel;
    parameters.dragCoefficient = settings.drag;
    parameters.crossSectionArea = settings.area;
    parameters.rollingResistance = settings.mass * 9.81 * 0.012;
    return parameters;
}

static void serve(CapturingSimulator& simulator, Engine& engine, const DriveSettings& settings, int profile,
    bool withIntake, bool withCombustion, DriveController* drive, RoadVehicle* vehicle) {
    constexpr int maxCylinders = 16;
    if (withCombustion && engine.getCylinderCount() > maxCylinders) {
        throw std::runtime_error("Combustion telemetry supports up to 16 cylinders");
    }
    simulator.captureCombustion = withCombustion;
    simulator.captureIntake = withIntake;
    simulator.intake.reserve(1024);
    std::vector<uint16_t> intake;
    intake.reserve(2048);
    std::vector<int16_t> pending;
    pending.reserve(2048);
    std::vector<uint32_t> combustion;
    if (withCombustion) {
        simulator.combustion.reserve(1024);
        combustion.reserve(2048);
    }
    int frames = 0;
    int ignition = 0;
    double pedal = 0;
    double texture = 1;
    double convolution = 1;
    double baseRpm = 800;
    double load = 0;
    double contactTime = 0;
    double throttle = 0;
    bool wasRunning = false;
    int mode = 2;
    int requestedGear = 0;
    std::uint64_t gearRequest = 0;
    double brake = 0;
    bool brakeAttached = false;
    bool roadConfigured = false;
    while (std::cin >> frames >> ignition >> pedal >> texture >> convolution >> baseRpm >> load) {
        if (drive && (!(std::cin >> mode >> requestedGear >> brake >> gearRequest) ||
                mode < 1 || mode > 2 || requestedGear < 0 ||
                requestedGear > static_cast<int>(settings.ratios.size()) ||
                !std::isfinite(brake) || brake < 0 || brake > 1)) {
            throw std::runtime_error("Invalid bench transmission request");
        }
        if (frames < 1 || frames > 960 || ignition < 0 || ignition > 1 ||
            !std::isfinite(pedal) || pedal < 0 || pedal > 1 ||
            !std::isfinite(texture) || texture < 0 || texture > 1 ||
            !std::isfinite(convolution) || convolution < 0 || convolution > 1 ||
            !std::isfinite(baseRpm) || baseRpm < 700 || baseRpm > 4000 ||
            !std::isfinite(load) || load < 0 || load > 1) {
            throw std::runtime_error("Invalid reference-render request");
        }
        if (vehicle && !roadConfigured && (mode == 1 || requestedGear > 0 || brake > 0)) {
            vehicle->initialize(roadParameters(settings));
            roadConfigured = true;
        }
        if (vehicle && brake > 0 && !brakeAttached) {
            vehicle->attachBrake(simulator.getSystem());
            brakeAttached = true;
        }
        if (ignition && !wasRunning) contactTime = 0;
        wasRunning = ignition;
        auto parameters = simulator.synthesizer().getAudioParameters();
        parameters.airNoise = texture * engine.getInitialNoise();
        parameters.inputSampleNoise = texture * engine.getInitialJitter();
        parameters.convolution = convolution;
        parameters.volume = 0.5;
        simulator.synthesizer().setAudioParameters(parameters);
        while (pending.size() < static_cast<size_t>(frames)) {
            const bool starter = ignition && contactTime < settings.starter && engine.getRpm() < (profile == 0 ? 650 : std::max(650.0, settings.idle * 0.65));
            simulator.m_starterMotor.m_enabled = starter;
            const bool useDrive = drive && (mode == 1 || requestedGear > 0 ||
                drive->currentGear() > 0 || drive->flags() != 0 || brakeAttached);
            const double drivenPedal = useDrive ? drive->update(ignition, pedal, mode, requestedGear, brake, 0.01, gearRequest) : pedal;
            engine.getIgnitionModule()->m_enabled = ignition && !(useDrive && drive->isCuttingIgnition());
            const bool inGear = drive && drive->currentGear() > 0;
            const double requestedThrottle = ignition && !starter ?
                (profile == 0 ? 0.35 : 1.0) * (inGear ? drivenPedal : pedal) : 0;
            throttle += 0.16 * (requestedThrottle - throttle);
            engine.setSpeedControl(throttle);
            const bool heldSpeed = ignition && pedal == 0 && baseRpm > 800 && engine.getRpm() > 600;
            simulator.m_dyno.m_hold = heldSpeed;
            simulator.m_dyno.m_enabled = !inGear &&
                (heldSpeed || (ignition && pedal > 0 && load > 0 && engine.getRpm() > 900));
            simulator.m_dyno.m_rotationSpeed = units::rpm(baseRpm);
            const double loadTorque = profile == 0 ? 250 : std::max(25.0, engine.getDisplacement() * 100000);
            simulator.m_dyno.m_maxTorque = heldSpeed ? 10000 : load * loadTorque;
            const size_t start = pending.size();
            renderQuantum(simulator, engine, pending, withIntake ? &intake : nullptr);
            if (withCombustion) {
                if (simulator.combustion.size() != pending.size() - start) {
                    throw std::runtime_error("Combustion and audio clocks diverged");
                }
                combustion.insert(combustion.end(), simulator.combustion.begin(), simulator.combustion.end());
            }
            if (ignition) contactTime += 0.01;
        }
        const uint32_t magic = drive ? (withIntake ? 0x39563845 : 0x36563845) :
            (withIntake ? 0x38563845 : 0x34563845);
        writeInteger(std::cout, withCombustion ? magic | 0x40000000 : magic, 4);
        writeInteger(std::cout, frames, 4);
        writeInteger(std::cout, static_cast<uint32_t>(std::round(engine.getRpm() * 1000)), 4);
        writeInteger(std::cout, ignition && (contactTime < 1.2 || engine.getRpm() < 650), 4);
        if (drive) {
            writeInteger(std::cout, drive->currentGear(), 4);
            writeInteger(std::cout, static_cast<uint32_t>(std::round(vehicle->getSpeed() * 3600)), 4);
            writeInteger(std::cout, drive->flags(), 4);
            writeInteger(std::cout, drive->shiftCount(), 4);
        }
        if (withCombustion) {
            std::array<uint16_t, maxCylinders> offsets {};
            for (int index = 0; index < frames; ++index) {
                uint32_t lit = combustion[index];
                while (lit != 0) {
                    const int cylinder = std::countr_zero(lit);
                    offsets[cylinder] = static_cast<uint16_t>(index + 1);
                    lit &= lit - 1;
                }
            }
            for (const auto offset : offsets) writeInteger(std::cout, offset, 2);
            combustion.erase(combustion.begin(), combustion.begin() + frames);
        }
        for (int index = 0; index < frames; ++index) {
            writeInteger(std::cout, static_cast<uint16_t>(pending[index]), 2);
            if (withIntake) writeInteger(std::cout, intake[index], 2);
        }
        std::cout.flush();
        if (!std::cout) throw std::runtime_error("Reference output pipe closed");
        pending.erase(pending.begin(), pending.begin() + frames);
        if (withIntake) intake.erase(intake.begin(), intake.begin() + frames);
    }
    if (!std::cin.eof()) throw std::runtime_error("Malformed reference-render request");
}

static void serveDrive(CapturingSimulator& simulator, Engine& engine, RoadVehicle& vehicle, Transmission& transmission, const DriveSettings& settings, bool withIntake = false) {
    simulator.captureIntake = withIntake;
    simulator.intake.reserve(1024);
    std::vector<uint16_t> intake;
    intake.reserve(2048);
    DriveController drive(settings, engine, transmission, vehicle);
    vehicle.attachBrake(simulator.getSystem());
    std::vector<int16_t> pending;
    pending.reserve(2048);
    int frames = 0, ignition = 0, mode = 1, requestedGear = 0;
    double pedal = 0, texture = 1, convolution = 1, baseRpm = 800, load = 0, brake = 0;
    double contactTime = 0, throttle = 0;
    bool previousContact = false;
    while (std::cin >> frames >> ignition >> pedal >> texture >> convolution >> baseRpm >> load >> mode >> requestedGear >> brake) {
        if (frames < 1 || frames > 960 || ignition < 0 || ignition > 1 || mode < 1 || mode > 2 ||
            requestedGear < 0 || requestedGear > static_cast<int>(settings.ratios.size()) ||
            !std::isfinite(pedal) || pedal < 0 || pedal > 1 || !std::isfinite(texture) || texture < 0 || texture > 1 ||
            !std::isfinite(convolution) || convolution < 0 || convolution > 1 || !std::isfinite(brake) || brake < 0 || brake > 1 ||
            !std::isfinite(baseRpm) || baseRpm < 700 || baseRpm > 4000 || !std::isfinite(load) || load < 0 || load > 1) {
            throw std::runtime_error("Invalid drivetrain request");
        }
        if (ignition && !previousContact) contactTime = 0;
        previousContact = ignition;
        auto parameters = simulator.synthesizer().getAudioParameters();
        parameters.airNoise = texture * engine.getInitialNoise();
        parameters.inputSampleNoise = texture * engine.getInitialJitter();
        parameters.convolution = convolution;
        parameters.volume = 0.5;
        simulator.synthesizer().setAudioParameters(parameters);
        while (pending.size() < static_cast<size_t>(frames)) {
            const bool starter = ignition && contactTime < settings.starter && engine.getRpm() < std::max(650.0, settings.idle * 0.65);
            simulator.m_starterMotor.m_enabled = starter;
            engine.getIgnitionModule()->m_enabled = ignition;
            const double requested = drive.update(ignition, pedal, mode, requestedGear, brake, 0.01);
            const double target = ignition && !starter ? requested : 0;
            throttle += 0.16 * (target - throttle);
            engine.setSpeedControl(throttle);
            simulator.m_dyno.m_enabled = false;
            renderQuantum(simulator, engine, pending, withIntake ? &intake : nullptr);
            if (ignition) contactTime += 0.01;
        }
        writeInteger(std::cout, withIntake ? 0x39563845 : 0x36563845, 4);
        writeInteger(std::cout, frames, 4);
        writeInteger(std::cout, static_cast<uint32_t>(std::round(engine.getRpm() * 1000)), 4);
        writeInteger(std::cout, ignition && (contactTime < 1.2 || engine.getRpm() < 650), 4);
        writeInteger(std::cout, drive.currentGear(), 4);
        writeInteger(std::cout, static_cast<uint32_t>(std::round(vehicle.getSpeed() * 3600)), 4);
        writeInteger(std::cout, drive.flags(), 4);
        writeInteger(std::cout, drive.shiftCount(), 4);
        for (int index = 0; index < frames; ++index) {
            writeInteger(std::cout, static_cast<uint16_t>(pending[index]), 2);
            if (withIntake) writeInteger(std::cout, intake[index], 2);
        }
        std::cout.flush();
        if (!std::cout) throw std::runtime_error("Drivetrain output pipe closed");
        pending.erase(pending.begin(), pending.begin() + frames);
        if (withIntake) intake.erase(intake.begin(), intake.begin() + frames);
    }
    if (!std::cin.eof()) throw std::runtime_error("Malformed drivetrain request");
}

// -----------------------------------------------------------------------------

class FollowRotation : public atg_scs::Constraint {
    public: explicit FollowRotation(Engine& engine) : atg_scs::Constraint(1, 1) {
        m_bodies[0] = &engine.getOutputCrankshaft()->m_body;
    }
    public: void setRpm(double rpm) { speed = units::rpm(rpm); }
    public: void calculate(Output* output, atg_scs::SystemState*) override {
        output->J[0][0] = 0; output->J[0][1] = 0; output->J[0][2] = 1;
        output->J_dot[0][0] = 0; output->J_dot[0][1] = 0; output->J_dot[0][2] = 0;
        output->ks[0] = 0; output->kd[0] = 1; output->C[0] = 0;
        output->v_bias[0] = speed;
        output->limits[0][0] = -10000; output->limits[0][1] = 10000;
    }
    private: double speed { 0 };
};

// -----------------------------------------------------------------------------

static void serveFollowing(CapturingSimulator& simulator, Engine& engine, FollowRotation& rotation, bool withIntake) {
    simulator.captureIntake = withIntake;
    simulator.intake.reserve(1024);
    std::vector<uint16_t> intake;
    intake.reserve(2048);
    std::vector<int16_t> pending;
    pending.reserve(2048);
    int frames = 0, ignition = 0;
    double load = 0, texture = 1, convolution = 1, target = 0, unused = 0;
    double rpm = 0, opening = 0;
    while (std::cin >> frames >> ignition >> load >> texture >> convolution >> target >> unused) {
        if (frames < 1 || frames > 960 || ignition < 0 || ignition > 1 ||
            !std::isfinite(load) || load < 0 || load > 1 || !std::isfinite(target) || target < 0 || target > 12000 ||
            !std::isfinite(texture) || texture < 0 || texture > 1 || !std::isfinite(convolution) || convolution < 0 || convolution > 1 || unused != 0) {
            throw std::runtime_error("Invalid externally driven engine state");
        }
        auto parameters = simulator.synthesizer().getAudioParameters();
        parameters.airNoise = texture * engine.getInitialNoise();
        parameters.inputSampleNoise = texture * engine.getInitialJitter();
        parameters.convolution = convolution; parameters.volume = 0.5;
        simulator.synthesizer().setAudioParameters(parameters);
        while (pending.size() < static_cast<size_t>(frames)) {
            rpm += std::clamp(target - rpm, -200.0, 200.0);
            rotation.setRpm(rpm);
            simulator.m_starterMotor.m_enabled = false;
            simulator.m_dyno.m_enabled = false;
            engine.getIgnitionModule()->m_enabled = ignition;
            opening += 0.16 * ((ignition ? load : 0) - opening);
            engine.setSpeedControl(opening);
            renderQuantum(simulator, engine, pending, withIntake ? &intake : nullptr);
        }
        writeInteger(std::cout, withIntake ? 0x42563845 : 0x41563845, 4);
        writeInteger(std::cout, frames, 4);
        writeInteger(std::cout, static_cast<uint32_t>(std::round(std::max(0.0, engine.getRpm()) * 1000)), 4);
        writeInteger(std::cout, 0, 4);
        for (int index = 0; index < frames; ++index) {
            writeInteger(std::cout, static_cast<uint16_t>(pending[index]), 2);
            if (withIntake) writeInteger(std::cout, intake[index], 2);
        }
        std::cout.flush();
        if (!std::cout) throw std::runtime_error("Reference output pipe closed");
        pending.erase(pending.begin(), pending.begin() + frames);
        if (withIntake) intake.erase(intake.begin(), intake.begin() + frames);
    }
    if (!std::cin.eof()) throw std::runtime_error("Malformed externally driven engine state");
}

// -----------------------------------------------------------------------------

static void renderOffline(CapturingSimulator& simulator, Engine& engine, const std::string& prefix) {
    std::vector<int16_t> samples;
    std::ofstream states(prefix + ".csv");
    if (!states) throw std::runtime_error("Cannot open state output");
    states << "seconds,rpm,throttle,ignition,starter\n";
    simulator.recording = true;
    for (int block = 0; block < 1400; ++block) {
        const double time = block * 0.01;
        const bool ignition = time >= 0.3 && time < 11.5;
        const bool starter = time >= 0.3 && time < 1.5;
        const double pedal = time >= 5 && time < 7 ? 0.35 : 0;
        engine.getIgnitionModule()->m_enabled = ignition;
        simulator.m_starterMotor.m_enabled = starter;
        engine.setSpeedControl(pedal);
        renderQuantum(simulator, engine, samples);
        states << time << ',' << engine.getRpm() << ',' << pedal << ',' << ignition << ',' << starter << '\n';
        if (block % 100 == 0) {
            std::printf("t=%.1f, rpm=%.1f\n", time, engine.getRpm());
            std::fflush(stdout);
        }
    }
    writeWave(prefix + ".wav", samples);
    std::ofstream trace(prefix + ".f32", std::ios::binary);
    trace.write(reinterpret_cast<const char*>(simulator.trace.data()), simulator.trace.size() * sizeof(float));
    std::printf("Output: %zu frames, %.6f seconds\n", samples.size(), samples.size() / 44100.0);
    if (!states || !trace) throw std::runtime_error("Cannot write diagnostic trace");
}

// -----------------------------------------------------------------------------

static double gearingValue(const char* text) {
    std::size_t consumed = 0;
    const double value = std::stod(text, &consumed);
    if (consumed != std::string(text).size() || !std::isfinite(value) || value < 0.05 || value > 20.0) {
        throw std::runtime_error("Gearing values must be finite and in 0.05..20");
    }
    return value;
}

// -----------------------------------------------------------------------------

int main(int count, char** arguments) {
    try {
        if (count < 5 || count > 22) {
            std::fprintf(stderr, "Usage: RenderReference profile.mr response output-prefix mode [profile-index]\n");
            return 2;
        }
        const std::string mode = arguments[4];
        const bool calculated = mode == "serve-calculated" || mode == "follow-calculated";
        const bool following = mode == "follow" || mode == "follow-intake" || mode == "follow-calculated";
        const bool bench = mode == "bench-combustion" || mode == "bench-intake-combustion";
        const bool withCombustion = bench || mode == "serve-combustion" || mode == "serve-intake-combustion";
        const bool serving = mode == "serve" || mode == "serve-intake" || mode == "serve-calculated" || withCombustion;
        const bool withIntake = mode == "serve-intake" || mode == "drive-intake" ||
            mode == "follow-intake" || mode == "serve-intake-combustion" || mode == "bench-intake-combustion";
        const bool driving = mode == "drive" || mode == "drive-intake";
        if (mode != "full" && mode != "base" && !serving && !driving && !following) throw std::runtime_error("Unknown rendering mode");
        const int profile = count >= 6 ? std::stoi(arguments[5]) : 0;
        auto settings = profileSettings(profile);
        int option = 6;
        bool calibratedVehicle = false;
        if (bench && option + 1 < count && std::string_view(arguments[option]) == "--vehicle") {
            calibratedVehicle = configureBenchVehicle(arguments[option + 1], settings);
            option += 2;
        }
        if (option < count) {
            const int ratioCount = count - option - 2;
            if ((!driving && !bench) || std::string_view(arguments[option]) != "--gearing" ||
                    ratioCount < 1 || ratioCount > 12) {
                throw std::runtime_error("Expected final reduction and one to twelve gear ratios");
            }
            settings.diff = gearingValue(arguments[option + 1]);
            settings.ratios.clear();
            for (int i = option + 2; i < count; ++i) {
                const double ratio = gearingValue(arguments[i]);
                if (!settings.ratios.empty() && ratio >= settings.ratios.back()) {
                    throw std::runtime_error("Gear ratios must decrease from first to last");
                }
                settings.ratios.push_back(ratio);
            }
        }
        const auto impulse = calculated ? std::vector<int16_t>() : readImpulse(arguments[2]);
        const auto response = calculated ? EngineReference::readExhaustResponse(arguments[2]) : EngineReference::ExhaustResponse();
        std::srand(42);
        es_script::Compiler compiler;
        compiler.initialize();
        if (!compiler.compile(arguments[1])) {
            compiler.destroy();
            throw std::runtime_error("Profile compile failed; see error_log.log");
        }
        const auto output = compiler.execute();
        compiler.destroy();
        if (!output.engine) throw std::runtime_error("Profile did not produce an engine");
        Engine& engine = *output.engine;
        std::fprintf(stderr, "Engine: %s, mode: %s\n", engine.getName().c_str(), mode.c_str());
        std::fflush(stderr);
        if (settings.strokes == 2) {
            if (engine.getCylinderCount() != 1) throw std::runtime_error("Two-stroke profile must be a single cylinder");
            engine.getOutputCrankshaft()->cycleRadians = 2 * constants::pi;
            engine.getChamber(0)->twoStroke = true;
        }
        RoadVehicle vehicle;
        Vehicle::Parameters vehicleParameters;
        vehicleParameters.mass = 1597;
        vehicleParameters.diffRatio = 3.42;
        vehicleParameters.tireRadius = 10 * units::inch;
        vehicleParameters.dragCoefficient = 0.25;
        vehicleParameters.crossSectionArea = 36 * units::foot * units::foot;
        vehicleParameters.rollingResistance = 2000;
        if (driving) vehicleParameters = roadParameters(settings);
        vehicle.initialize(vehicleParameters);
        Transmission transmission;
        const double ratios[] = {2.97, 2.07, 1.43, 1.0, 0.84, 0.56};
        Transmission::Parameters transmissionParameters;
        transmissionParameters.GearCount = 6;
        transmissionParameters.GearRatios = ratios;
        transmissionParameters.MaxClutchTorque = 1000 * units::ft_lb;
        if (driving || bench) {
            transmissionParameters.GearCount = settings.ratios.size();
            transmissionParameters.GearRatios = settings.ratios.data();
            if (settings.strokes == 2) transmissionParameters.MaxClutchTorque = 40;
        }
        double launchClutchFraction = 1.0;
        if (bench) {
            const double launchCapacity = std::clamp(sweptVolume(engine) * 120000.0,
                35.0, transmissionParameters.MaxClutchTorque);
            if (calibratedVehicle) launchClutchFraction = launchCapacity / transmissionParameters.MaxClutchTorque;
            else transmissionParameters.MaxClutchTorque = launchCapacity;
        }
        transmission.initialize(transmissionParameters);
        CapturingSimulator simulator;
        const std::string_view outputPrefix = arguments[3];
        constexpr std::string_view capturePrefix = "collectors=";
        if ((serving || following) && outputPrefix.starts_with(capturePrefix)) {
            simulator.openCollectorCapture(std::string(outputPrefix.substr(capturePrefix.size())));
        }
        Simulator::Parameters simulatorParameters;
        simulator.initialize(simulatorParameters);
        simulator.setSimulationFrequency(static_cast<int>(engine.getSimulationFrequency()));
        simulator.loadSimulation(&engine, &vehicle, &transmission);
        simulator.setFluidSimulationSteps(8);
        simulator.setTargetSynthesizerLatency(0);
        Synthesizer& synthesizer = simulator.synthesizer();
        if (settings.strokes == 2) {
            synthesizer.m_levelingFilter.immediateAttack = true;
            synthesizer.m_levelingFilter.p_minLevel = 0;
        }
        synthesizer.m_latency = 0;
        auto parameters = synthesizer.getAudioParameters();
        parameters.inputSampleNoise = mode == "base" ? 0 : engine.getInitialJitter();
        parameters.airNoise = mode == "base" ? 0 : engine.getInitialNoise();
        parameters.dF_F_mix = mode == "base" ? 0 : engine.getInitialHighFrequencyGain();
        parameters.convolution = mode == "base" ? 0 : 1;
        parameters.volume = 0.7;
        synthesizer.setAudioParameters(parameters);
        for (int index = 0; index < engine.getExhaustSystemCount(); ++index) {
            synthesizer.m_filters[index].antialiasing.setCutoffFrequency(settings.audioCutoff, 44100);
            const double volume = engine.getExhaustSystem(index)->getImpulseResponse()->getVolume();
            if (calculated) synthesizer.m_filters[index].calculatedExhaust.configure(response, volume);
            else synthesizer.initializeImpulseResponse(impulse.data(), impulse.size(), volume, index);
        }
        FollowRotation rotation(engine);
        if (following) { simulator.getSystem()->addConstraint(&rotation); serveFollowing(simulator, engine, rotation, withIntake); }
        else if (driving) serveDrive(simulator, engine, vehicle, transmission, settings, withIntake);
        else if (serving) {
            DriveController drive(settings, engine, transmission, vehicle, bench, launchClutchFraction);
            serve(simulator, engine, settings, profile, withIntake, withCombustion,
                bench ? &drive : nullptr, bench ? &vehicle : nullptr);
        }
        else renderOffline(simulator, engine, arguments[3]);
        synthesizer.destroy();
        simulator.destroy();
        engine.destroy();
        delete output.engine;
        for (Function* function : output.functions) {
            function->destroy();
            delete function;
        }
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
