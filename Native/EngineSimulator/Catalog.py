"""Keep the Silex projection aligned with the native profile catalogue."""
import argparse,json
from pathlib import Path
root=Path(__file__).resolve().parent
path=root.parents[1]/'Module/Engines/@Profiles.sx'
def generated():
    rows=json.loads((root/'Profiles.json').read_text())['profiles']
    source=path.read_text().split('func engine_profiles()')[0]+'func engine_profiles() Profile[] {\n    return [\n'
    for index,row in enumerate(rows):
        source+=f'        Profile(key:{json.dumps(row["key"])}, label:{json.dumps(row["label"],ensure_ascii=False)}, redline:{row["redline"]}.0, ceiling:{row["ceiling"]}.0, idle:{row["idle"]}.0, strokes:{row["strokes"]}, gears:{len(row["ratios"])}, gearing:Gearing(ratios:{json.dumps(row["ratios"])}, final_drive:{row["diff"]}), intake:{row["breath_percent"]/100}, slot:{index})'+(',' if index<len(rows)-1 else '')+'\n'
    return source+'    ]\n}\n'
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    expected=generated()
    if args.check:
        assert path.read_text()==expected,'Profile projection differs; run Catalog.py'
        print('Engine profile projection matches the catalogue')
    else:path.write_text(expected)
