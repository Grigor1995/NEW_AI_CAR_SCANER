"""Compare original statistics with compiled packed ABI including Python marshalling."""
import argparse
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from uuid import uuid4

root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'services/platform_engine'),str(root/'services/platform_engine/backend')]
from native_acceleration import fast_stats
from telemetry.analysis import compute_stats
from telemetry.models import TelemetrySample

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path)
args=parser.parse_args()
rng=random.Random(17);sid=uuid4();results=[]
for count in (100,5000,50000):
 samples=[TelemetrySample(session_id=sid,pid='rpm',timestamp_ms=rng.randrange(10000000),value=rng.uniform(600,6000)) for _ in range(count)]
 row={'samples':count}
 for name,fn in [('python',compute_stats),('cpp_packed',fast_stats)]:
  fn(sid,'rpm',samples)
  timings=[]
  for _ in range(7):
   start=time.perf_counter();fn(sid,'rpm',samples);timings.append((time.perf_counter()-start)*1000)
  row[name+'_median_ms']=statistics.median(timings)
 row['speedup']=row['python_median_ms']/row['cpp_packed_median_ms'];results.append(row)
report={'platform':platform.platform(),'python':platform.python_version(),'repetitions':7,'includes_marshalling':True,'results':results}
if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
