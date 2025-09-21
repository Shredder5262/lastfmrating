# 🎵 beets-lastfmrating

A [beets](https://beets.io/) plugin that **fetches Last.fm listener stats and maps them to ratings** for your music library — with optional **push-to-Kodi integration**.

---

## ✨ Features
- 🔗 **Last.fm integration** – fetch track listener counts via Last.fm API  
- 📊 **Smart rating mapping** – normalize listeners to a 1–10 rating scale  
- 💿 **Album ratings** – compute album rating as the median of track ratings  
- 📺 **Kodi support** – automatically push track and album ratings into your Kodi library (`rating` for tracks, `fRating` for albums)  
- 🛠 **Configurable behavior**
  - `--pretend` mode (dry-run, no database writes)  
  - `debug_api` flag for full API request/response logging  
  - `push_to_kodi` toggle to enable/disable Kodi syncing  
  - `strict_album_match` option to avoid false positives on compilations and greatest hits  
- 📌 **Beets fields**
  - `lastfm_track_rating` (per track)  
  - `lastfm_album_rating` (per album)  

---
Enable it in your beets config.yaml:
```yaml
plugins: lastfmrating
```
⚙️ Configuration
Add to your config.yaml:
```yaml
lastfmrating:
  apikey: YOUR_LASTFM_API_KEY
  push_to_kodi: true
  debug_api: false
  strict_album_match: false
  kodi:
    host: 192.168.1.100
    port: 8080
    user: kodi
    password: secret
```
- `apikey`: Your Last.fm API key
- `push_to_kodi`: Push ratings into Kodi (default: true)
- `debug_api`: Print full API request/response logs (default: false)
- `strict_album_match`: Only update tracks that belong to the album currently being processed (helps with compilations)
---
🚀 Usage
Fetch and apply ratings for all albums by an artist:
```bash
beet lastfmrating artist:"Alice in Chains"
```
Preview changes without writing:
```bash
beet lastfmrating artist:"Alice in Chains" --pretend
```
Verbose output with ratings:
```bash
beet -v lastfmrating artist:"40 Below Summer"
```
Extra-verbose with raw API debug logs:
```bash
beet -vv lastfmrating artist:"40 Below Summer"
```
🖥 Example Output
Pretend mode (--pretend)
```bash
lastfmrating: [Pretend] Set Rating=8 for track 'Rain' (20061 listeners)
lastfmrating: [Pretend] Set AlbumRating=6.5 (median of 10 tracks) for album 'The Mourning After'
```
Verbose (-v)
```bash
lastfmrating: Set Rating=7 for track 'Taxi Cab Confession' (16712 listeners)
lastfmrating: Set AlbumRating=5.0 (median of 12 tracks) for album 'Invitation to the Dance'
```
Debug (-vv + debug_api: true)
```bash
lastfmrating: Kodi request URL: http://192.168.1.100:8080/jsonrpc
lastfmrating: Kodi request payload: {"jsonrpc": "2.0", "id": 1, "method": "AudioLibrary.SetSongDetails", ...}
lastfmrating: Kodi response: {"id": 1, "jsonrpc": "2.0", "result": "OK"}
```

---
## 📦 Installation

Clone this repo and place the plugin in your beets plugin directory (usually `~/.config/beets/beetsplug/`):

```bash
git clone https://github.com/yourusername/beets-lastfmrating.git
cp beets-lastfmrating/lastfmrating.py ~/.config/beets/beetsplug/
```
📷 Screenshots
### Ratings pushed into Kodi
![Kodi album rating](screenshots/2025-09-21 14_46_10-Kodi.png)
