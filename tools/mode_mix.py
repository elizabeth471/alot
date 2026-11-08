#!/usr/bin/env python3
"""Render one pre-mixed stream per purpose, plus a chapter list so the app knows which track is playing.

  python3 -I mode_mix.py            render every mix and write ~/music-pipeline/ektoplazm/modes/modes.json
  python3 -I mode_mix.py run        render only the named mixes, keeping the others as they are
  python3 -I mode_mix.py noise      render only the three noise-only loops (brown, pink, white)

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
# Track lists chosen from measurements (track_features.py: drum share, beat clarity, brightness, bass) and album character.
# Each track belongs to one purpose; Sleep keeps the Night Arc already confirmed on Sonos.
def named(*parts):
    return lambda t: any(p in t['name'] for p in parts)
RUN_ALBUMS = ('barby-nexus', 'octogoat-robot-reproduction', 'cryomatter-cryomatter', 'one-arc-degree-cybernetika-nether-moon', 'mellow-sonic-twisted-worlds')
MODES = {
    # Warms up on full-on psytrance, then climbs to drum and bass, with almost no noise.
    'run': dict(pick=lambda t: t['release'] in RUN_ALBUMS, noise='brown', level=0.02, climb=True),
    # Focus: a steady, clear beat with moderate drums. All of Entangled Everything, most of Holobiont, rhythmic Saluberrimae and Sephira.
    'flow': dict(pick=lambda t: t['release'] == 'globular-entangled-everything' or named(
        '[42]', 'Might of Chondria', 'Temple of the Pollinator', 'Upwards Curve', 'Emergent Resurgence', 'Overcoming Occhiolism', 'and It Speaks',
        'Loophole', 'Trapped Inside', 'Gestonkenflapped', 'Čiernobiela', 'Večerná', 'Dissolution Dichotomy', 'A Fitting End', 'Cave Of Calcination')(t),
        noise='brown', level=0.08),
    # Calm and settled: dub bass, plus Saluberrimae's three darkest.
    'ground': dict(pick=lambda t: t['release'] == 'zoungla-there-will-be-dub' or named('Jennifer Connelly', 'Frozen', 'The Abyss')(t), noise='brown', level=0.14),
    # No drums, hardly any beat: Shinjibomb's long ambient pieces and Ajnia's quietest.
    'meditate': dict(pick=named('2019 (Neo Tokyo', 'Firefly (Shinjibomb', 'Ajnia – Earth', 'Ajnia – Fire', 'Ajnia – Water', 'Ajnia – Air', 'Ajnia – Ether',
        'Entre Las Dunas', 'La Gran Ruta Del Sur', 'Ajnia – Oasis', 'Saluberrimae – Time Is A Flat Circle'), noise='pink', level=0.05),
    # Slow, warm, sensual: few drums, deep bass. Rises gently to the middle and comes back down.
    'love': dict(pick=lambda t: t['release'] == 'greatowl-lilia-sin-mi' or named(
        'Conjunction Event', 'Double Distillation', 'Dormant Fermentation', 'Coagulation', 'Self Separation', 'Stranger At The Oasis',
        'Philae', 'Simoon', 'Jesenné', 'Tabula Rasa')(t), noise='brown', level=0.04, arc=True),
}

def render(mode, spec):
    pool = [t for t in tracks if spec['pick'](t)]
    random.Random('alot-' + mode).shuffle(pool)
    pool.sort(key=lambda t: intros.get(t['name'], 0) >= 2)  # opens on a track that is audible at once
    head, rest = pool[:1], pool[1:]
    random.Random('alot2-' + mode).shuffle(rest)
    if spec.get('arc'):
        energy = json.load(open(os.path.join(ROOT, 'features.json'), encoding='utf-8'))
        pool.sort(key=lambda t: energy[t['id']]['energy'])
        head, rest = [], pool[0::2] + pool[1::2][::-1]  # quietest at both ends, fullest in the middle
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
    output = os.path.join(OUT, mode + '-v2.m4a')  # a new name: the old files are cached for a year
    subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-y'] + inputs + ['-filter_complex', ';'.join(parts), '-map', '[out]', '-c:a', 'aac', '-b:a', BITRATE, '-movflags', '+faststart', output], check=True, stderr=subprocess.DEVNULL)
    return {'id': mode, 'file': f'{PUBLIC}/{mode}-v2.m4a', 'loop': True, 'duration': seconds, 'chapters': chapters}, output

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

NOISE_COLORS = {'brown': 0.64, 'pink': 0.6, 'white': 0.33}  # gains chosen so the three sit at a similar loudness

def noise_mode():
    """Noise only: one hour per color that loops seamlessly. The last 5 s fade into the first 5 s, so the loop point has no click."""
    files = {}
    for color, gain in NOISE_COLORS.items():
        output = os.path.join(OUT, f'noise-{color}.m4a')
        src = lambda seed: f'anoisesrc=d=3605:c={color}:r=44100:a={gain}:s={seed},lowpass=f=3200'
        graph = (f'{src(11)}[l];{src(29)}[r];[l][r]join=inputs=2:channel_layout=stereo,asplit[a][b];'
                 f'[a]atrim=start=5:end=3605,asetpts=PTS-STARTPTS[body];[b]atrim=end=5,asetpts=PTS-STARTPTS[head];'
                 f'[body][head]acrossfade=d=5:c1=qsin:c2=qsin,alimiter=limit=0.84:level=false[out]')
        subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-y', '-filter_complex', graph, '-map', '[out]',
                        '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', output], check=True, stderr=subprocess.DEVNULL)
        files[color] = f'{PUBLIC}/noise-{color}.m4a'
        print(f'noise {color}: {os.path.getsize(output) / 1e6:.0f} MB, mean/peak dB', level(output, 600), flush=True)
    return {'id': 'noise', 'file': files['brown'], 'files': files, 'loop': True, 'duration': 3600, 'chapters': []}

def level(path, at):
    e = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-ss', str(at), '-t', '30', '-i', path, '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return [l.split()[-2] for l in e.splitlines() if 'mean_volume' in l or 'max_volume' in l]

os.makedirs(OUT, exist_ok=True)
ORDER = ['run', 'flow', 'ground', 'meditate', 'love', 'sleep', 'noise']  # most energy to least, ending at night; Noise only last
only = sys.argv[1:]
path_json = os.path.join(OUT, 'modes.json')
modes = {m['id']: m for m in json.load(open(path_json, encoding='utf-8'))['modes']} if only and os.path.exists(path_json) else {'sleep': sleep_mode()}
if not only or 'noise' in only:
    modes['noise'] = noise_mode()
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
