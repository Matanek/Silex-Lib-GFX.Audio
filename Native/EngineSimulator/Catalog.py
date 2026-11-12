"""Keep the Silex projection aligned with the native profile catalogue."""
import argparse,json
from pathlib import Path
root=Path(__file__).resolve().parent
path=root.parents[1]/'Module/Engines/@Profiles.sx'
def generated():
    data=json.loads((root/'Profiles.json').read_text())
    rows=data['profiles']
    source=path.read_text().split('func engine_profiles()')[0]+'func engine_profiles() Profile[] {\n    return [\n'
    for index,row in enumerate(rows):
        source+=f'        Profile(key:{json.dumps(row["key"])}, label:{json.dumps(row["label"],ensure_ascii=False)}, redline:{row["redline"]}.0, ceiling:{row["ceiling"]}.0, idle:{row["idle"]}.0, strokes:{row["strokes"]}, gears:{len(row["ratios"])}, gearing:Gearing(ratios:{json.dumps(row["ratios"])}, final_drive:{row["diff"]}), intake:{row["breath_percent"]/100}, slot:{index})'+(',' if index<len(rows)-1 else '')+'\n'
    source += '    ]\n}\n\nmodule func bench_gearing(key:str) Gearing? {\n'
    for row in data['bench_vehicles']:
        ratios = json.dumps(row['ratios'])
        source += f'    if key == {json.dumps(row["key"])} {{ return Gearing(ratios:{ratios}, final_drive:{row["diff"]}) }}\n'
    return source + '    return null\n}\n'


def native_header(data):
    source = '#pragma once\n#include <Drive.hpp>\n#include <string_view>\ninline DriveSettings profileSettings(int index) {\n    switch (index) {\n'
    for index, profile in enumerate(data['profiles']):
        fields = ('idle', 'mass', 'area', 'drag', 'diff', 'wheel', 'shift', 'starter', 'strokes', 'audio_cutoff')
        values = ', '.join(str(profile[field]) for field in fields)
        ratios = ', '.join(str(value) for value in profile['ratios'])
        source += f'        case {index}: return {{{values}, {{{ratios}}}}};\n'
    source += '        default: throw std::runtime_error("Unknown profile");\n    }\n}\n\n'
    source += 'inline bool configureBenchVehicle(std::string_view key, DriveSettings& settings) {\n'
    for row in data['bench_vehicles']:
        source += f'    if (key == {json.dumps(row["key"])}) {{\n'
        for field in ('mass', 'area', 'drag', 'diff', 'wheel', 'shift'):
            source += f'        settings.{field} = {row[field]};\n'
        ratios = ', '.join(str(value) for value in row['ratios'])
        source += f'        settings.ratios = {{{ratios}}};\n        return true;\n    }}\n'
    return source + '    return false;\n}\n'

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    expected=generated()
    if args.check:
        assert path.read_text()==expected,'Profile projection differs; run Catalog.py'
        print('Engine profile projection matches the catalogue')
    else:path.write_text(expected)
