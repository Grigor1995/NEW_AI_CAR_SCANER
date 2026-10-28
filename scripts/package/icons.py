"""Package one canonical SVG's Qt-rendered PNGs for native platforms. Requires Pillow."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from PIL import Image

root = Path(__file__).resolve().parents[2]
assets = root / 'assets/app_icon'
image = Image.open(assets / 'previews/icon-1024.png').convert('RGBA')
image.save(assets / 'windows.ico', sizes=[(s,s) for s in (16,24,32,48,64,128,256)])
ios = root / 'apps/ios/Assets.xcassets/AppIcon.appiconset'
ios.mkdir(parents=True, exist_ok=True)
image.convert('RGB').save(ios / 'AppIcon-1024.png')
(ios / 'Contents.json').write_text(json.dumps({'images':[{'filename':'AppIcon-1024.png','idiom':'universal','platform':'ios','size':'1024x1024'}],'info':{'author':'CDA','version':1}},indent=2)+'\n')
android = root / 'apps/android/res'
for density, size in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
    path = android / ('mipmap-'+density)
    path.mkdir(parents=True, exist_ok=True)
    image.resize((size,size),Image.Resampling.LANCZOS).save(path/'ic_launcher.png')
# The same canonical path geometry is converted to a foreground VectorDrawable.
svg = ET.parse(assets/'canonical.svg').getroot()
ns={'svg':'http://www.w3.org/2000/svg'}
paths=[]
for path in svg.findall('.//svg:g/svg:path',ns):
    paths.append(f'<path android:pathData="{path.attrib["d"]}" android:fillColor="#00000000" android:strokeColor="#00BFFF" android:strokeWidth="5" android:strokeLineCap="round" android:strokeLineJoin="round"/>')
for circle in svg.findall('.//svg:g/svg:circle',ns):
    x=float(circle.attrib['cx']);y=float(circle.attrib['cy']);r=float(circle.attrib['r'])
    paths.append(f'<path android:pathData="M{x-r},{y}a{r},{r} 0 1,0 {r*2},0a{r},{r} 0 1,0 -{r*2},0" android:fillColor="#29DFFF"/>')
(android/'drawable').mkdir(parents=True,exist_ok=True)
(android/'drawable/ic_launcher_foreground.xml').write_text('<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="256" android:viewportHeight="256"><group android:scaleX="0.66" android:scaleY="0.66" android:translateX="43.52" android:translateY="43.52">'+''.join(paths)+'</group></vector>\n')
(android/'values').mkdir(exist_ok=True)
(android/'values/colors.xml').write_text('<resources><color name="ic_launcher_background">#070D18</color></resources>\n')
(android/'mipmap-anydpi-v26').mkdir(exist_ok=True)
(android/'mipmap-anydpi-v26/ic_launcher.xml').write_text('<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@color/ic_launcher_background"/><foreground android:drawable="@drawable/ic_launcher_foreground"/></adaptive-icon>\n')
print('Generated Windows ICO, Android adaptive/legacy icons and iOS AppIcon from canonical artwork')
