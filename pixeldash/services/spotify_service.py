"""
Spotify service - fetches currently playing track
"""

import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional, Dict
from pixeldash.config import get_config


logger = logging.getLogger(__name__)


class SpotifyService:
    """Service for fetching Spotify currently playing track"""

    def __init__(self):
        config = get_config()

        # Get credentials from environment variables
        load_dotenv(".env")
        client_id = os.getenv("SPOTIFY_CLIENT_ID") or config.get("spotify.client_id")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") or config.get("spotify.client_secret")
        redirect_uri = config.get("spotify.redirect_uri")

        if not client_id or not client_secret:
            raise ValueError(
                "Set spotify.client_id and spotify.client_secret in your config, "
                "or SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
            )

        cache_path = Path(config.get("spotify.cache_path")).expanduser()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cached_track = None
        self._last_fetch = None

        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope="user-read-currently-playing user-read-playback-state",
                cache_path=str(cache_path),
            ),
            requests_timeout=5,
            retries=0,
            status_retries=0,
        )

    def get_current_track(self) -> Optional[Dict]:
        """
        Get currently playing track.

        Returns:
            Dict with track info or None if nothing playing
        """
        now = time.monotonic()
        if self._last_fetch is None or now - self._last_fetch >= 5:
            self._cached_track = self._fetch_current_track()
            self._last_fetch = time.monotonic()
        if self._cached_track is None:
            return None
        track = self._cached_track.copy()
        track["progress_ms"] = min(
            track["duration_ms"],
            track["progress_ms"] + int((time.monotonic() - self._last_fetch) * 1000),
        )
        return track

    def _fetch_current_track(self) -> Optional[Dict]:
        try:
            current = self.sp.current_playback()

            if not current or not current.get("is_playing"):
                return None

            track = current["item"]
            if not track:
                return None

            return {
                "name": track["name"],
                "artist": ", ".join([artist["name"] for artist in track["artists"]]),
                "album": track["album"]["name"],
                "album_art_url": (
                    track["album"]["images"][0]["url"] if track["album"]["images"] else None
                ),
                "is_playing": current["is_playing"],
                "progress_ms": current.get("progress_ms", 0),
                "duration_ms": track.get("duration_ms", 0),
            }

        except (spotipy.SpotifyException, requests.RequestException, KeyError, TypeError):
            logger.warning("Could not fetch Spotify playback; retrying in 5 seconds.")
            return None

    def get_track_name(self) -> Optional[str]:
        """Get current track name"""
        track = self.get_current_track()
        return track["name"] if track else None

    def get_artist_name(self) -> Optional[str]:
        """Get current artist name"""
        track = self.get_current_track()
        return track["artist"] if track else None

    def get_album_art_url(self) -> Optional[str]:
        """Get album art URL"""
        track = self.get_current_track()
        return track["album_art_url"] if track else None
