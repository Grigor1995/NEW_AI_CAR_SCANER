"""Structural checks supplement runtime C++ tests; they do not certify hardware."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[2]
checks=[]
def check(name,condition):
    if not condition: raise AssertionError(name)
    checks.append(name)

check('no_legacy_desktop_application',not (root/'finalbuild').exists() and not (root/'services/platform_engine/apps').exists())
check('no_cicd_workflows',not (root/'.github/workflows').exists())
for folder in ['protocols','security','telemetry','ai','interfaces']:
    for p in (root/'core'/folder).rglob('*'):
        if p.suffix in ('.hpp','.cpp'):
            check('domain_no_qt_'+p.name,not re.search(r'#include\s*[<"]Q[A-Z]',p.read_text()))
translations={}
for language in ['en','hy','ru','fr']:
    tree=ET.parse(root/f'ui/translations/cda_{language}.ts')
    entries={}
    for context in tree.findall('context'):
        for message in context.findall('message'):
            text=message.findtext('translation');node=message.find('translation')
            check('translation_'+language+'_'+context.findtext('name')+'_'+message.findtext('source'),bool(text) and node.get('type') not in ('unfinished','vanished'))
            entries[(context.findtext('name'),message.findtext('source'))]=text
    translations[language]=set(entries)
check('locale_source_parity',all(s==translations['en'] for s in translations.values()))
check('exactly_four_locales',len(list((root/'ui/translations').glob('*.ts')))==4)
payment_files=list((root/'future_modules/payments').rglob('*'))
check('payments_documentation_only',all(p.suffix=='.md' for p in payment_files if p.is_file()))
check('canonical_icon_no_text',not ET.parse(root/'assets/app_icon/canonical.svg').findall('.//{http://www.w3.org/2000/svg}text'))
check('icon_artifacts',all((root/p).is_file() for p in ['assets/app_icon/windows.ico','apps/android/res/mipmap-anydpi-v26/ic_launcher.xml','apps/ios/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png']))
check('openapi_matches_implemented_routes',len(json.loads((root/'docs/api/openapi.json').read_text())['paths'])==8)
print(json.dumps({'status':'PASS','checks':len(checks),'translation_messages':len(translations['en'])},indent=2))
