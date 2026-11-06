#!/usr/bin/env python3
"""Turn likes and dislikes copied from alot into changes to the shared track list.

  python3 -I alot_ratings.py ratings1.json [ratings2.json ...]           show what would change
  python3 -I alot_ratings.py --apply ratings1.json [ratings2.json ...]   save it, then run ektoplazm_publish.py

Across people: a track with more dislikes than likes is removed, one with more likes comes up about 3x more in shuffle.
A tie stays as it is. Also reports which artists are doing well, to guide finding more music. Never deploys.
"""
import json, os, sys
ROOT = os.path.expanduser('~/music-pipeline/ektoplazm')
SAVED = os.path.join(ROOT, 'ratings-applied.json')
args = [a for a in sys.argv[1:] if a != '--apply']
apply_it = '--apply' in sys.argv
if not args:
    sys.exit(__doc__)
tracks = {t['id']: t for t in json.load(open(os.path.join(ROOT, 'preview/tracks/manifest.json'), encoding='utf-8'))['tracks']}
state = json.load(open(SAVED, encoding='utf-8')) if os.path.exists(SAVED) else {'removed': [], 'weights': {}, 'votes': {}}
state.setdefault('votes', {})
for path in args:
    data = json.load(open(path, encoding='utf-8'))
    if data.get('app') != 'alot' or not isinstance(data.get('ratings'), dict):
        sys.exit(f'{path}: not a set of alot ratings')
    for key, vote in data['ratings'].items():
        if key not in tracks:
            print('ignored, not in the library:', str(key)[:60])
        elif vote in (1, -1):
            state['votes'].setdefault(key, {})[data.get('exported', path)] = vote
removed, weights, artists = [], {}, {}
for key, votes in state['votes'].items():
    total = sum(votes.values())
    artist = tracks[key]['name'].split(' – ')[0]
    artists[artist] = artists.get(artist, 0) + total
    if total < 0:
        removed.append(key)
    elif total > 0:
        weights[key] = 3
name = lambda k: tracks[k]['name']
print(f'{len(state["votes"])} tracks rated')
print('Remove:', *(f'\n  {name(k)}' for k in sorted(removed)) or [' none'])
print('Play more often:', *(f'\n  {name(k)}' for k in sorted(weights)) or [' none'])
print('Artists by score:', *(f'\n  {v:+d} {a}' for a, v in sorted(artists.items(), key=lambda x: -x[1])) or [' none'])
if apply_it:
    state['removed'], state['weights'] = removed, weights
    json.dump(state, open(SAVED, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('Saved. Next: ektoplazm_publish.py, tests, then publish.')
else:
    print('Nothing changed. Add --apply to save.')
