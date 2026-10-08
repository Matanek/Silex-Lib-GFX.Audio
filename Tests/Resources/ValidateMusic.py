"""Private macOS ARM64 allocation gate for musical authoring and owned MIDI feeding."""
from pathlib import Path
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile

fixture = Path(__file__).resolve().parent
owner = fixture.parents[1]
workspace = owner.parents[1]
if Path.cwd().resolve() != workspace:
    raise SystemExit('Run from SilexProject or the Spec Worktree group root')
if platform.system() != 'Darwin' or platform.machine() != 'arm64':
    raise SystemExit('The positive allocation control covers macOS ARM64 only')
cache = workspace / '.silex'
compiler = Path(os.environ.get('SILEX_EXECUTABLE', workspace/'Silex/Toolchain/zig-out/bin/silex'))
environment = dict(os.environ, SDL_AUDIODRIVER='dummy', SDL_VIDEODRIVER='dummy',
                   ZIG_GLOBAL_CACHE_DIR=str(cache/'zig-global'), ZIG_LOCAL_CACHE_DIR=str(cache/'zig-local'))
library = cache/'audio-heap-probe.dylib'
subprocess.run(['clang','-dynamiclib','-arch','arm64','-arch','x86_64','-O2','-fno-builtin',
                '-Wall','-Wextra','-Werror',str(fixture/'HeapProbe.c'),'-o',str(library)],check=True)
pattern = re.compile(r'AUDIO_HEAP allocations=(\d+) bytes=(\d+) copies=(\d+) copy_bytes=(\d+)')
def execute(entry, mode, label):
    binary = cache/f'{label}-{mode}'
    subprocess.run([str(compiler),'compile',str(entry),f'--{mode}','--nocache','-o',str(binary)],
                   cwd=workspace,env=environment,check=True,timeout=120)
    result = subprocess.run([str(binary)],cwd=workspace,env=dict(environment,DYLD_INSERT_LIBRARIES=str(library)),
                            text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (cache/f'{label}-{mode}.log').write_text(result.stdout)
    result.check_returncode()
    rows=[]; phase=''
    for line in result.stdout.splitlines():
        match=pattern.fullmatch(line)
        if match: rows.append(dict(phase=phase,**dict(zip(['allocations','bytes','copies','copy_bytes'],map(int,match.groups())))))
        else: phase=line
    assert rows[0]['phase']=='empty' and all(rows[0][key]==0 for key in ['allocations','bytes','copies','copy_bytes'])
    assert rows[1]['phase']=='positive allocation' and rows[1]['allocations']>0
    return rows
report=dict(host=platform.platform(),target='macos-arm64',compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),
            audio_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=owner,text=True).strip(),modes={})
for mode in ['debug','release']:
    rows=execute(fixture/'MusicHeap.sx',mode,'music-resources')
    dsp=[row for row in rows if row['phase']=='DSP block']
    assert len(dsp)>=100 and all(row['allocations']==0 and row['copies']==0 for row in dsp),dsp
    assert any(row['copies']>0 for row in rows),'Missing positive copy control'
    assert len(rows)==116, len(rows)
    report['modes'][mode]=dict(public_path=rows)
    print(f'{mode}: public preparation/trigger/feed measured; instrument DSP allocation-free',flush=True)

# A disposable copy retains the exact candidate Module sources except three mechanical markers.
# It supplies a test-only System boundary. The owner and installed provider are never edited.
original=(owner/'Module/Music/Recipe.sx').read_text()
marked='use Interop.C\nuse Interop.Boundary\nlet resource_phase = C.function<func() int32>(library:Boundary.System,name:"getppid")\n'+original
for start,end,label in [('    func send(', '    func render(', 'recipe commands'),('    func render(', '    func reset()', 'recipe block')]:
    first=marked.index(start);last=marked.index(end,first)
    body=marked[first:last]
    if label=='recipe commands':body=body.replace('        match command {','        print("recipe commands"); resource_phase()\n        match command {',1)
    else:body=body.replace('        var start = 0','        print("recipe block"); resource_phase()\n        var start = 0',1)
    point=body.rindex('        return Result<void, Error>.success()')
    body=body[:point]+'        resource_phase()\n'+body[point:]
    marked=marked[:first]+body+marked[last:]
marked=marked.replace('    func reset() { for var voice in self.voices { voice.reset() } self.serial = 0 }',
    '    func reset() { print("recipe reset"); resource_phase(); for var voice in self.voices { voice.reset() } self.serial = 0; resource_phase() }')
report['recipe_original_sha256']=hashlib.sha256(original.encode()).hexdigest()
report['recipe_instrumented_sha256']=hashlib.sha256(marked.encode()).hexdigest()
link=workspace/'.silex/links/GFX.Audio.json'
before=json.loads(link.read_text())
assert Path(before['path']).resolve()==owner.resolve(),before
with tempfile.TemporaryDirectory(prefix='music-dsp-owner-',dir=cache) as temporary:
    copied=Path(temporary)
    shutil.copytree(owner/'Module',copied/'Module')
    (copied/'Boundary').symlink_to(owner/'Boundary',target_is_directory=True)
    manifest=json.loads((owner/'Package.json').read_text())
    for target in ['macos-arm64','macos-x64']:
        manifest['boundary'][target]['providers']['System']={'libraries':['System']}
    (copied/'Package.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (copied/'Module/Music/Recipe.sx').write_text(marked)
    try:
        subprocess.run([str(compiler),'link',str(copied),'--workspace',str(workspace)],cwd=workspace,env=environment,check=True)
        for mode in ['debug','release']:
            rows=execute(fixture/'RecipeHeap.sx',mode,'recipe-resources')
            measured=[row for row in rows if row['phase'].startswith('recipe ')]
            assert sum(row['phase']=='recipe block' for row in measured)>=100
            assert sum(row['phase']=='recipe commands' for row in measured)>=16
            assert any(row['phase']=='recipe reset' for row in measured)
            assert all(row['allocations']==0 and row['copies']==0 for row in measured),measured
            report['modes'][mode]['recipe_dsp']=rows
            print(f'{mode}: actual recipe rendering/commands/reset allocation-free in instrumented copy',flush=True)
    finally:
        subprocess.run([str(compiler),'link',str(owner),'--workspace',str(workspace)],cwd=workspace,env=environment,check=True)
assert (owner/'Module/Music/Recipe.sx').read_text()==original
assert json.loads(link.read_text())==before
report['module_sha256']={str(p.relative_to(owner)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((owner/'Module').rglob('*.sx'))}
report['binary_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for label in ['music-resources','recipe-resources'] for mode in ['debug','release'] for p in [cache/f'{label}-{mode}']}
(cache/'music-resource-validation.json').write_text(json.dumps(report,indent=2)+'\n')
