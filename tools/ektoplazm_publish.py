#!/usr/bin/env python3
"""Write alot's track list (pointing at our R2 storage) and its music credits page into the alot source folder.

  python3 -I ektoplazm_publish.py

Never deploys. Publishing stays a separate step behind gate.py. Keeps any weights and removals the ratings tool made.
"""
import html, json, os
ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
ALOT = os.environ.get('ALOT_DIR') or os.path.expanduser('~/Documents/_bench-src/alot')
PUBLIC = 'https://pub-dfe2dc87a34d4016a8782237145e0938.r2.dev'
LICENSES = {'by-nc-sa/4.0': ('CC BY-NC-SA 4.0', 'https://creativecommons.org/licenses/by-nc-sa/4.0/'),
            'by/4.0': ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/')}
source = json.load(open(os.path.join(ROOT, 'preview/tracks/manifest.json'), encoding='utf-8'))['tracks']
releases = {r['slug']: r for r in json.load(open(os.path.join(ROOT, 'releases.json'), encoding='utf-8'))}
live_path = os.path.join(ALOT, 'tracks/manifest.json')
live = {}
ratings_path = os.path.join(ROOT, 'ratings-applied.json')
applied = json.load(open(ratings_path, encoding='utf-8')) if os.path.exists(ratings_path) else {'removed': [], 'weights': {}}
out, by_release = [], {}
for t in source:
    if t['id'] in applied['removed']:
        continue
    row = {k: t[k] for k in ['id', 'name', 'style', 'bpm', 'duration', 'size']}
    row['file'] = f"{PUBLIC}/{t['file']}"
    row['weight'] = applied['weights'].get(t['id'], 1)
    row['album'] = f"{releases[t['release']]['artist']}: {releases[t['release']]['album']}"
    out.append(row)
    by_release.setdefault(t['release'], []).append(t['name'])
os.makedirs(os.path.dirname(live_path), exist_ok=True)
json.dump({'tracks': out}, open(live_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
e = html.escape
sections = []
for slug, names in by_release.items():
    r = releases[slug]
    licenses = [LICENSES[x] for x in r['licenses_on_page']]
    items = ''.join(f'<li>{e(n)}</li>' for n in names)
    links = ', '.join(f'<a href="{u}" rel="license noopener" target="_blank">{e(n)}</a>' for n, u in licenses)
    sections.append(f'<section><h2>{e(r["artist"])}: {e(r["album"])} ({e(str(r.get("year")))})</h2>'
                    f'<p>{links} · <a href="{e(r["page"])}" rel="noopener" target="_blank">Ektoplazm</a></p><ul>{items}</ul></section>')
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>alot: music credits</title>
<style>
:root {{ color-scheme: dark; }}
body {{ margin: 0 auto; max-width: 640px; padding: 40px 16px 64px; background: #0e0b09; color: #f3e9dc; font: 16px/1.6 ui-serif, Georgia, 'Iowan Old Style', serif; }}
h1 {{ font-weight: 400; font-size: 34px; margin: 0 0 8px; }} h2 {{ font-weight: 400; font-size: 20px; margin: 32px 0 4px; }}
p {{ margin: 4px 0; color: #cdbfae; }} a {{ color: #f0c48c; }} ul {{ margin: 8px 0 0; padding-left: 20px; color: #cdbfae; }}
.es {{ margin-top: 2px; }}
</style></head><body>
<p><a href="./">alot</a></p>
<h1>Music credits</h1>
<p>Free for non-commercial use. Loudness adjusted for this app.</p>
<p class="es" lang="es">Uso libre no comercial. Volumen ajustado para esta app.</p>
{''.join(sections)}
</body></html>
'''
open(os.path.join(ALOT, 'credits.html'), 'w', encoding='utf-8').write(page)
print(len(out), 'tracks in the list;', len(by_release), 'releases credited')
