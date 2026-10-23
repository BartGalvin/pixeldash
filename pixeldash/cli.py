"""Run the dashboard in a desktop window or on an LED matrix."""

import argparse
import time

from pixeldash.config import configure
from pixeldash.display import EmulatorDisplay, MatrixDisplay
from pixeldash.screen_manager import ScreenManager
from pixeldash.screens import SCREENS, create_screen


def run(display, manager):
    """Render at up to 30 FPS and handle emulator controls."""
    previous_frame = time.monotonic()
    while True:
        frame_start = time.monotonic()
        for event in display.poll_input():
            if event == "quit":
                return
            if event == "next":
                manager.next_screen()
            elif event == "previous":
                manager.previous_screen()
        manager.update()
        screen = manager.get_current_screen()
        screen.update(frame_start - previous_frame)
        display.show(screen.render())
        previous_frame = frame_start
        time.sleep(max(0, 1 / 30 - (time.monotonic() - frame_start)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", metavar="PATH", help="read settings from this YAML file")
    parser.add_argument("--display", choices=("emulator", "matrix"), default="emulator")
    parser.add_argument("--screens", nargs="+", choices=SCREENS, help="screens to cycle through")
    parser.add_argument("--interval", type=float, metavar="SECONDS", help="time on each screen")
    args = parser.parse_args(argv)

    display = None
    try:
        config = configure(args.config)
        names = args.screens if args.screens is not None else config.get("dashboard.screens")
        interval = args.interval if args.interval is not None else config.get("dashboard.interval")
        manager = ScreenManager([create_screen(name) for name in names], interval)
        display = EmulatorDisplay() if args.display == "emulator" else MatrixDisplay()
        run(display, manager)
    except KeyboardInterrupt:
        pass
    except ModuleNotFoundError as exc:
        if exc.name in ("requests", "spotipy", "dotenv"):
            parser.exit(2, "Install service support with: python -m pip install '.[services]'\n")
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"pixeldash: {exc}\n")
    finally:
        if display is not None:
            display.close()
    return 0
