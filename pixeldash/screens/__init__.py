"""Built-in screens. Service dependencies load only when a screen is selected."""

from importlib import import_module

SCREENS = {
    "clock": ("clock", "ClockScreen"),
    "hello": ("hello_world", "HelloWorldScreen"),
    "weather": ("weather", "WeatherScreen"),
    "weather-clock": ("weather_clock", "WeatherClockScreen"),
    "spotify": ("spotify", "SpotifyScreen"),
}

__all__ = [class_name for _, class_name in SCREENS.values()]


def create_screen(name):
    if name not in SCREENS:
        raise ValueError(f"Unknown screen '{name}'. Choose from: {', '.join(SCREENS)}")
    module, class_name = SCREENS[name]
    return getattr(import_module(f"pixeldash.screens.{module}"), class_name)()


def __getattr__(name):
    # Keep the existing `from pixeldash.screens import ClockScreen` interface.
    for module, class_name in SCREENS.values():
        if name == class_name:
            return getattr(import_module(f"pixeldash.screens.{module}"), class_name)
    raise AttributeError(name)
