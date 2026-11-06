#!/usr/bin/env python3
"""Build a private copy of alot at /stream/ matching the alot folder, with all music coming from R2.

  python3 -I ektoplazm_stream_preview.py     then open http://127.0.0.1:8765/stream/?lang=en
"""
import os, shutil
OUT = os.path.expanduser('~/music-pipeline/ektoplazm/preview/stream')
ALOT = os.path.expanduser('~/Documents/_bench-src/alot')
os.makedirs(os.path.join(OUT, 'tracks'), exist_ok=True)
for name in ['index.html', 'icon.png', 'credits.html', 'tracks/manifest.json', 'tracks/modes.json']:
    shutil.copy2(os.path.join(ALOT, name), os.path.join(OUT, name))
print('stream copy refreshed')
