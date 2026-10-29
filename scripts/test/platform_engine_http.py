"""Exercise migrated source APIs against a running local companion."""
import argparse
import json
import re
from pathlib import Path
from uuid import uuid4
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=8001)
parser.add_argument('--output',type=Path)
args=parser.parse_args()
checks=[]
with httpx.Client(base_url=f'http://127.0.0.1:{args.port}',timeout=30) as client:
 def request(method,path,body=None,expected=200):
  response=client.request(method,path,json=body)
  assert response.status_code==expected,(path,response.status_code,response.text)
  checks.append({'method':method,'path':path,'status':response.status_code})
  return response
 runtime=request('GET','/api/v1/migration/runtime').json()
 assert runtime['native']['available']
 schema=request('GET','/openapi.json').json()
 inventory=json.loads((Path(__file__).resolve().parents[2]/'docs/migration/source-inventory.json').read_text())
 for op in inventory['routes']:
  path=re.sub(r'\{([^}:]+):[^}]+\}', r'{\1}', op['path'])
  assert path in schema['paths'] and op['method'].lower() in schema['paths'][path],op
 checks.append({'check':'all_source_operations_registered','count':len(inventory['routes'])})
 s=request('POST','/api/v1/sessions',{}).json()['session_id']
 root='/api/v1/sessions/'+s
 request('POST',root+'/symptoms',{'raw_text':'Cylinder misfire on LPG, normal on petrol'})
 request('POST',root+'/dtcs',{'code':'P0302','source':'USER_REPORTED'})
 analysis=request('POST','/api/v1/intelligence/sessions/'+s+'/analyze',{}).json()
 assert analysis['hypotheses'] and analysis['recommendations']
 request('GET','/api/v1/decision/sessions/'+s+'/plan')
 request('POST','/api/v1/ai/sessions/'+s+'/context',{})
 doc='http-contract-'+str(uuid4())
 request('POST','/api/v1/ai/knowledge',{'document_id':doc,'title':'Misfire reference','text':'LPG misfire fuel trim comparison','metadata':{'source':'test fixture'}})
 assert request('POST','/api/v1/ai/knowledge/search',{'query':'LPG misfire','top_k':5}).json()
 samples=[{'session_id':s,'pid':'rpm','timestamp_ms':1000+i*1000,'value':800+i*200,'unit':'rpm','source':'TEST_FIXTURE','quality':'GOOD'} for i in range(3)]
 request('POST','/api/v1/telemetry/sessions/'+s+'/samples',{'samples':samples})
 summary=request('GET','/api/v1/telemetry/sessions/'+s+'/summary').json()
 assert summary['sample_count']==3 and summary['stats'][0]['mean']==1000
 request('POST','/api/v1/telemetry/sessions/'+s+'/analyze',{})
 request('POST','/api/v1/network-discovery/sessions/'+s+'/frames',{'bus':'CAN0','frames':[{'arbitration_id':2024,'data_hex':'03410C1AF8','is_extended':False}]})
 request('GET','/api/v1/network-discovery/sessions/'+s+'/map')
 vehicles=request('GET','/api/v1/vehicle-reference').json()['vehicles'];assert len(vehicles)==70
 request('GET','/api/v1/vehicle-reference/'+vehicles[0]['id']+'/image')
 request('POST','/api/v1/obd/j1939/decode',{'arbitration_id':0x18FECA00,'data':'000001000001FFFF'})
 report=request('GET',root+'/report').json();assert 'session_id' not in report
 pdf=request('GET',root+'/report?format=pdf');assert pdf.content.startswith(b'%PDF-')
 request('GET',root)
result={'status':'PASS','checks':checks,'session_id':s,'physical_hardware_tested':False}
if args.output:
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'PASS','checks':len(checks),'source_operations':len(inventory['routes'])}))
