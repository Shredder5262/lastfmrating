Skip to content
Navigation Menu
Shredder5262
lastfmrating

Type / to search
Code
Issues
Pull requests
Actions
Projects
Wiki
Security
Insights
Settings
lastfmrating
/
README.md
in
main

Edit

Preview
Indent mode

Spaces
Indent size

2
Line wrap mode

Soft wrap
Editing README.md file contents
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
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


Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
No file chosen
Attach files by dragging & dropping, selecting or pasting them.
Editing lastfmrating/README.md at main · Shredder5262/lastfmrating
Focus on filter text box and list of items, Focused item: VisualStudio, not selected, 147 of 156
