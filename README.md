# alot

Sound for what you need right now: purposes with curated music and noise, a mixer, and a projector mode. Live: https://alot-indol.vercel.app (Spanish by default, EN/ES at the top).

## Use it
Open the link in a phone or computer browser. Nothing to install, no sign-in.

- **Purposes**, from most energy to least: **Run, Flow, Ground, Meditate, Love, Sleep**, then **Noise only**. Tap one to play its pre-mixed stream; tap again to stop. Like, Dislike and Next act on the track playing.
  - **Noise only** plays brown, pink or white noise on its own, one seamless hour-long loop per color.
  - **Sleep** is the Night Arc: music fading out over the first hour, then noise to six hours.
- **Choose speaker** (top) opens the AirPlay list where the browser offers it. Every purpose is one stream, so it carries to Sonos through AirPlay.
- **Projector** (top, on computers and large screens): full-screen light that follows the music. Four visuals (Silk, Aurora, Bloom, Flower: four whorls of translucent petals that open and close with the song's tempo, outer whorls a moment later), the purpose's mood colors with your accent color as the light. Esc exits, Space plays or stops, → skips a track.
  - **Sync:** AirPlay and Sonos play about 2 s late, so the picture waits for them. Nudge with the Sync slider, press **Tap to the beat** (or **T**) four times on the kick, or use **Flash beats** to compare by eye. Off with Less motion.
- **Customize** opens the mixer: generated noise, a playlist with Shuffle, one Play for both. AirPlay carries one stream, so through a speaker the mixer's noise and music do not play together.
- **Settings (gear):** background, accent color, **Layout** (home screen List, Tiles, Compact or Large; icons; button shape), sizes, sound and phone options.

## Code
- Work is on branch **`revive-noise-studio`**; `main` is updated from it when GitHub Pages is off (see below).
- `index.html` is the whole app, plain HTML, CSS and JavaScript with no build step. `tracks/manifest.json` lists the library; `tracks/modes.json` lists the purpose streams and their chapters. `credits.html` is generated.
- Publish from this folder only: `vercel deploy --prod --yes` (Vercel project `teamblossom/alot`). Run the tests first; a push alone does not publish.

## Music
- 100 tracks from 15 Ektoplazm releases, Creative Commons, evened out in loudness. Treat all of them as **non-commercial**. Credits and licenses: `credits.html`.
- Streamed from Cloudflare R2, bucket `alot-music`, account teamblossom.ops@gmail.com: https://pub-dfe2dc87a34d4016a8782237145e0938.r2.dev (rate-limited by Cloudflare; needs a real domain before alot is promoted). Allowed sites are set in the bucket's CORS policy.
- `tools/` holds the download, encode, analysis, mix, upload and publish scripts. Audio files are not in git. The scripts expect `~/music-pipeline/ektoplazm` and were written for one Mac.

## How the purposes are made
- `tools/track_features.py` measures every track: beat clarity, share of drums, brightness, bass, loudness, punch.
- `tools/mode_mix.py` picks each purpose's tracks from those measurements (each track belongs to one purpose; Sleep keeps the Night Arc), crossfades them into one file per purpose, and writes `modes.json`. Re-rendered mixes get a new file name (`-v2`), because files are cached for a year.
  - Meditate: no drums, hardly any beat. Love: slow, warm, deep bass, few drums, quietest at both ends. Flow: a steady, clear beat. Ground: dub and bass. Run: psytrance climbing to drum and bass.
- `tools/mode_envelope.py` analyses each mix for the projector: levels 40 times a second, every beat with its strength, the tempo, and drops and calms. Files: `modes/env/<mix>.v2.bin` and `.v2.json` on R2.

## Ratings
- **Like** marks the track for that purpose; **Dislike** skips it and keeps it skipped there on that device. Votes are stored as `purpose--track`.
- Votes go to a Cloudflare Worker and D1 database (`worker/`, `alot-ratings`) with a random device ID, the track and the vote. No names, emails or IP addresses. The address is write-only.
- Changing the shared mixes needs a person's review: `tools/alot_ratings.py` shows the votes; `--apply` saves the changes. Rules: remove at 2 or more dislikes with more dislikes than likes; favor when likes outnumber dislikes; otherwise no change.

## Battery
alot runs all night: nothing animates, polls or wakes on a timer while idle. The projector draws only while open (about 18% of a core) and frees its graphics memory when closed. Tests fail if idle playback uses over 10% of a core.

## Tests
Browser tests with Playwright in `tests/`; some paths are written for the original Mac. Before publishing: `gate.py` (takes the Chrome path), `audit.py` (Chrome path and URL, `#mix`), `modes.py` and `projector.py` (URL with `?lang=en`), `layers.py`, `speaker.py`, `stream.py` (URL with `?lang=en#mix`), plus `overnight.py`, `locked_screen.py`, `single_player.py`.

## Not yet verified
- By ear: the curated purpose lists and the music and noise balance. Real overnight battery on a phone. The projector on a real projector with Sonos.
- Spanish needs a native read. The name "alot" has not been cleared. Music rights need an attorney's look before any commercial use.
