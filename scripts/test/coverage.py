"""Collect GCC JSON line/branch coverage for pure domain code; keep Qt separate."""
from pathlib import Path
import gzip
import json
import subprocess
ROOT=Path(__file__).resolve().parents[2]
output=ROOT/'artifacts/coverage'
output.mkdir(parents=True,exist_ok=True)
for obj in (ROOT/'build/coverage/CMakeFiles').rglob('*.gcda'):
    subprocess.run(['gcov','--json-format','--branch-probabilities','--branch-counts','-o',str(obj),str(obj)],cwd=output,check=True,stdout=subprocess.DEVNULL)
records={}
for archive in output.glob('*.gcov.json.gz'):
    data=json.loads(gzip.decompress(archive.read_bytes()))
    for f in data['files']:
        path=Path(f['file'])
        if not path.is_absolute():path=Path(data['current_working_directory'])/path
        path=path.resolve()
        if not path.is_relative_to(ROOT):continue
        rel=path.relative_to(ROOT).as_posix()
        if not (rel.startswith('core/') or rel in ['services/updates/manifest.hpp','services/monitoring/eligibility.hpp']):continue
        if not f['lines']:continue
        lines=records.setdefault(rel,{})
        for line in f['lines']:
            target=lines.setdefault(line['line_number'],{'count':0,'branches':[]})
            target['count']+=line['count'];target['branches']+=line.get('branches',[])
files={}
for name,lines in records.items():
    covered=sum(v['count']>0 for v in lines.values())
    branches=[b for l in lines.values() for b in l['branches']]
    files[name]={'lines':len(lines),'covered':covered,'line_percent':round(covered/len(lines)*100,2),'branches':len(branches),'branches_taken':sum(b['count']>0 for b in branches)}
total=sum(v['lines'] for v in files.values());covered=sum(v['covered'] for v in files.values())
if not total:raise RuntimeError('No current GCC domain coverage was collected')
result={'scope':'pure C++ domain only; excludes Qt services/UI/HTTP','files':files,'lines':total,'covered':covered,'line_percent':round(covered/total*100,2)}
print(json.dumps(result,indent=2))
(output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
