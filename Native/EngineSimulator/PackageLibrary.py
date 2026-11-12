"""Stage the validated renderer and its resources as an independently deployable bank."""
import argparse, hashlib, json, platform, shutil
from pathlib import Path

def stage(source, output):
    source,output=Path(source).resolve(),Path(output).resolve()
    expected=json.loads((source/'Provenance.json').read_text())
    marker='silex-engine-library-v2\n' if 'gearing-v1' in expected.get('features',[]) else 'silex-engine-library-v1\n'
    if 'following-v1' in expected.get('features',[]):marker='silex-engine-library-v3\n'
    combustion = 'combustion-v1' in expected.get('features', [])
    features = expected.get('features', [])
    bench = next((version for version in ('bench-transmission-v2', 'bench-transmission-v1') if version in features), None)
    if source==output:
        (output/'EngineLibrary.txt').write_text(marker)
        if combustion: (output/'CombustionTelemetry.txt').write_text('combustion-v1\n')
        if bench: (output/'BenchTransmission.txt').write_text(bench + '\n')
        return
    if output.exists():
        raise SystemExit('Refusing to overwrite an engine library: '+str(output))
    binary=source/'RenderReference'
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=expected['binary_sha256']:
        raise SystemExit('Renderer does not match its provenance')
    output.mkdir(parents=True)
    shutil.copy2(binary,output/'RenderReference')
    for path in (source/'Runtime').rglob('*'):
        if path.is_file() and (path.suffix in ('.mr','.pcm') or path.name.startswith('LICENSE')):
            destination=output/'Runtime'/path.relative_to(source/'Runtime')
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    shutil.copy2(source/'Provenance.json',output/'Provenance.json')
    (output/'EngineLibrary.txt').write_text(marker)
    if combustion: (output/'CombustionTelemetry.txt').write_text('combustion-v1\n')
    if bench: (output/'BenchTransmission.txt').write_text(bench + '\n')
    files={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'Library-Manifest.json').write_text(json.dumps(dict(schema=1,host=platform.platform(),files=files),indent=2)+'\n')
    print('Engine library:',output)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-build',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    options=parser.parse_args();stage(options.from_build,options.output)
