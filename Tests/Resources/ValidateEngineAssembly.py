"""Check prepared engine-part DSP allocations on macOS ARM64."""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess

fixture = Path(__file__).resolve().parent
workspace = fixture.parents[3]
if Path.cwd().resolve() != workspace:
    raise SystemExit('Run from the workspace or owning Spec Worktree group')
if platform.system() != 'Darwin' or platform.machine() != 'arm64':
    raise SystemExit('This counter is qualified only for macOS ARM64')
compiler = Path(os.environ.get('SILEX_EXECUTABLE', shutil.which('silex') or 'silex')).resolve()
cache = workspace / '.silex'
library = cache / 'engine-assembly-heap-probe.dylib'
subprocess.run(['clang', '-dynamiclib', '-arch', 'arm64', '-O2', '-fno-builtin',
    '-Wall', '-Wextra', '-Werror', str(fixture / 'HeapProbe.c'), '-o', str(library)], check=True)
pattern = re.compile(r'AUDIO_HEAP allocations=(\d+) bytes=(\d+) copies=(\d+) copy_bytes=(\d+)')
report = dict(host=platform.platform(), target='macos-arm64',
    compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),
    scope='Marked application thread: prepared engine-part DSP and transitions; excludes Audio.write, SDL and UI', modes={})
for mode in ['debug', 'release']:
    binary = cache / ('engine-assembly-heap-' + mode)
    subprocess.run([str(compiler), 'compile', str(fixture / 'EngineAssemblyHeap.sx'),
        '--' + mode, '-o', str(binary)], cwd=workspace, check=True, timeout=180)
    run = subprocess.run([str(binary)], cwd=workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=dict(os.environ, DYLD_INSERT_LIBRARIES=str(library)), timeout=90)
    text = run.stdout
    (cache / ('engine-assembly-heap-' + mode + '.log')).write_text(text)
    run.check_returncode()
    rows, label = [], ''
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        if match:
            rows.append(dict(phase=label, **dict(zip(['allocations', 'bytes', 'copies', 'copy_bytes'], map(int, match.groups())))))
        else:
            label = line
    assert len(rows) == 8, rows
    assert rows[0]['allocations'] == 0 and rows[1]['allocations'] > 0, 'Invalid counter controls'
    assert rows[2]['allocations'] > 0 and rows[5]['allocations'] > 0, 'Preparation must be counted'
    for index in [3, 4, 6, 7]:
        assert rows[index]['allocations'] == 0, rows[index]
    report['modes'][mode] = dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), phases=rows)
    print(mode + ': prepared render, controls, part crossfade and reset allocation-free', flush=True)
(cache / 'engine-assembly-resource-validation.json').write_text(json.dumps(report, indent=2) + '\n')
