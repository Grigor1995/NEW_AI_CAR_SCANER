# Canonical application icon

assets/app_icon/canonical.svg is editable, text-free, symmetric car-front line art with circuit/OBD pins and a waveform. It uses a #070D18 rounded square with #00BFFF/#29DFFF/#126EFF accents, with no manufacturer logo. All raster packages derive from this artwork.

The compiled client --generate-icons option renders PNGs with QtSvg. scripts/package/icons.py produces multi-resolution Windows ICO, Android adaptive VectorDrawable and density raster icons, plus an opaque 1024px iOS asset catalog. Qt is the SVG renderer; Pillow is only an asset tool. No native package build or app-store acceptance is inferred from generated icon files. iOS catalog attachment/signing remains a platform release step.
