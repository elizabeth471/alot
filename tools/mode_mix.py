#!/usr/bin/env python3
"""Render one pre-mixed stream per purpose, plus a chapter list so the app knows which track is playing.

  python3 -I mode_mix.py            render every mix and write ~/music-pipeline/ektoplazm/modes/modes.json
  python3 -I mode_mix.py run        render only the named mixes, keeping the others as they are

One file per purpose carries over AirPlay as a single stream, and no code has to run while it plays.
Lists are a first draft from tempo, style and album: they need a person's ears, then votes refine them. Nothing here publishes.
"""
import json, os, random, subprocess, sys

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
OUT = os.path.join(ROOT, 'modes')
PUBLIC = 'https://pub-dfe2dc87a34d4016a8782237145e0938.r2.dev/modes'
CROSS, BITRATE = 6, '128k'
MAX_SECONDS = 5 * 3600  # keeps a file under the 315 MB limit for a single upload at this bitrate
tracks = json.load(open(os.path.join(ROOT, 'preview/tracks/manifest.json'), encoding='utf-8'))['tracks']
intros = json.load(open(os.path.join(ROOT, 'intros.json'), encoding='utf-8'))
MODES = {
    # Warms up on full-on psytrance, then climbs to drum and bass, with almost no noise.
    'run': dict(pick=lambda t: t['release'] in ('barby-nexus', 'octogoat-robot-reproduction', 'cryomatter-cryomatter', 'one-arc-degree-cybernetika-nether-moon', 'mellow-sonic-twisted-worlds'), noise='brown', level=0.02, climb=True),
    'flow': dict(pick=lambda t: t['style'] == 'electronic' and t['bpm'] <= 83, noise='brown', level=0.10),
    'ground': dict(pick=lambda t: t['release'] in ('zoungla-there-will-be-dub', 'globular-holobiont'), noise='brown', level=0.16),
    'meditate': dict(pick=lambda t: t['release'] in ('ajnia-oasis', 'ajnia-elements'), noise='pink', level=0.05),
}

def render(mode, spec):
    pool = [t for t in tracks if spec['pick'](t)]
    random.Random('alot-' + mode).shuffle(pool)
    pool.sort(key=lambda t: intros.get(t['name'], 0) >= 2)  # opens on a track that is audible at once
    head, rest = pool[:1], pool[1:]
    random.Random('alot2-' + mode).shuffle(rest)
    if spec.get('climb'):
        pool.sort(key=lambda t: t['bpm'])
        head, rest = [], pool
    chosen, at, chapters = [], 0.0, []
    for t in head + rest:
        if at + t['duration'] > MAX_SECONDS:
            continue
        chapters.append({'t': round(at, 2), 'id': t['id'], 'name': t['name']})
        chosen.append(t)
        at += t['duration'] - CROSS
    seconds = int(at + CROSS)
    inputs, parts = [], []
    for t in chosen:
        inputs += ['-i', os.path.join(ROOT, 'preview', t['file'])]
    last = '[0:a]'
    for i in range(1, len(chosen)):
        parts.append(f'{last}[{i}:a]acrossfade=d={CROSS}:c1=tri:c2=tri[m{i}]')
        last = f'[m{i}]'
    parts.append(f'{last}anull[music]')
    parts.append(f"anoisesrc=d={seconds}:c={spec['noise']}:r=44100:a=0.9:s=1804,lowpass=f=3200,pan=stereo|c0=c0|c1=c0,volume={spec['level']}[noise]")
    parts.append(f'[music][noise]amix=inputs=2:duration=first:normalize=0,afade=t=in:d=4,afade=t=out:st={seconds - 4}:d=4,alimiter=limit=0.84:level=false,aformat=sample_rates=44100:channel_layouts=stereo[out]')
    output = os.path.join(OUT, mode + '.m4a')
    subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-y'] + inputs + ['-filter_complex', ';'.join(parts), '-map', '[out]', '-c:a', 'aac', '-b:a', BITRATE, '-movflags', '+faststart', output], check=True, stderr=subprocess.DEVNULL)
    return {'id': mode, 'file': f'{PUBLIC}/{mode}.m4a', 'loop': True, 'duration': seconds, 'chapters': chapters}, output

def sleep_mode():
    """Sleep is the Night Arc already confirmed on Sonos: its chapters are worked out from the same track list."""
    data = json.load(open(os.path.join(ROOT, 'arc/night-arc-v1.json'), encoding='utf-8'))
    by_name = {t['name']: t for t in tracks}
    chapters, at = [], 0.0
    for item in data['tracks']:
        t = by_name[item['name']]
        if at < 3600:
            chapters.append({'t': round(at, 2), 'id': t['id'], 'name': t['name']})
        at += t['duration'] - 6
    return {'id': 'sleep', 'file': 'https://pub-dfe2dc87a34d4016a8782237145e0938.r2.dev/arcs/night-arc-v1.m4a', 'loop': False,
            'duration': 21600, 'music_until': 3600, 'chapters': chapters}

def level(path, at):
    e = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-ss', str(at), '-t', '30', '-i', path, '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return [l.split()[-2] for l in e.splitlines() if 'mean_volume' in l or 'max_volume' in l]

os.makedirs(OUT, exist_ok=True)
ORDER = ['sleep', 'flow', 'run', 'ground', 'meditate']
only = sys.argv[1:]
path_json = os.path.join(OUT, 'modes.json')
modes = {m['id']: m for m in json.load(open(path_json, encoding='utf-8'))['modes']} if only and os.path.exists(path_json) else {'sleep': sleep_mode()}
for mode, spec in MODES.items():
    if only and mode not in only:
        continue
    entry, path = render(mode, spec)
    modes[mode] = entry
    size = os.path.getsize(path) / 1e6
    print(f'{mode}: {len(entry["chapters"])} tracks, {entry["duration"] / 3600:.1f} hours, {size:.0f} MB', flush=True)
    if size > 315:
        sys.exit(f'{mode} is too large for a single upload')
    for at in [60, entry['duration'] // 2, entry['duration'] - 90]:
        print('   at', at, 's mean/peak dB', level(path, at), flush=True)
    for chapter in entry['chapters'][:4]:
        print('   ', chapter['name'], flush=True)
json.dump({'modes': [modes[m] for m in ORDER if m in modes]}, open(path_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
