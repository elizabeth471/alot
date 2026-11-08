#!/usr/bin/env python3
"""Work out how each purpose mix moves, so projector mode can follow it without analysing audio on the device.

  ~/music-pipeline/venv/bin/python -I mode_envelope.py            every mix in modes.json
  ~/music-pipeline/venv/bin/python -I mode_envelope.py run flow   only the named ones

Writes to ~/music-pipeline/ektoplazm/modes/env/:
  <name>.bin   40 frames a second, 6 bytes each: [bass, mids, highs, hit, bright, loud], 0-255.
               hit: onset strength. bright: spectral centroid (how bright the sound is). loud: overall level.
  <name>.json  {"fps": 40, "beats": [[time, strength 1-9, 1 if it starts a bar], ...], "tempo": [[time, bpm], ...],
                "moments": [[time, "drop"|"calm"], ...], "sections": [[time, key 0-11, major 1|minor 0, energy 0-9], ...]}
Beats are only kept where the music has a clear pulse, so ambient and noise get none. Nothing here publishes.
"""
import json, os, subprocess, sys
import numpy as np
import librosa

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
OUT = os.path.join(ROOT, 'modes', 'env')
FPS = 40
RATE = 22040            # 40 x 551, so one frame is exactly 551 samples
HOP = RATE // FPS
WIN = 2048
BANDS = [(20, 160), (160, 2000), (2000, 8000)]
CHUNK, PAD = 120, 8     # beats are found two minutes at a time, with overlap so none are lost at the joins

def local_path(url):
    name = url.rsplit('/', 1)[1]
    return os.path.join(ROOT, 'arc' if '/arcs/' in url else 'modes', name)

def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', path, '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

def levels(y):
    """Band levels and onset strength, 40 a second."""
    freqs = np.fft.rfftfreq(WIN, 1 / RATE)
    masks = [(freqs >= lo) & (freqs < hi) for lo, hi in BANDS]
    window = np.hanning(WIN).astype(np.float32)
    n = (len(y) - WIN) // HOP + 1
    bands = np.zeros((n, 3), np.float32)
    flux = np.zeros(n, np.float32)
    cent = np.zeros(n, np.float32)
    total = np.zeros(n, np.float32)
    prev = None
    step = 4000
    for s in range(0, n, step):
        m = min(step, n - s)
        idx = np.arange(WIN)[None, :] + HOP * (s + np.arange(m))[:, None]
        spec = np.abs(np.fft.rfft(y[idx] * window, axis=1))
        for i, mask in enumerate(masks):
            bands[s:s + m, i] = np.sqrt((spec[:, mask] ** 2).mean(axis=1))
        power = spec ** 2
        total[s:s + m] = np.sqrt(power.mean(axis=1))
        cent[s:s + m] = (power * freqs).sum(axis=1) / (power.sum(axis=1) + 1e-9)
        low = np.log1p(spec[:, freqs < 4000] * 10)
        start = low[:1] if prev is None else prev
        flux[s:s + m] = np.maximum(np.diff(np.vstack([start, low]), axis=0), 0).sum(axis=1)
        prev = low[-1:]
    out = np.zeros((n, 6), np.uint8)
    db = 20 * np.log10(bands + 1e-6)
    for i in range(3):
        lo, hi = np.percentile(db[:, i], 5), np.percentile(db[:, i], 99.5)
        out[:, i] = np.clip((db[:, i] - lo) / max(hi - lo, 1e-6) * 255, 0, 255)
    avg = np.convolve(flux, np.ones(41) / 41, mode='same')
    hit = np.maximum(flux - 1.3 * avg, 0)
    top = np.percentile(hit[hit > 0], 97) if (hit > 0).any() else 1
    out[:, 3] = np.clip(hit / max(top, 1e-6) * 255, 0, 255)
    lc = np.log2(cent + 50)
    lo, hi = np.percentile(lc, 3), np.percentile(lc, 99)
    out[:, 4] = np.clip((lc - lo) / max(hi - lo, 1e-6) * 255, 0, 255)
    ldb = 20 * np.log10(total + 1e-6)
    lo, hi = np.percentile(ldb, 5), np.percentile(ldb, 99.5)
    out[:, 5] = np.clip((ldb - lo) / max(hi - lo, 1e-6) * 255, 0, 255)
    return out, db

def beats(y):
    """Beat times with strength, and tempo, for the parts of the mix that have a clear pulse."""
    found, tempo = [], []
    total = len(y) / RATE
    start = 0.0
    while start < total:
        a, b = max(0, start - PAD), min(total, start + CHUNK + PAD)
        seg = y[int(a * RATE):int(b * RATE)]
        env = librosa.onset.onset_strength(y=seg, sr=RATE, hop_length=512)
        if len(env) > 100 and env.std() > 1e-6:
            e = (env - env.mean()) / env.std()
            ac = librosa.autocorrelate(e, max_size=int(RATE / 512 * 2))
            ac = ac / ac[0]
            lo, hi = int(RATE / 512 * 60 / 200), int(RATE / 512 * 60 / 60)   # lags for 200 to 60 BPM
            clarity = float(ac[lo:hi].max())
            if clarity > 0.5:   # a real, steady pulse (Run and Flow mostly 0.6-0.9); ambient and noise stay below
                bpm, frames = librosa.beat.beat_track(onset_envelope=env, sr=RATE, hop_length=512, tightness=120)
                bpm = float(np.atleast_1d(bpm)[0])
                times = librosa.frames_to_time(frames, sr=RATE, hop_length=512) + a
                peak = np.percentile(env, 98) or 1
                low = librosa.onset.onset_strength(y=seg, sr=RATE, hop_length=512, fmax=200, n_mels=32)
                phase = int(np.argmax([low[frames[k::4]].mean() if len(frames[k::4]) else 0 for k in range(4)])) if len(frames) >= 8 else 0
                for j, (f, t) in enumerate(zip(frames, times)):
                    if start <= t < start + CHUNK:
                        found.append([round(float(t), 3), int(np.clip(env[f] / peak * 9, 1, 9)), int(j % 4 == phase)])
                tempo.append([round(start, 1), round(bpm, 1)])
            else:
                tempo.append([round(start, 1), 0])
        start += CHUNK
    return found, tempo

MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
def sections(y, data):
    """Key (Krumhansl profiles on chroma) and energy, every 12 s, smoothed over a minute; a new section where either changes."""
    step = 12
    rows = []
    for a in range(0, int(len(y) / RATE) - step, step):
        seg = y[a * RATE:(a + step) * RATE]
        chroma = librosa.feature.chroma_stft(y=seg, sr=RATE, hop_length=2048).mean(axis=1)
        if chroma.sum() < 1e-6:
            rows.append((a, -1, 1, 0)); continue
        c = (chroma - chroma.mean()) / (chroma.std() + 1e-9)
        scores = [(np.corrcoef(c, np.roll(MAJOR, k))[0, 1], k, 1) for k in range(12)] + [(np.corrcoef(c, np.roll(MINOR, k))[0, 1], k, 0) for k in range(12)]
        best = max(scores)
        energy = int(np.clip(data[a * FPS:(a + step) * FPS, 5].mean() / 255 * 9.99, 0, 9))
        rows.append((a, best[1] if best[0] > 0.35 else -1, best[2], energy))
    out, last, held = [], None, 0
    for i, r in enumerate(rows):
        window = rows[max(0, i - 5):i + 6]   # about two minutes, so a section is a real change, not a passing chord
        keys = [w[1] for w in window if w[1] >= 0]
        key = max(set(keys), key=keys.count) if keys else -1
        modes = [w[2] for w in window]
        mode = 1 if sum(modes) * 2 >= len(modes) else 0
        energy = int(round(np.median([w[3] for w in window])))
        cur = (key, mode, energy // 4)
        if cur != last:
            out.append([float(r[0]), key, mode, energy]); last = cur
    return out

def moments(db, fps=FPS):
    """Drops (energy jumps after a quieter stretch) and calms (energy falls away), at least 20 s apart."""
    energy = db.mean(axis=1)
    per_s = energy[:len(energy) // fps * fps].reshape(-1, fps).mean(axis=1)
    smooth = np.convolve(per_s, np.ones(3) / 3, mode='same')
    found, last = [], -99
    for t in range(10, len(smooth) - 6):
        before, after = smooth[t - 10:t - 2].mean(), smooth[t:t + 6].mean()
        if t - last < 20:
            continue
        if after - before > 6 and after > np.median(smooth):
            found.append([float(t), 'drop']); last = t
        elif before - after > 7:
            found.append([float(t), 'calm']); last = t
    return found

def main():
    modes = json.load(open(os.path.join(ROOT, 'modes', 'modes.json'), encoding='utf-8'))['modes']
    only = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
    for m in modes:
        for url in (m.get('files') or {'': m['file']}).values():
            name = url.rsplit('/', 1)[1].replace('.m4a', '')
            if only and m['id'] not in only and name not in only:
                continue
            y = decode(local_path(url))
            data, db = levels(y)
            data.tofile(os.path.join(OUT, name + '.v3.bin'))
            b, tempo = beats(y)
            mo = moments(db)
            sec = sections(y, data)
            json.dump({'fps': FPS, 'beats': b, 'tempo': tempo, 'moments': mo, 'sections': sec}, open(os.path.join(OUT, name + '.v3.json'), 'w'), separators=(',', ':'))
            hours = len(y) / RATE / 3600
            bpms = [x[1] for x in tempo if x[1]]
            print(f'{name}: {hours:.2f} h, {data.nbytes / 1e6:.1f} MB levels, {len(b)} beats ({len(b) / (hours * 60):.0f}/min), '
                  f'tempo {min(bpms) if bpms else 0:.0f}-{max(bpms) if bpms else 0:.0f}, pulse in {len(bpms)}/{len(tempo)} stretches, '
                  f'{sum(1 for x in mo if x[1] == "drop")} drops, {sum(1 for x in mo if x[1] == "calm")} calms, {len(sec)} sections, {sum(1 for x in b if x[2])} bar starts', flush=True)

if __name__ == '__main__':
    main()
