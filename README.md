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
```yaml
plugins: lastfmrating
```

---
## 📦 Installation

Clone this repo and place the plugin in your beets plugin directory (usually `~/.config/beets/beetsplug/`):

```bash
git clone https://github.com/yourusername/beets-lastfmrating.git
cp beets-lastfmrating/lastfmrating.py ~/.config/beets/beetsplug/


