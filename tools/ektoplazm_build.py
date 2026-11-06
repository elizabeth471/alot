#!/usr/bin/env python3
"""Turn the downloaded Ektoplazm releases into a private preview copy of alot.

  python3 -I ektoplazm_build.py            encode the tracks and build the preview
  python3 -I ektoplazm_build.py --site     only refresh the preview's copy of alot's page

Originals stay untouched. Tracks are evened out to the same loudness so they sit
consistently against the noise. The real alot folder is only read, never written.
Nothing here publishes anything.
"""
import concurrent.futures, json, os, re, shutil, subprocess, sys, unicodedata

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
PREVIEW = os.path.join(ROOT, 'preview')
TRACKS = os.path.join(PREVIEW, 'tracks')
ALOT = os.path.expanduser('~/Documents/_bench-src/alot')
TARGET_LUFS, TRUE_PEAK, RANGE = -16.0, -1.5, 11
AMBIENT = {'huuhaa-frostient', 'saluberrimae-time-is-a-flat-circle', 'ajnia-oasis', 'ajnia-elements', 'shinjibomb-shinjibomb'}

def slugify(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:format_tags=artist,title',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)['format']
    tags = {k.lower(): v for k, v in data.get('tags', {}).items()}
    return float(data['duration']), tags.get('artist', ''), tags.get('title', '')

def encode(job):
    source, out = job
    if os.path.exists(out):
        return None  # already encoded
    first = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-i', source, '-af',
                            f'loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={RANGE}:print_format=json',
                            '-f', 'null', '-'], capture_output=True, text=True, check=True).stderr
    m = json.loads(first[first.rindex('{'):first.rindex('}') + 1])
    gain = (f'loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={RANGE}:linear=true:measured_I={m["input_i"]}:'
            f'measured_TP={m["input_tp"]}:measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:'
            f'offset={m["target_offset"]}')
    subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', source, '-vn', '-map_metadata', '-1', '-af', gain,
                    '-ar', '44100', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    return float(m['input_i'])

def copy_site():
    os.makedirs(TRACKS, exist_ok=True)
    for name in ['index.html', 'icon.png']:
        shutil.copy2(os.path.join(ALOT, name), os.path.join(PREVIEW, name))

def build():
    copy_site()
    releases = json.load(open(os.path.join(ROOT, 'releases.json'), encoding='utf-8'))
    entries, jobs, credits = [], [], []
    old = {}
    if os.path.exists(os.path.join(TRACKS, 'manifest.json')):
        old = {t['id']: t for t in json.load(open(os.path.join(TRACKS, 'manifest.json'), encoding='utf-8'))['tracks']}
    for release in releases:
        if release.get('status') != 'ok':
            credits.append(f'- NOT INCLUDED: {release["slug"]} ({release.get("status")})')
            continue
        license_text = ', '.join('CC ' + x.upper() for x in release['licenses_on_page'])
        note = ''
        if release['noncommercial_wording_on_page'] and not any('nc' in x for x in release['licenses_on_page']):
            note = ' Page wording also says noncommercial, which does not match the linked license: treat as noncommercial.'
        credits.append(f'\n## {release["artist"]}: {release["album"]} ({release.get("year")})\n'
                       f'- Source: {release["page"]}\n- License on page: {license_text}.{note}\n- Retrieved: {release["retrieved"]}\n- Tracks:')
        for name in release['tracks']:
            source = os.path.join(ROOT, 'originals', release['slug'], 'mp3', name)
            seconds, artist, title = probe(source)
            title = title or re.sub(r'^\d+\s*[-.]?\s*', '', os.path.splitext(name)[0])
            artist = artist or release['artist']
            track_id = slugify(f'{release["slug"]}-{title}')[:90].rstrip('-')
            out = os.path.join(TRACKS, track_id + '.m4a')
            jobs.append((source, out))
            entries.append({'id': track_id, 'name': f'{artist} – {title}',
                            'style': 'ambient' if release['slug'] in AMBIENT else 'electronic',
                            'bpm': release.get('bpm') or 80, 'file': f'tracks/{track_id}.m4a',
                            'duration': round(seconds, 2), 'size': 0, 'release': release['slug'],
                            'license': license_text})
            credits.append(f'  - {artist} – {title}')
    if len({e['id'] for e in entries}) != len(entries):
        sys.exit('two tracks would share a file name')
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        loudness = list(pool.map(encode, jobs))
    for entry, level in zip(entries, loudness):
        entry['size'] = os.path.getsize(os.path.join(PREVIEW, entry['file']))
        entry['source_lufs'] = level if level is not None else old.get(entry['id'], {}).get('source_lufs')
    json.dump({'tracks': entries}, open(os.path.join(TRACKS, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    open(os.path.join(ROOT, 'CREDITS.md'), 'w', encoding='utf-8').write(
        '# Ektoplazm library: credits and licenses\n\nPrivate listening copy. License terms were read from each '
        'release page on the date shown. Not legal clearance.\n' + '\n'.join(credits) + '\n')
    hours = sum(e['duration'] for e in entries) / 3600
    print(f'{len(entries)} tracks, {hours:.1f} hours, {sum(e["size"] for e in entries) / 1e9:.2f} GB')

if __name__ == '__main__':
    copy_site() if '--site' in sys.argv else build()
