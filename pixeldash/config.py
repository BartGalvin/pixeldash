"""Load dashboard settings from YAML, with defaults for an offline demo."""

from copy import deepcopy
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

PACKAGE_DIR = Path(__file__).parent
ASSETS_DIR = PACKAGE_DIR / "assets"
FONT_DIR = ASSETS_DIR / "fonts"
IMAGE_DIR = ASSETS_DIR / "images"
COLOR_SCHEMES_DIR = ASSETS_DIR / "color_schemes"

DEFAULTS = {
    "display": {"width": 64, "height": 32},
    "emulator": {"pixel_size": 10},
    "dashboard": {"screens": ["clock", "hello"], "interval": 10},
    "matrix": {
        "rows": 32,
        "cols": 64,
        "brightness": 80,
        "chain_length": 1,
        "parallel": 1,
        "hardware_mapping": "adafruit-hat",
        "gpio_slowdown": 1,
        "pwm_lsb_nanoseconds": 80,
        "limit_refresh_rate_hz": 150,
    },
    "font": {"name": "tiny.otf", "size": 5},
    "color_scheme": "Kanagawa",
    "clock": {"show_date": True, "format_24h": True},
    "weather": {"city": "", "units": "imperial", "api_key": None},
    "spotify": {
        "client_id": None,
        "client_secret": None,
        "redirect_uri": "http://127.0.0.1:8888/callback",
        "cache_path": ".spotify_cache",
    },
}


class Config:
    """Merge settings over defaults without changing other Config instances."""

    def __init__(self, config_path: str | Path | None = None):
        self._data = deepcopy(DEFAULTS)
        if config_path is not None:
            self._load(Path(config_path).expanduser())
        else:
            for path in (Path("config.yaml"), Path("config.local.yaml")):
                if path.exists():
                    self._load(path)
        self._validate()

    def _load(self, path: Path) -> None:
        try:
            with path.open(encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {path}") from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"Config must contain a YAML mapping: {path}")
        self._merge_config(data)

    def _merge_config(self, data: dict) -> None:
        def merge(base, override):
            for key, value in override.items():
                if key in base and isinstance(base[key], dict):
                    if not isinstance(value, dict):
                        raise ValueError(f"Config section '{key}' must be a mapping")
                    merge(base[key], value)
                else:
                    base[key] = value

        merge(self._data, data)

    def _validate(self) -> None:
        for key in (
            "display.width", "display.height", "emulator.pixel_size", "font.size",
            "matrix.rows", "matrix.cols", "matrix.chain_length", "matrix.parallel",
        ):
            value = self.get(key)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{key} must be a positive integer")
        interval = self.get("dashboard.interval")
        if type(interval) not in (int, float) or not isfinite(interval) or interval <= 0:
            raise ValueError("dashboard.interval must be a positive number")
        screens = self.get("dashboard.screens")
        if not isinstance(screens, list) or not screens or not all(
            isinstance(name, str) for name in screens
        ):
            raise ValueError("dashboard.screens must be a nonempty list of screen names")
        for key in ("clock.show_date", "clock.format_24h"):
            if type(self.get(key)) is not bool:
                raise ValueError(f"{key} must be true or false")
        for key in ("font.name", "weather.city", "spotify.redirect_uri", "spotify.cache_path"):
            if not isinstance(self.get(key), str):
                raise ValueError(f"{key} must be text")
        if self.get("weather.units") not in ("imperial", "metric"):
            raise ValueError("weather.units must be imperial or metric")

    def get(self, key_path: str) -> Any:
        """Read a dotted setting name, such as display.width."""
        if key_path == "font.path":
            return str(FONT_DIR / self.get("font.name"))
        value = self._data
        for key in key_path.split("."):
            if not isinstance(value, dict) or key not in value:
                raise KeyError(f"Config key not found: {key_path}")
            value = value[key]
        return value


_config: Config | None = None


def configure(config_path: str | Path | None = None) -> Config:
    """Select the configuration used by screens and displays."""
    global _config
    _config = Config(config_path)
    return _config


def get_config() -> Config:
    global _config
    if _config is None:
        return configure()
    return _config
