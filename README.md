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
- **Like:** marks the track; it comes up about 3x sooner in shuffles on that device. Tap again to take it back.
- **Dislike:** skips to the next track, removes it from the list, and keeps it out of shuffles on that device. Undo reverses it; adding it again from the Library clears it.
- Votes go to a Cloudflare Worker and D1 database (`worker/`, `alot-ratings`, account teamblossom.ops@gmail.com) with a random device ID, the track and the vote. No names, emails or IP addresses are stored. The address is write-only. Votes send only on a tap, on load if some are waiting, or on reconnecting.
- Shared changes need a person's review. `tools/alot_ratings.py` shows them; `--apply` saves them; then run `tools/ektoplazm_publish.py`, test, and publish. Rules: remove at 2 or more dislikes with more dislikes than likes; favor when likes outnumber dislikes; otherwise no change.

## Battery
alot runs all night. No endless animation, polling or idle timers. `tests/overnight.py` fails if idle playback uses over 10% of a processor core.

## Tests
Browser tests using Playwright, in `tests/`. Some paths are written for the original Mac. Example: `python tests/layers.py https://alot-indol.vercel.app/?lang=en`. Before publishing: `gate.py` (takes the Chrome path), then `audit.py`, `layers.py`, `stream.py`, `overnight.py`, `speaker.py`, `locked_screen.py`, `single_player.py`.

## Not verified
- iPhone, AirPlay and Sonos have not passed a real test. Music was reported silent on an iPhone playing through AirPlay to Sonos on 2026-11-06; cause not yet confirmed.
- Spanish needs a native read. The name "alot" has not been cleared. Music rights need an attorney's look before any commercial use.
