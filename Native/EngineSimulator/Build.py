#!/usr/bin/env python3
"""Construire un témoin engine-sim depuis des archives Git immuables, pour GFX.Audio."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import wave
import TwoStroke
import Impulse
import ExhaustBlend
import Catalog
import PackageLibrary

REVISION = '85f7c3b959a908ed5232ede4f1a4ac7eafe6b630'
DEPENDENCIES = {
    'simple-2d-constraint-solver': 'e009f4ff1c9c4c5874e865e893cdb62e208fb2b3',
    'piranha': '432f0b122bb1663b686c553c7e7269300afac3bc',
    'csv-io': '2112c55e1e831c8f7a1b91de23722b7926ad3d00',
}


def archive(repository, revision, destination, paths):
    resolved = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', revision + '^{commit}'], text=True).strip()
    if resolved != revision:
        raise RuntimeError('Révision inattendue : ' + resolved)
    data = subprocess.check_output(['git', '-C', str(repository), 'archive', revision, *paths])
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as stream:
        stream.extractall(destination, filter='data')


def replace(path, before, after):
    source = path.read_text()
    if before not in source:
        raise RuntimeError('Adaptation non applicable : ' + str(path))
    path.write_text(source.replace(before, after))


def prepare(source):
    replace(source / 'src/synthesizer.cpp', '#include "../include/delta.h"\n', '')
    replace(source / 'src/engine.cpp', '#include "..\\include\\engine.h"\n', '')
    replace(source / 'include/gas_system.h', 'const Mix &mix = {}', 'const Mix &mix = {0.0, 1.0, 0.0}')
    replace(source / 'include/ring_buffer.h', 'if (start + index < m_capacity)', 'if (m_start + index < m_capacity)')
    for name in ['constants.h', 'units.h']:
        replace(source / 'include' / name, 'extern constexpr', 'inline constexpr')
    replace(source / 'scripting/include/object_reference_node.h', 'template <typename Type>\n        void overrideType()', 'template <typename OverrideType>\n        void overrideType()')
    replace(source / 'scripting/include/object_reference_node.h', 'LookupChannelType<Type>()', 'LookupChannelType<OverrideType>()')
    scs = source / 'dependencies/submodules/simple-2d-constraint-solver'
    replace(scs / 'include/sparse_matrix.h', '#include <string.h>', '#include <string.h>\n#include "matrix.h"')
    piranha = source / 'dependencies/submodules/piranha'
    path = piranha / 'include/path.h'
    text = path.read_text()
    start = text.index('// Forward Boost declaration')
    end = text.index('namespace piranha', start)
    path.write_text((text[:start] + '#include <filesystem>\n\n' + text[end:]).replace('boost::filesystem', 'std::filesystem'))
    replace(piranha / 'src/path.cpp', '#include <boost/filesystem.hpp>', '#include <filesystem>')
    replace(piranha / 'src/path.cpp', 'boost::filesystem', 'std::filesystem')
    replace(piranha / 'src/path.cpp', 'is_complete()', 'is_absolute()')
    replace(piranha / 'src/standard_allocator.cpp', '#include <malloc.h>', '#include <cstdlib>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Clone public engine-sim et ses trois sous-modules utiles')
    parser.add_argument('--output', required=True, type=Path, help='Dossier de build et runtime de ce témoin')
    parser.add_argument('--bison', default='bison')
    parser.add_argument('--scalar-fir', action='store_true')
    args = parser.parse_args()
    if Catalog.path.read_text() != Catalog.generated():
        raise RuntimeError("Rebuild the Silex profile catalogue with Catalog.py")
    root = args.source.resolve()
    output = args.output.resolve()
    tools = Path(__file__).resolve().parent
    snapshot = output / 'Source'
    archive(root, REVISION, snapshot, ['CMakeLists.txt', 'LICENSE', 'src', 'include', 'scripting', 'es',
        'assets/engines', 'assets/sound-library'])
    for name, revision in DEPENDENCIES.items():
        paths = ['include', 'src']
        if name == 'piranha':
            paths += ['flex-bison']
        archive(root / 'dependencies/submodules' / name, revision, snapshot / 'dependencies/submodules' / name, paths)
    prepare(snapshot)
    TwoStroke.prepare(snapshot, replace)
    ExhaustBlend.prepare(snapshot, replace)
    profiles = json.loads((tools / 'Profiles.json').read_text())['profiles']
    generated = '#pragma once\n#include <Drive.hpp>\ninline DriveSettings profileSettings(int index) {\n    switch (index) {\n'
    for index, profile in enumerate(profiles):
        values = ', '.join(str(profile[key]) for key in ['idle','mass','area','drag','diff','wheel','shift','starter','strokes','audio_cutoff'])
        ratios = ', '.join(str(value) for value in profile['ratios'])
        generated += f'        case {index}: return {{{values}, {{{ratios}}}}};\n'
    generated += '        default: throw std::runtime_error("Unknown profile");\n    }\n}\n'
    (output / 'GeneratedProfiles.hpp').write_text(generated)
    compiler = Path(subprocess.check_output(['xcrun', '--find', 'clang++'], text=True).strip())
    flex_include = compiler.parent.parent / 'include'
    if not (flex_include / 'FlexLexer.h').is_file():
        raise RuntimeError('Header Flex du toolchain Xcode introuvable')
    subprocess.run(['cmake', '-S', str(tools), '-B', str(output / 'CMake'), '-DCMAKE_BUILD_TYPE=Release',
        '-DENGINE_REFERENCE_GENERATED=' + str(output), '-DENGINE_REFERENCE_SOURCE=' + str(snapshot), '-DENGINE_REFERENCE_FLEX_INCLUDE=' + str(flex_include),
        '-DBISON_EXECUTABLE=' + str(Path(shutil.which(args.bison) or args.bison).resolve()),
        '-DENGINE_REFERENCE_VECTOR_FIR=' + ('OFF' if args.scalar_fir else 'ON')], check=True)
    subprocess.run(['cmake', '--build', str(output / 'CMake'), '--parallel', '1'], check=True)
    # Replacing the inode avoids stale macOS code-signature pages on rebuild.
    staged_binary = output / 'RenderReference.staged'
    shutil.copy2(output / 'CMake/RenderReference', staged_binary)
    staged_binary.replace(output / 'RenderReference')
    runtime = output / 'Runtime'
    (runtime / 'engines/chevrolet').mkdir(parents=True, exist_ok=True)
    shutil.copytree(snapshot / 'es', runtime / 'es', dirs_exist_ok=True)
    shutil.copytree(snapshot / 'assets/engines', runtime / 'engines', dirs_exist_ok=True)
    shutil.copytree(tools / 'Profiles', runtime / 'engines/local', dirs_exist_ok=True)
    shutil.copy2(snapshot / 'LICENSE', runtime / 'LICENSE.engine-sim')
    (runtime / 'Profile454.mr').write_text('import "engine_sim.mr"\nimport "engines/chevrolet/engine_03_for_e1.mr"\nset_engine(engine_03_for_e1())\n')
    impulse = snapshot / 'assets/sound-library/smooth/smooth_39.wav'
    with wave.open(str(impulse), 'rb') as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, 44100):
            raise RuntimeError('Format IR inattendu')
        (runtime / 'Impulse.pcm').write_bytes(stream.readframes(stream.getnframes()))
    for profile in profiles:
        (runtime / ('Profile-' + profile['key'] + '.mr')).write_text('import "engine_sim.mr"\nimport "engines/' + profile['path'] + '"\nset_engine(' + profile['node'] + '())\n')
        with wave.open(str(snapshot / 'assets/sound-library' / profile['impulse']), 'rb') as stream:
            assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (1, 2, 44100)
            pcm = stream.readframes(stream.getnframes())
            pcm = Impulse.prepare(pcm, profile.get('treble_db', 0), profile.get('tail_ms', 0), profile.get('bass_db', 0),
                profile.get('mid_decay_ms', 0), profile.get('high_decay_ms', 0))
            (runtime / ('Impulse-' + profile['key'] + '.pcm')).write_bytes(pcm)
    metadata = {'repository': 'https://github.com/ange-yaghi/engine-sim', 'revision': REVISION,
        'dependencies': DEPENDENCIES, 'profiles': profiles,
        'local_profiles_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((tools / 'Profiles').glob('*.mr'))},
        'catalog_sha256': hashlib.sha256((tools / 'Profiles.json').read_bytes()).hexdigest(), 'profile': 'assets/engines/chevrolet/engine_03_for_e1.mr',
        'features': ['gearing-v1'], 'sample_rate': 44100, 'vector_fir': not args.scalar_fir,
        'binary_sha256': hashlib.sha256((output / 'RenderReference').read_bytes()).hexdigest(),
        'impulse_sha256': hashlib.sha256(impulse.read_bytes()).hexdigest()}
    (output / 'Provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    PackageLibrary.stage(output, output)
    print('Bibliothèque de moteurs prête :', output)


if __name__ == '__main__':
    main()
