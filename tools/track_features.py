#!/usr/bin/env python3
"""Measure every track in the library, so each purpose's playlist is chosen from how the music sounds, not just its album.

  ~/music-pipeline/venv/bin/python -I track_features.py

Writes ~/music-pipeline/ektoplazm/features.json, one entry per track:
  tempo (BPM, as heard), pulse (0-1, how clear and steady the beat is), energy (loudness, dB),
  bright (spectral centroid, Hz), bass (share of energy under 160 Hz), punch (how sharp the hits are),
  swing (how much loudness varies), percussive (share of energy in drums vs sustained sound).
Reads the evened-out preview copies. Nothing here publishes.
"""
import concurrent.futures, json, os, subprocess
import numpy as np
import librosa

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
SR = 22050

def measure(track):
    path = os.path.join(ROOT, 'preview', track['file'])
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.float32)
    # skip the first and last 20 s: intros and outros are not the character of the track
    if len(y) > SR * 60:
        y = y[SR * 20:-SR * 20]
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    power = S ** 2
    env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S), sr=SR)
    e = (env - env.mean()) / (env.std() + 1e-9)
    ac = librosa.autocorrelate(e, max_size=int(SR / 512 * 2)); ac = ac / ac[0]
    lo, hi = int(SR / 512 * 60 / 200), int(SR / 512 * 60 / 60)
    pulse = float(ac[lo:hi].max())
    tempo = float(np.atleast_1d(librosa.beat.tempo(onset_envelope=env, sr=SR))[0])
    rms = librosa.feature.rms(S=S)[0]
    db = 20 * np.log10(rms + 1e-9)
    per_s = db[:len(db) // 43 * 43].reshape(-1, 43).mean(axis=1)
    harm, perc = librosa.decompose.hpss(S)
    return track['id'], {
        'name': track['name'], 'release': track['release'], 'minutes': round(track['duration'] / 60, 1),
        'tempo': round(tempo, 1), 'pulse': round(pulse, 2),
        'energy': round(float(np.percentile(db, 75)), 1),
        'bright': round(float((librosa.feature.spectral_centroid(S=S, sr=SR)[0]).mean())),
        'bass': round(float(power[freqs < 160].sum() / power.sum()), 3),
        'punch': round(float(np.percentile(env, 95) / (np.median(env) + 1e-9)), 2),
        'swing': round(float(np.std(per_s)), 1),
        'percussive': round(float((perc ** 2).sum() / ((harm ** 2).sum() + (perc ** 2).sum())), 3),
    }

def main():
    tracks = json.load(open(os.path.join(ROOT, 'preview/tracks/manifest.json'), encoding='utf-8'))['tracks']
    if 'release' not in tracks[0]:
        raise SystemExit('preview manifest is the public copy; restore the private one first')
    out = {}
    with concurrent.futures.ProcessPoolExecutor(6) as pool:
        for tid, f in pool.map(measure, tracks):
            out[tid] = f
            print(f"{f['release'][:22]:22s} {f['tempo']:6.1f} bpm pulse {f['pulse']:.2f} energy {f['energy']:6.1f} bright {f['bright']:5d} bass {f['bass']:.2f} punch {f['punch']:5.2f} perc {f['percussive']:.2f}  {f['name'][:40]}", flush=True)
    json.dump(out, open(os.path.join(ROOT, 'features.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
