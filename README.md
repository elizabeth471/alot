# alot

Layer noise and music in the browser. Live: https://alot-indol.vercel.app (Spanish by default, EN/ES toggle at the top).

## Use it
Open the link in a phone or computer browser. There is nothing to install and no sign-in.

- **Noise:** the round button plays it, the fader sets its level, the chips choose a color, Configure opens the generator.
- **Playlist:** Shuffle queues the whole library in one tap. Like and Dislike steer later shuffles. Configure opens the Playlist and Library tabs.
- **Big Play:** starts noise and music together. **Master volume** sets the overall level.
- **Settings (gear):** beats, crossfade, screen and phone options.

## Code
- Work is on branch **`revive-noise-studio`**. `main` is older and is not what is live.
- `index.html` is the whole app. `tracks/manifest.json` lists the music. `credits.html` is generated.
- Publish from this folder only: `vercel deploy --prod --yes` (Vercel project `teamblossom/alot`). Run the tests first; a push alone does not publish.

## Music
- 66 tracks from 10 Ektoplazm releases, Creative Commons, loudness adjusted. Treat all of them as **non-commercial**. Credits and licenses: `credits.html`.
- Files are streamed from Cloudflare R2, bucket `alot-music`, account teamblossom.ops@gmail.com. Public address: https://pub-dfe2dc87a34d4016a8782237145e0938.r2.dev (rate-limited by Cloudflare; needs a real domain before alot is promoted).
- Allowed web addresses for streaming are set in the bucket's CORS policy: the live site and `127.0.0.1:8765`/`localhost:8765`.
- `tools/` holds the download, encode, upload and publish scripts. Audio files are not in git. The scripts expect `~/music-pipeline/ektoplazm` and were written for one Mac, so paths may need changing.

## Ratings
Likes and dislikes stay on the device. In Configure > Playlist, **Copy my ratings** copies them. `tools/alot_ratings.py` previews what they would change; add `--apply`, then run `tools/ektoplazm_publish.py`, test, and publish.

## Tests
Browser tests using Playwright, in `tests/`. Some paths are written for the original Mac. Example: `python tests/layers.py https://alot-indol.vercel.app/?lang=en`. Before publishing: `gate.py` (takes the Chrome path), then `audit.py`, `layers.py`, `stream.py`, `overnight.py`, `locked_screen.py`, `single_player.py`.

## Not verified
- iPhone, AirPlay and Sonos have not passed a real test. Music was reported silent on an iPhone playing through AirPlay to Sonos on 2026-11-06; cause not yet confirmed.
- Spanish needs a native read. The name "alot" has not been cleared. Music rights need an attorney's look before any commercial use.
