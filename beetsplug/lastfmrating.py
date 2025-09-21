# lastfmrating.py
# Beets plugin: fetch Last.fm listeners and map to ratings, push to Kodi

import json
import urllib.parse
import urllib.request
import base64

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand


class LastfmRating(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.config.add({
            'apikey': None,
            'min_listener_cutoff': 1000,
            'fallback_cutoff': 10000,
            'push_to_kodi': True,
            'debug_api': False,          # << toggle for -vv logging
            'strict_album_match': False, # << new flag for fallback behavior
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
    # Kodi core request
    # ------------------------
    def kodi_request(self, payload):
        kodi_cfg = self.config['kodi']
        host = kodi_cfg['host'].get()
        port = kodi_cfg['port'].get()
        user = kodi_cfg['user'].get()
        password = kodi_cfg['password'].get()

        if not host:
            return None, "Kodi host not configured"

        url = f"http://{host}:{port}/jsonrpc"
        headers = {"Content-Type": "application/json"}
        if user and password:
            creds = f"{user}:{password}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(creds).decode("utf-8")

        data = json.dumps(payload).encode("utf-8")

        if self.config['debug_api'].get():
            self._log.debug("Kodi request URL: {}", url)
            self._log.debug("Kodi request payload: {}", json.dumps(payload))

        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req) as resp:
                result = json.load(resp)
                if self.config['debug_api'].get():
                    self._log.debug("Kodi response: {}", json.dumps(result))
                return result, None
        except Exception as e:
            return None, str(e)

    # ------------------------
    # Kodi ID lookups with optional fallback
    # ------------------------
    def get_kodi_songid(self, artist, title, album=None):
        base_filter = [
            {"field": "artist", "operator": "is", "value": artist},
            {"field": "title", "operator": "is", "value": title}
        ]
        if album:
            base_filter.append({"field": "album", "operator": "is", "value": album})

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "AudioLibrary.GetSongs",
            "params": {
                "filter": {"and": base_filter},
                "properties": ["title", "rating", "albumid", "album"]
            }
        }

        resp, err = self.kodi_request(payload)
        songs = []
        if not err and resp and "result" in resp and "songs" in resp["result"]:
            songs = resp["result"].get("songs") or []

        # Fallback if strict_album_match is False
        if not songs and album and not self.config['strict_album_match'].get():
            self._log.warning(
                "No exact match for '{} - {}' in album '{}', retrying without album filter",
                artist, title, album
            )
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
    # Last.fm fetchers
    # ------------------------
    def fetch_track_listeners(self, artist, title):
        api_key = self.config['apikey'].get()
        if not api_key:
            return 0

        url = (
            f"http://ws.audioscrobbler.com/2.0/?method=track.getInfo"
            f"&api_key={api_key}&artist={urllib.parse.quote(artist)}"
            f"&track={urllib.parse.quote(title)}&format=json"
        )

        try:
            with urllib.request.urlopen(url) as resp:
                data = json.load(resp)
                listeners = int(data['track']['listeners'])
                return listeners
        except Exception:
            return 0

    # ------------------------
    # Rating calculation
    # ------------------------
    def map_listeners_to_rating(self, listeners, min_listeners, max_listeners):
        min_cutoff = self.config['min_listener_cutoff'].get()
        if listeners <= min_cutoff:
            return 1
        if max_listeners == min_listeners:
            return 5
        cutoff = min_listeners + 0.95 * (max_listeners - min_listeners)
        listeners_capped = min(listeners, cutoff)
        rating = 1 + 9 * (listeners_capped - min_listeners) / (cutoff - min_listeners)
        return max(1, min(10, int(round(rating))))

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
            "params": {"songid": songid, "rating": float(rating)},
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

    # ------------------------
    # Main processor
    # ------------------------
    def process_album(self, album, pretend=False):
        artist = album.albumartist
        album_title = album.album

        track_listeners = []
        for item in album.items():
            listeners = self.fetch_track_listeners(artist, item.title)
            track_listeners.append(listeners)

        if not track_listeners:
            return

        min_listeners = min(track_listeners)
        max_listeners = max(track_listeners)

        ratings = []
        for item, listeners in zip(album.items(), track_listeners):
            rating = self.map_listeners_to_rating(listeners, min_listeners, max_listeners)
            ratings.append(rating)

            # Always show pretend output, show real ratings only with -v
            log_fn = self._log.info if pretend else self._log.debug
            log_fn(
                "{}Set Rating={} for track '{}' ({} listeners)",
                "[Pretend] " if pretend else "",
                rating, item.title, listeners
            )

            if not pretend:
                item['lastfm_track_rating'] = rating
                item.store()
                self.push_track_rating(artist, item.title, album_title, rating, pretend)

        album_rating = float(median(ratings))
        log_fn = self._log.info if pretend else self._log.debug
        log_fn(
            "{}Set AlbumRating={:.1f} (median of {} tracks) for album '{}'",
            "[Pretend] " if pretend else "",
            album_rating, len(ratings), album_title
        )

        if not pretend:
            album['lastfm_album_rating'] = album_rating
            album.store()
            self.push_album_rating(artist, album_title, album_rating, pretend)

    def func(self, lib, opts, args):
        query = args if args else None
        albums = lib.albums(query)
        for album in albums:
            self.process_album(album, pretend=opts.pretend)


def median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    else:
        return s[mid]
