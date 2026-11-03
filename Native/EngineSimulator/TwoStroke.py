"""Adaptation mono 2T du témoin : lumières, balayage simplifié et allumage 360°.

Le réservoir de transfert à pression prescrite remplace le carter-pompe. Ce
modèle sonore ne prétend pas qualifier la thermodynamique d'un moteur réel.
La branche 4T reste textuellement inchangée derrière les valeurs par défaut.
"""


def prepare(source, replace):
    replace(source / 'include/crankshaft.h', '#include "part.h"', '#include "part.h"\n#include "constants.h"')
    replace(source / 'include/crankshaft.h', 'double getCycleAngle(double offset = 0.0);',
        'double getCycleAngle(double offset = 0.0);\n        double cycleRadians = 4 * constants::pi;')
    replace(source / 'src/crankshaft.cpp', 'std::fmod(-getAngle() + offset, 4 * constants::pi)',
        'std::fmod(-getAngle() + offset, cycleRadians)')
    replace(source / 'src/crankshaft.cpp', '? wrapped + 4 * constants::pi', '? wrapped + cycleRadians')
    replace(source / 'src/ignition_module.cpp', 'const double fourPi = 4 * constants::pi;',
        'const double fourPi = m_crankshaft->cycleRadians;')
    replace(source / 'include/combustion_chamber.h', 'void update(double dt);',
        'bool twoStroke = false;\n        void update(double dt);')
    replace(source / 'src/combustion_chamber.cpp', '    m_exhaustFlowRate = m_head->exhaustFlowRate(m_piston->getCylinderIndex());', '''    m_exhaustFlowRate = m_head->exhaustFlowRate(m_piston->getCylinderIndex());
    if (twoStroke) {
        // Single-cylinder port timing, referenced to top dead centre.
        const double phase = m_engine->getOutputCrankshaft()->getCycleAngle();
        const double exhaust = std::max(0.0, -std::cos(phase));
        const double transfer = std::max(0.0, (-std::cos(phase) - 0.5) * 2.0);
        const double throttle = std::cos(m_head->getIntake(0)->getThrottlePlatePosition() * constants::pi / 2);
        m_exhaustFlowRate = GasSystem::k_carb(180) * exhaust;
        m_intakeFlowRate = GasSystem::k_carb(130) * transfer * throttle;
        // Prescribed crankcase-pump supply; port flow still uses the gas solver.
        const double pressure = units::atm * (1.0 + 0.35 * (0.5 - 0.5 * std::cos(phase)));
        const double air = 55.0 / 56.0;
        m_intakeRunnerAndManifold.reset(pressure, units::celcius(25), {1.0 - air, air * 0.75, air * 0.25});
    }''')
    replace(source / 'src/combustion_chamber.cpp', 'flowParams.k_flow = m_manifoldToRunnerFlowRate;',
        'flowParams.k_flow = twoStroke ? 0 : m_manifoldToRunnerFlowRate;')
    replace(source / 'src/combustion_chamber.cpp', '(crankAngle / (4 * constants::pi))',
        '(crankAngle / m_engine->getOutputCrankshaft()->cycleRadians)')

    # New sharp 2T transients need peak capture before PCM16 conversion. The
    # original smoothed leveler remains the default for every four-stroke.
    replace(source / 'include/leveling_filter.h', 'float p_target;',
        'float p_target;\n        bool immediateAttack = false;')
    replace(source / 'src/leveling_filter.cpp', 'm_attenuation = 0.9 * m_attenuation + 0.1 * attenuation;',
        'm_attenuation = immediateAttack && attenuation < m_attenuation ? attenuation : 0.9 * m_attenuation + 0.1 * attenuation;')
