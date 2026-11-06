#!/usr/bin/env python3
"""Render a Night Arc: one long file where music fades away and gentle noise carries on.

  python3 -I night_arc.py

Timeline: music with noise to 45 min, music fades out by 60 min, noise eases down 3 dB over the next hour,
then holds until the end. One file means no code has to run while it plays. Nothing here publishes it.
"""
import json, os, subprocess, sys

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
OUT = os.path.join(ROOT, 'arc')
HOURS, FADE_START, FADE_LEN, CROSS = 6, 2700, 900, 6
BITRATE = '96k'  # keeps 6 hours under the 315 MB limit for a single upload
tracks = json.load(open(os.path.join(ROOT, 'preview/tracks/manifest.json'), encoding='utf-8'))['tracks']
intros = json.load(open(os.path.join(ROOT, 'intros.json'), encoding='utf-8'))
calm = [t for t in tracks if t['style'] == 'ambient' and intros.get(t['name'], 0) < 2 and t['bpm'] <= 95]
calm.sort(key=lambda t: (-t['bpm'], t['id']))  # slows down as it goes
chosen, total = [], 0
per_album = {}
for t in calm:
    per_album[t['release']] = per_album.get(t['release'], 0) + 1
    if per_album[t['release']] > 4:
        continue
    chosen.append(t)
    total += t['duration'] - CROSS
    if total >= FADE_START + FADE_LEN + 30:
        break
if total < FADE_START + FADE_LEN:
    sys.exit(f'only {total / 60:.0f} minutes of calm music found')
os.makedirs(OUT, exist_ok=True)
seconds = HOURS * 3600
inputs, parts = [], []
for t in chosen:
    inputs += ['-i', os.path.join(ROOT, 'preview', t['file'])]
last = '[0:a]'
for i in range(1, len(chosen)):
    parts.append(f'{last}[{i}:a]acrossfade=d={CROSS}:c1=tri:c2=tri[m{i}]')
    last = f'[m{i}]'
n = len(chosen)
music_end = FADE_START + FADE_LEN
parts.append(f'{last}atrim=0:{music_end},afade=t=in:d=10,afade=t=out:st={FADE_START}:d={FADE_LEN}:curve=qsin,apad=whole_dur={seconds}[music]')
# Noise sits well under the music, then eases down 3 dB between 60 and 120 minutes.
ease = "0.27*(1-0.29*min(1\\,max(0\\,(t-3600)/3600)))"
parts.append(f"anoisesrc=d={seconds}:c=brown:r=44100:a=0.9:s=1804,lowpass=f=2400,pan=stereo|c0=c0|c1=c0,volume='{ease}':eval=frame,afade=t=in:d=20,afade=t=out:st={seconds - 30}:d=30[noise]")
parts.append('[music][noise]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.84:level=false,aformat=sample_rates=44100:channel_layouts=stereo[out]')
output = os.path.join(OUT, 'night-arc-v1.m4a')
command = ['ffmpeg', '-hide_banner', '-nostdin', '-y'] + inputs + ['-filter_complex', ';'.join(parts), '-map', '[out]', '-t', str(seconds),
           '-c:a', 'aac', '-b:a', BITRATE, '-movflags', '+faststart', output]
subprocess.run(command, check=True, stderr=subprocess.DEVNULL)
credits = {'file': 'night-arc-v1.m4a', 'hours': HOURS, 'tracks': [{'name': t['name'], 'license': t['license'], 'minutes': round(t['duration'] / 60, 1)} for t in chosen]}
json.dump(credits, open(os.path.join(OUT, 'night-arc-v1.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{n} tracks, {os.path.getsize(output) / 1e6:.0f} MB')
for t in chosen:
    print(' ', t['name'], t['license'])

# Check by measurement, since nobody here can hear it.
def level(start, length=30):
    e = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-ss', str(start), '-t', str(length), '-i', output, '-af', 'volumedetect', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    mean = [l for l in e.splitlines() if 'mean_volume' in l][0].split()[-2]
    peak = [l for l in e.splitlines() if 'max_volume' in l][0].split()[-2]
    return float(mean), float(peak)
for label, at in [('1 min', 60), ('30 min', 1800), ('44 min', 2640), ('52 min', 3120), ('59 min', 3540), ('62 min', 3720), ('2.5 hr', 9000), ('5.9 hr', seconds - 400)]:
    mean, peak = level(at)
    print(f'{label:7s} mean {mean:6.1f} dB   peak {peak:6.1f} dB')
