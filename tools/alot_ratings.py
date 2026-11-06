#!/usr/bin/env python3
"""Turn collected likes and dislikes into changes to the shared track list. A person reviews before anything changes.

  python3 -I alot_ratings.py            read the database and show what would change
  python3 -I alot_ratings.py --apply    save the changes, then run ektoplazm_publish.py, test and publish

RULES, per track, counting one vote per device:
  Remove from the library:  2 or more dislikes, and more dislikes than likes.
  Favor in shuffles (3x):   more likes than dislikes.
  Watch, no change:         1 dislike only, or a tie. That person's own device already skips it.
Artist totals are printed to guide finding more music. This tool never publishes.
"""
import json, os, subprocess, sys
ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
SAVED = os.path.join(ROOT, 'ratings-applied.json')
ENV = dict(os.environ, XDG_CONFIG_HOME=os.path.expanduser('~/.config/tb-cloudflare'), WRANGLER_SEND_METRICS='false')
QUERY = 'SELECT track, SUM(vote = 1) AS likes, SUM(vote = -1) AS dislikes, COUNT(DISTINCT device) AS devices FROM votes GROUP BY track'
def read_votes():
    result = subprocess.run(['npx', '--yes', 'wrangler@4', 'd1', 'execute', 'alot-ratings', '--remote', '--json', '--command', QUERY],
                            cwd=os.path.expanduser('~/Documents/_bench-src/alot/worker'), env=ENV, capture_output=True, text=True)
    if result.returncode:
        sys.exit('Could not read the ratings database: ' + (result.stderr + result.stdout).strip()[-300:])
    return json.loads(result.stdout)[0]['results']
def decide(rows):
    removed, weights, watch = [], {}, []
    for row in rows:
        likes, dislikes = row['likes'], row['dislikes']
        if dislikes >= 2 and dislikes > likes: removed.append(row['track'])
        elif likes > dislikes: weights[row['track']] = 3
        elif dislikes: watch.append(row['track'])
    return removed, weights, watch
if __name__ == '__main__':
    tracks = {t['id']: t['name'] for t in json.load(open(os.path.join(ROOT, 'preview/tracks/manifest.json'), encoding='utf-8'))['tracks']}
    votes = read_votes()
    # Votes made in a purpose are stored as purpose--track, and only change that purpose's mix.
    by_mode = {}
    for r in votes:
        if '--' in r['track']:
            mode, track = r['track'].split('--', 1)
            if track in tracks:
                by_mode.setdefault(mode, []).append(dict(r, track=track))
    for mode, mode_rows in sorted(by_mode.items()):
        out, more, keep = decide(mode_rows)
        names = lambda keys: ', '.join(sorted(tracks[k] for k in keys)) or 'none'
        print(f'[{mode}] {len(mode_rows)} tracks rated. Take out: {names(out)}. Keep or play more: {names(more)}. Watch: {names(keep)}.')
    if by_mode:
        print('Purpose mixes change only by updating the list in mode_mix.py and rendering again.')
    rows = [r for r in votes if r['track'] in tracks]
    removed, weights, watch = decide(rows)
    artists = {}
    for r in rows:
        artist = tracks[r['track']].split(' – ')[0]
        artists[artist] = artists.get(artist, 0) + r['likes'] - r['dislikes']
    show = lambda keys: ''.join(f'\n  {tracks[k]}' for k in sorted(keys)) or ' none'
    print(f'{len(rows)} tracks rated by {sum(r["devices"] for r in rows)} votes')
    print('Remove:' + show(removed)); print('Favor:' + show(weights)); print('Watch:' + show(watch))
    print('Artists:' + (''.join(f'\n  {v:+d} {a}' for a, v in sorted(artists.items(), key=lambda x: -x[1])) or ' none'))
    if '--apply' in sys.argv:
        json.dump({'removed': removed, 'weights': weights}, open(SAVED, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('Saved. Next: ektoplazm_publish.py, tests, then publish.')
    else:
        print('Nothing changed. Add --apply after review.')
