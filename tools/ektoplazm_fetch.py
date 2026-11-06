#!/usr/bin/env python3
"""Download chosen Ektoplazm releases into a private library, keeping each release's license.

  python3 -I ektoplazm_fetch.py

Only fetches the release pages named below, one at a time, with a pause between requests.
A release with no Creative Commons link on its page is skipped, not assumed.
Only .mp3 files are taken out of each zip; nothing downloaded is ever run.
Nothing here publishes anything.
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request, zipfile, datetime

ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
ORIGINALS = os.path.join(ROOT, 'originals')
UA = 'alot-private-library/1.0'
PAUSE = 3

RELEASES = [
    'globular-entangled-everything', 'zoungla-there-will-be-dub', 'sephira-the-master-work',
    'globular-holobiont', 'greatowl-lilia-sin-mi', 'huuhaa-frostient',
    'saluberrimae-time-is-a-flat-circle', 'ajnia-oasis', 'ajnia-elements', 'shinjibomb-shinjibomb',
]

def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': UA})
    return urllib.request.urlopen(request, timeout=120)

def download(url, path):
    if os.path.exists(path) and zipfile.is_zipfile(path):
        return os.path.getsize(path)
    part = path + '.part'
    with get(url) as response, open(part, 'wb') as out:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    if not zipfile.is_zipfile(part):
        os.remove(part)
        raise ValueError('download is not a zip')
    os.replace(part, path)
    return os.path.getsize(path)

def extract_mp3s(zip_path, dest):
    os.makedirs(dest, exist_ok=True)
    names = []
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            base = os.path.basename(info.filename)  # drops any folder path inside the zip
            if info.is_dir() or not base.lower().endswith('.mp3') or base.startswith('.'):
                continue
            with archive.open(info) as source, open(os.path.join(dest, base), 'wb') as out:
                while True:
                    chunk = source.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
            names.append(base)
    return sorted(names)

def main():
    os.makedirs(ORIGINALS, exist_ok=True)
    results = []
    for slug in RELEASES:
        page_url = f'https://ektoplazm.com/free-music/{slug}'
        record = {'slug': slug, 'page': page_url, 'retrieved': datetime.date.today().isoformat()}
        try:
            page = get(page_url).read().decode('utf-8', 'replace')
            time.sleep(PAUSE)
            licenses = sorted(set(re.findall(r'creativecommons\.org/licenses/([a-z-]+/[\d.]+)', page)))
            zips = re.findall(r'href="(https://ektoplazm\.com/files/[^"]+MP3\.zip)"', page)
            bpm = re.findall(r'(\d{2,3})\s*BPM', page)
            record['licenses_on_page'] = licenses
            record['noncommercial_wording_on_page'] = bool(re.search(r'non-?commercial', html.unescape(page), re.I))
            record['bpm'] = int(bpm[0]) if bpm else None
            if not licenses:
                record['status'] = 'skipped: no Creative Commons link on page'
            elif not zips:
                record['status'] = 'skipped: no MP3 download on page'
            else:
                url = zips[0]
                name = urllib.parse.unquote(url.rsplit('/', 1)[1])
                parts = name.replace(' - MP3.zip', '').split(' - ')
                record.update({'artist': parts[0], 'album': parts[1] if len(parts) > 1 else slug,
                               'year': parts[2] if len(parts) > 2 else None, 'download': url})
                folder = os.path.join(ORIGINALS, slug)
                os.makedirs(folder, exist_ok=True)
                zip_path = os.path.join(folder, 'release.zip')
                record['zip_bytes'] = download(url, zip_path)
                record['tracks'] = extract_mp3s(zip_path, os.path.join(folder, 'mp3'))
                record['status'] = 'ok' if record['tracks'] else 'skipped: zip held no mp3'
                time.sleep(PAUSE)
        except Exception as error:
            record['status'] = f'failed: {error}'
        results.append(record)
        print(slug, '->', record['status'], record.get('licenses_on_page'), len(record.get('tracks', [])), flush=True)
        json.dump(results, open(os.path.join(ROOT, 'releases.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    ok = [r for r in results if r['status'] == 'ok']
    print(f'{len(ok)} of {len(results)} releases ok, {sum(len(r["tracks"]) for r in ok)} tracks')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
