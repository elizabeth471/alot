#!/usr/bin/env python3
"""Upload the evened-out Ektoplazm tracks to alot's R2 bucket, then check each one from the public address.

  python3 -I ektoplazm_upload.py

Uses the Team Blossom Cloudflare login, kept in its own config so the login utterlight uses is untouched.
Files already there at the right size are skipped, so it is safe to run again.
"""
import concurrent.futures, json, os, subprocess, sys, urllib.error, urllib.request

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm/preview')
BUCKET = 'alot-music'
PUBLIC = 'https://pub-dfe2dc87a34d4016a8782237145e0938.r2.dev'
ENV = dict(os.environ, XDG_CONFIG_HOME=os.path.expanduser('~/.config/tb-cloudflare'), WRANGLER_SEND_METRICS='false')
UA = {'User-Agent': 'alot-upload-check/1.0'}

def remote_size(key):
    request = urllib.request.Request(f'{PUBLIC}/{key}', method='HEAD', headers=UA)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.headers.get('Content-Length', -1))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

def upload(track):
    key = track['file']
    path = os.path.join(ROOT, key)
    size = os.path.getsize(path)
    if remote_size(key) == size:
        return key, 'already there'
    result = subprocess.run(['npx', '--yes', 'wrangler@4', 'r2', 'object', 'put', f'{BUCKET}/{key}', '--remote', '--file', path,
                             '--content-type', 'audio/mp4', '--cache-control', 'public, max-age=31536000'],
                            cwd='/private/tmp', env=ENV, capture_output=True, text=True)
    if result.returncode:
        return key, 'FAILED ' + result.stderr.strip()[-200:]
    return key, 'uploaded'

def check(track):
    key = track['file']
    size = os.path.getsize(os.path.join(ROOT, key))
    request = urllib.request.Request(f'{PUBLIC}/{key}', headers=dict(UA, Range='bytes=0-1023', Origin='http://127.0.0.1:8765'))
    with urllib.request.urlopen(request, timeout=30) as response:
        problems = []
        if response.status != 206: problems.append(f'status {response.status}')
        if response.headers.get('Content-Type') != 'audio/mp4': problems.append('type ' + str(response.headers.get('Content-Type')))
        if not (response.headers.get('Content-Range') or '').endswith(f'/{size}'): problems.append('size mismatch')
        if response.headers.get('Access-Control-Allow-Origin') != 'http://127.0.0.1:8765': problems.append('no CORS header')
        if len(response.read()) != 1024: problems.append('short read')
    return key, problems

def main():
    tracks = json.load(open(os.path.join(ROOT, 'tracks/manifest.json'), encoding='utf-8'))['tracks']
    failed = 0
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        for key, status in pool.map(upload, tracks):
            print(status, key, flush=True)
            failed += status.startswith('FAILED')
    if failed:
        sys.exit(f'{failed} uploads failed; run again')
    bad = 0
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        for key, problems in pool.map(check, tracks):
            if problems:
                bad += 1
                print('BAD', key, problems, flush=True)
    print(f'{len(tracks)} tracks: {len(tracks) - bad} check out, {bad} with problems', flush=True)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
