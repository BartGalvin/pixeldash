from copy import deepcopy
from importlib.util import find_spec
import os
from unittest import skipUnless
from unittest.mock import Mock, patch

from support import ConfiguredTestCase

HAS_SERVICES = all(find_spec(name) is not None for name in ("requests", "spotipy", "dotenv"))
if HAS_SERVICES:
    import requests
    from pixeldash.services.spotify_service import SpotifyService
    from pixeldash.services.weather_service import WeatherService

WEATHER = {
    "main": {"temp": 20.5},
    "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
}
PLAYBACK = {
    "is_playing": True,
    "progress_ms": 1000,
    "item": {
        "name": "Example Track",
        "artists": [{"name": "Example Artist"}],
        "album": {"name": "Example Album", "images": [{"url": "https://example.com/art.jpg"}]},
        "duration_ms": 180000,
    },
}


@skipUnless(HAS_SERVICES, "optional service dependencies are not installed")
class WeatherTests(ConfiguredTestCase):
    def setUp(self):
        super().setUp()
        dotenv = patch("pixeldash.services.weather_service.load_dotenv")
        dotenv.start()
        self.addCleanup(dotenv.stop)
        self.configure_with('weather: {city: "Example,MA,US", api_key: "test-api-key", units: metric}')

    def test_requests_use_configured_city_and_cache_the_result(self):
        geo = Mock()
        geo.json.return_value = [{"lat": 42.1, "lon": -71.1}]
        weather = Mock()
        weather.json.return_value = WEATHER
        with patch("pixeldash.services.weather_service.requests.get", side_effect=[geo, weather]) as get:
            service = WeatherService()
            self.assertEqual(service.get_temperature(), 20.5)
            self.assertEqual(service.get_icon_code(), "01d")
            self.assertEqual(service.get_description(), "clear sky")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[0].kwargs["params"]["q"], "Example,MA,US")
        self.assertTrue(all(call.args[0].startswith("https://") for call in get.call_args_list))
        self.assertEqual(get.call_args_list[1].kwargs["params"]["units"], "metric")
        geo.raise_for_status.assert_called_once()

    def test_failed_requests_are_not_retried_each_frame_or_logged_with_credentials(self):
        with patch("pixeldash.services.weather_service.requests.get", side_effect=requests.Timeout(
            "https://example.com/?appid=test-api-key"
        )) as get:
            service = WeatherService()
            with self.assertLogs("pixeldash.services.weather_service", level="WARNING") as logs:
                self.assertIsNone(service.get_weather())
                self.assertIsNone(service.get_weather())
        get.assert_called_once()
        self.assertNotIn("test-api-key", " ".join(logs.output))

    def test_empty_geocoding_result_is_handled(self):
        response = Mock()
        response.json.return_value = []
        with patch("pixeldash.services.weather_service.requests.get", return_value=response):
            with self.assertLogs("pixeldash.services.weather_service", level="WARNING"):
                self.assertIsNone(WeatherService().get_weather())

    def test_failed_refresh_keeps_last_good_reading(self):
        service = WeatherService()
        service.cached_data = WEATHER
        service.last_fetch = 0
        with patch("pixeldash.services.weather_service.time.monotonic", return_value=601):
            with patch("pixeldash.services.weather_service.requests.get", side_effect=requests.Timeout):
                with self.assertLogs("pixeldash.services.weather_service", level="WARNING"):
                    self.assertEqual(service.get_temperature(), 20.5)

    def test_missing_credentials_or_city_fail_before_requests(self):
        for text in ('weather: {city: "Example,US"}', 'weather: {api_key: "test-api-key"}'):
            with self.subTest(text=text):
                self.configure_with(text)
                with patch("pixeldash.services.weather_service.requests.get") as get:
                    with self.assertRaises(ValueError):
                        WeatherService()
                get.assert_not_called()

    def test_environment_credentials_take_precedence(self):
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "environment-key"}):
            self.assertEqual(WeatherService().api_key, "environment-key")


@skipUnless(HAS_SERVICES, "optional service dependencies are not installed")
class SpotifyTests(ConfiguredTestCase):
    def setUp(self):
        super().setUp()
        self.configure_with('spotify: {client_id: "test-id", client_secret: "test-secret"}')
        for name in ("load_dotenv", "SpotifyOAuth", "spotipy.Spotify"):
            mocked = patch("pixeldash.services.spotify_service." + name)
            value = mocked.start()
            self.addCleanup(mocked.stop)
            if name == "SpotifyOAuth":
                self.oauth = value
            elif name == "spotipy.Spotify":
                self.client = value.return_value
        self.client.current_playback.return_value = deepcopy(PLAYBACK)

    def test_cached_playback_advances_progress_without_repeated_requests(self):
        with patch("pixeldash.services.spotify_service.time.monotonic", return_value=100) as clock:
            service = SpotifyService()
            first = service.get_current_track()
            clock.return_value = 102
            second = service.get_current_track()
            self.assertEqual(first["progress_ms"], 1000)
            self.assertEqual(second["progress_ms"], 3000)
            self.client.current_playback.assert_called_once()
            clock.return_value = 105
            service.get_current_track()
            self.assertEqual(self.client.current_playback.call_count, 2)

    def test_nothing_playing_is_cached(self):
        self.client.current_playback.return_value = None
        service = SpotifyService()
        self.assertIsNone(service.get_current_track())
        self.assertIsNone(service.get_current_track())
        self.client.current_playback.assert_called_once()

    def test_request_failures_are_cached_and_do_not_echo_credentials(self):
        self.client.current_playback.side_effect = requests.Timeout("private-test-credential")
        service = SpotifyService()
        with self.assertLogs("pixeldash.services.spotify_service", level="WARNING") as logs:
            self.assertIsNone(service.get_current_track())
            self.assertIsNone(service.get_current_track())
        self.client.current_playback.assert_called_once()
        self.assertNotIn("private-test-credential", " ".join(logs.output))

    def test_environment_credentials_and_custom_cache_path(self):
        self.configure_with('spotify: {cache_path: "cache/spotify.json"}')
        with patch.dict(os.environ, {"SPOTIFY_CLIENT_ID": "environment-id", "SPOTIFY_CLIENT_SECRET": "environment-secret"}):
            SpotifyService()
        self.assertEqual(self.oauth.call_args.kwargs["client_id"], "environment-id")
        self.assertEqual(self.oauth.call_args.kwargs["cache_path"], "cache/spotify.json")
        self.assertTrue((self.directory / "cache").is_dir())

    def test_missing_credentials_fail_before_starting_authentication(self):
        self.configure_with("")
        with self.assertRaises(ValueError):
            SpotifyService()
        self.oauth.assert_not_called()
