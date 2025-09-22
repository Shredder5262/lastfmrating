# lastfmrating.py
# Beets plugin: fetch Last.fm listeners and map to ratings, push to Kodi

import json
import urllib.parse
import urllib.request
import base64
import time
import math
import re
import unicodedata

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand


def median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n == 0:
        return 0.0
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    else:
        return float(s[mid])


class LastfmRating(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.config.add({
            'apikey': None,
            'min_listener_cutoff': 1000,
            'fallback_cutoff': 10000,
            'push_to_kodi': True,
            'debug_api': False,
            'strict_album_match': False,
            'kodi': {
                'host': None,
                'port': 8080,
                'user': None,
                'password': None,
            },
        })

        # Subcommand
        self._subcommand = Subcommand(
            'lastfmrating',
            help='Fetch Last.fm listeners and map to ratings'
        )
        self._subcommand.parser.add_option(
            '--pretend',
            action='store_true',
            help="show what would happen, but don’t write changes or push to Kodi"
        )
        self._subcommand.func = self.func

    def commands(self):
        return [self._subcommand]

    # ------------------------
    # Helpers: normalization
    # ------------------------
    def _norm_text(self, s):
        if not isinstance(s, str):
            return ''
        s = unicodedata.normalize('NFKC', s)
        s = s.replace('’', "'").replace('‘', "'").replace('`', "'")
        s = s.replace('“', '"').replace('”', '"')
        s = s.replace('–', '-').replace('—', '-')
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def _strip_feat(self, title):
        t = re.sub(r'\s*[\(\[]?(feat\.|featuring|ft\.)[^)\]]*[\)\]]?', '', title, flags=re.I)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def _same_title(self, a, b):
        def canon(x):
            x = self._norm_text(x).lower()
            x = self._strip_feat(x)
            x = re.sub(r'\s*-\s*(remaster(ed)?\s*\d{2,4}|remix|radio edit|album version|single version|clean|dirty|explicit|instrumental).*$', '', x, flags=re.I)
            x = re.sub(r'\s*\((remaster(ed)?\s*\d{2,4}|remix|radio edit|album version|single version|clean|dirty|explicit|instrumental)\)\s*$', '', x, flags=re.I)
            x = re.sub(r'\s+', ' ', x).strip()
            return x
        return canon(a) == canon(b)

    # ------------------------
    # HTTP utilities
    # ------------------------
    def _http_get_json(self, url, retry=3, timeout=10):
        headers = {
            "User-Agent": "beets-lastfmrating/1.0 (+https://beets.io)"
        }
        last_err = None
        for attempt in range(1, retry + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    return json.loads(raw.decode('utf-8')), None
            except Exception as e:
                last_err = str(e)
                if self.config['debug_api'].get():
                    self._log.debug("HTTP GET failed (attempt {}): {}", attempt, last_err)
                time.sleep(min(2 ** (attempt - 1), 4))
        return None, last_err

    # ------------------------
    # Last.fm fetchers
    # ------------------------
    def fetch_track_listeners(self, artist, title):
        api_key = self.config['apikey'].get()
        if not api_key:
            self._log.debug("No Last.fm API key configured; returning 0 listeners")
            return 0

        artist_norm = self._norm_text(artist)
        title_norm = self._norm_text(title)

        def build_getinfo(a, t):
            return (
                "https://ws.audioscrobbler.com/2.0/?method=track.getInfo"
                "&autocorrect=1"
                f"&api_key={urllib.parse.quote(api_key)}"
                f"&artist={urllib.parse.quote(a)}"
                f"&track={urllib.parse.quote(t)}"
                "&format=json"
            )

        def build_search(a, t):
            return (
                "https://ws.audioscrobbler.com/2.0/?method=track.search"
                f"&api_key={urllib.parse.quote(api_key)}"
                f"&artist={urllib.parse.quote(a)}"
                f"&track={urllib.parse.quote(t)}"
                "&limit=10&format=json"
            )

        # 1) Exact
        url = build_getinfo(artist_norm, title_norm)
        data, err = self._http_get_json(url)
        if data and isinstance(data, dict) and 'track' in data and 'listeners' in data['track']:
            try:
                listeners = int(data['track']['listeners'])
                self._log.debug("[Last.fm:getInfo] {} - {} → {} listeners", artist, title, listeners)
                return listeners
            except Exception:
                pass

        # 2) Strip feat
        t2 = self._strip_feat(title_norm)
        if t2 != title_norm:
            url2 = build_getinfo(artist_norm, t2)
            data2, err2 = self._http_get_json(url2)
            if data2 and isinstance(data2, dict) and 'track' in data2 and 'listeners' in data2['track']:
                try:
                    listeners = int(data2['track']['listeners'])
                    self._log.debug("[Last.fm:getInfo:strip] {} - {} → {} listeners", artist, t2, listeners)
                    return listeners
                except Exception:
                    pass

        # 3) Search
        url3 = build_search(artist_norm, title_norm)
        data3, err3 = self._http_get_json(url3)
        best = 0
        if data3 and isinstance(data3, dict):
            tracks = (data3.get('results', {}) or {}).get('trackmatches', {}) or {}
            matches = tracks.get('track', []) or []
            if isinstance(matches, dict):
                matches = [matches]
            for m in matches:
                name = m.get('name') or ''
                art = m.get('artist') or ''
                try:
                    lis = int(m.get('listeners') or 0)
                except Exception:
                    lis = 0
                if self._same_title(name, title_norm) and self._norm_text(art).lower() == artist_norm.lower():
                    best = max(best, lis)
                else:
                    best = max(best, lis)
        self._log.debug("[Last.fm:search] {} - {} → {} listeners (best)", artist, title, best)
        return best

    # ------------------------
    # Rating calculation: Hybrid
    # ------------------------
    def map_album_listeners_to_ratings(self, listeners_list):
        vals = [max(0, int(x or 0)) for x in listeners_list]
        if not vals or all(v == 0 for v in vals):
            return [5 for _ in vals]

        # Global base scale: log10 up to 1M listeners
        logs = [math.log10(v + 1.0) for v in vals]
        lo_global, hi_global = 0.0, 6.0
        base_ratings = []
        for lv in logs:
            t = (lv - lo_global) / (hi_global - lo_global)
            r = 1 + 9 * max(0.0, min(1.0, t))
            base_ratings.append(r)

        # Album-relative adjustment
        lo_album, hi_album = min(vals), max(vals)
        adjusted = []
        for v, base in zip(vals, base_ratings):
            if hi_album > lo_album:
                rel = (v - lo_album) / (hi_album - lo_album)
            else:
                rel = 0.5
            adj = (rel - 0.5) * 3.0  # ±1.5
            final = base + adj
            adjusted.append(int(round(max(1, min(10, final)))))

        return adjusted

    # ------------------------
    # Kodi core request
    # ------------------------
    def kodi_request(self, payload, retry=3, timeout=10):
        kodi_cfg = self.config['kodi']
        host = kodi_cfg['host'].get()
        port = kodi_cfg['port'].get()
        user = kodi_cfg['user'].get()
        password = kodi_cfg['password'].get()

        if not host:
            return None, "Kodi host not configured"

        url = "http://{}:{}/jsonrpc".format(host, port)
        headers = {"Content-Type": "application/json"}
        if user and password:
            creds = "{}:{}".format(user, password).encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(creds).decode("utf-8")

        data = json.dumps(payload).encode("utf-8")

        if self.config['debug_api'].get():
            self._log.debug("Kodi request URL: {}", url)
            self._log.debug("Kodi request payload: {}", json.dumps(payload))

        last_err = None
        for attempt in range(1, retry + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = json.load(resp)
                    if self.config['debug_api'].get():
                        self._log.debug("Kodi response: {}", json.dumps(result))
                    return result, None
            except Exception as e:
                last_err = str(e)
                self._log.debug("Kodi request failed (attempt {}): {}", attempt, last_err)
                time.sleep(min(2 ** (attempt - 1), 4))

        return None, last_err

    # ------------------------
    # Kodi helpers
    # ------------------------
    def get_kodi_songid(self, artist, title, album=None):
        base_filter = [
            {"field": "artist", "operator": "is", "value": artist},
            {"field": "title", "operator": "is", "value": title},
        ]
        if album:
            base_filter.append({"field": "album", "operator": "is", "value": album})

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "AudioLibrary.GetSongs",
            "params": {
                "filter": {"and": base_filter},
                "properties": ["title", "album", "albumid", "userrating"]
            }
        }

        resp, err = self.kodi_request(payload)
        songs = []
        if not err and resp and "result" in resp and "songs" in resp["result"]:
            songs = resp["result"].get("songs") or []

        if not songs and album and not self.config['strict_album_match'].get():
            self._log.debug("No exact song match in album; retrying without album filter for '{}' - '{}'", artist, title)
            payload["params"]["filter"]["and"] = [
                {"field": "artist", "operator": "is", "value": artist},
                {"field": "title", "operator": "is", "value": title}
            ]
            resp, err = self.kodi_request(payload)
            if not err and resp and "result" in resp and "songs" in resp["result"]:
                songs = resp["result"].get("songs") or []

        return songs[0].get("songid") if songs else None

    def get_kodi_albumid_via_song(self, artist, album):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "AudioLibrary.GetSongs",
            "params": {
                "filter": {"and": [
                    {"field": "artist", "operator": "is", "value": artist},
                    {"field": "album", "operator": "is", "value": album}
                ]},
                "properties": ["albumid"],
                "limits": {"start": 0, "end": 1}
            }
        }
        resp, err = self.kodi_request(payload)
        if err or not resp or "result" not in resp or "songs" not in resp["result"]:
            return None
        songs = resp["result"].get("songs") or []
        return songs[0].get("albumid") if songs else None

    # ------------------------
    # Kodi pushers
    # ------------------------
    def push_track_rating(self, artist, title, album, rating, pretend=False):
        if not self.config['push_to_kodi'].get() or pretend:
            return
        songid = self.get_kodi_songid(artist, title, album)
        if not songid:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "AudioLibrary.SetSongDetails",
            "params": {"songid": songid, "userrating": int(rating)},
        }
        self.kodi_request(payload)

    def push_album_rating(self, artist, album_title, rating, pretend=False):
        if not self.config['push_to_kodi'].get() or pretend:
            return
        albumid = self.get_kodi_albumid_via_song(artist, album_title)
        if not albumid:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "AudioLibrary.SetAlbumDetails",
            "params": {"albumid": albumid, "rating": float(rating)},
        }
        self.kodi_request(payload)

    def kodi_refresh_container(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Input.ExecuteAction",
            "params": {"action": "Container.Refresh"}
        }
        self.kodi_request(payload)

    # ------------------------
    # Main processor
    # ------------------------
    def process_album(self, album, pretend=False):
        artist = album.albumartist
        album_title = album.album

        self._log.info("Processing album '{}' by {}", album_title, artist)

        track_titles = [it.title for it in album.items()]
        listeners_list = []
        for t in track_titles:
            listeners = self.fetch_track_listeners(artist, t)
            listeners_list.append(listeners)

        ratings = self.map_album_listeners_to_ratings(listeners_list)

        any_pushed = False
        for item, listeners, rating in zip(album.items(), listeners_list, ratings):
            if pretend:
                self._log.info("[Pretend] Set Rating={} for track '{}' ({} listeners)", rating, item.title, listeners)
            else:
                item['lastfm_track_rating'] = rating
                item.store()
                self.push_track_rating(artist, item.title, album_title, rating, pretend=False)
                any_pushed = True
                self._log.debug("Set Rating={} for track '{}' ({} listeners)", rating, item.title, listeners)

        if ratings:
            album_rating = round(sum(ratings) / float(len(ratings)), 1)
        else:
            album_rating = 0.0

        if pretend:
            self._log.info("[Pretend] Set AlbumRating={} for album '{}'", album_rating, album_title)
        else:
            album['lastfm_album_rating'] = album_rating
            album.store()
            self.push_album_rating(artist, album_title, album_rating, pretend=False)
            any_pushed = True
            self._log.debug("Set AlbumRating={} for album '{}'", album_rating, album_title)

        if any_pushed and not pretend:
            self.kodi_refresh_container()

        return any_pushed

    def func(self, lib, opts, args):
        query = args if args else None
        albums = lib.albums(query)

        did_push_any = False
        for album in albums:
            pushed = self.process_album(album, pretend=opts.pretend)
            did_push_any = did_push_any or pushed
