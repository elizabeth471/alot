# alot

Layer noise and music in the browser. Live: https://alot-indol.vercel.app (Spanish by default, EN/ES toggle at the top).

## Use it
Open the link in a phone or computer browser. There is nothing to install and no sign-in.

- **Purposes:** Sleep, Flow, Ground and Meditate on the main screen. Tap one to play its pre-mixed stream. Like, Dislike and Next act on the track playing. Votes count per purpose.
- **Choose speaker** (top of the page) opens the AirPlay list where the browser offers it. Sonos through AirPlay works with these streams on an iPhone, per Ely on 2026-11-06.
- **Customize** opens the mixer: noise, playlist with Shuffle, and one Play for both. Noise colors are in the Library tab under Configure. AirPlay carries one stream, so through a speaker the mixer's noise and music do not play together.
- **Settings (gear):** beats, crossfade, screen and phone options.

## Code
- Work is on branch **`revive-noise-studio`**. `main` is older and is not what is live.
- `index.html` is the whole app. `tracks/manifest.json` lists the music. `credits.html` is generated.
- Publish from this folder only: `vercel deploy --prod --yes` (Vercel project `teamblossom/alot`). Run the tests first; a push alone does not publish.

## Music
- 100 tracks from 15 Ektoplazm releases, Creative Commons, loudness adjusted. Treat all of them as **non-commercial**. Credits and licenses: `credits.html`.
- Files are streamed from Cloudflare R2, bucket `alot-music`, account teamblossom.ops@gmail.com. Public address: https://pub-dfe2dc87a34d4016a8782237145e0938.r2.dev (rate-limited by Cloudflare; needs a real domain before alot is promoted).
- Allowed web addresses for streaming are set in the bucket's CORS policy: the live site and `127.0.0.1:8765`/`localhost:8765`.
- `tools/` holds the download, encode, upload and publish scripts. Audio files are not in git. The scripts expect `~/music-pipeline/ektoplazm` and were written for one Mac, so paths may need changing.

## Purpose mixes
`tools/mode_mix.py` renders one file per purpose and writes `tracks/modes.json`, whose chapters tell the app which track is playing. Sleep is the Night Arc from `tools/night_arc.py`: music to 45 minutes, fading out by 60, then noise to 6 hours. The track lists are a first draft from tempo and album, and need a person's ears. Run waits for faster music.

## Ratings
- **Like:** marks the track; it comes up about 3x sooner in shuffles on that device. Tap again to take it back.
- **Dislike:** skips to the next track, removes it from the list, and keeps it out of shuffles on that device. Undo reverses it; adding it again from the Library clears it.
- Votes in a purpose are stored as `purpose--track` and only affect that purpose's mix. Votes go to a Cloudflare Worker and D1 database (`worker/`, `alot-ratings`, account teamblossom.ops@gmail.com) with a random device ID, the track and the vote. No names, emails or IP addresses are stored. The address is write-only. Votes send only on a tap, on load if some are waiting, or on reconnecting.
- Shared changes need a person's review. `tools/alot_ratings.py` shows them; `--apply` saves them; then run `tools/ektoplazm_publish.py`, test, and publish. Rules: remove at 2 or more dislikes with more dislikes than likes; favor when likes outnumber dislikes; otherwise no change.

## Battery
alot runs all night. No endless animation, polling or idle timers. `tests/overnight.py` fails if idle playback uses over 10% of a processor core.

## Tests
Browser tests using Playwright, in `tests/`. Some paths are written for the original Mac. Example: `python tests/modes.py https://alot-indol.vercel.app/?lang=en`. Before publishing: `gate.py` (takes the Chrome path), then `audit.py`, `modes.py`, `layers.py`, `stream.py`, `overnight.py`, `speaker.py`, `locked_screen.py`, `single_player.py`.

## Not verified
- Real overnight battery life, the music and noise balance by ear, and the draft purpose lists.
- iPhone, AirPlay and Sonos: Ely reported them working on 2026-11-06, on her devices only. Flow, Ground and Meditate are new since that report.
- Spanish needs a native read. The name "alot" has not been cleared. Music rights need an attorney's look before any commercial use.
