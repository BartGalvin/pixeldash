"""Import installed RGB matrix bindings or a checkout beside the project."""

import sys
from pathlib import Path


def setup_matrix_path():
    bindings = Path(__file__).resolve().parent.parent / "rpi-rgb-led-matrix" / "bindings" / "python"
    if (bindings / "rgbmatrix").is_dir() and str(bindings) not in sys.path:
        sys.path.insert(0, str(bindings))


def get_matrix_classes():
    setup_matrix_path()
    try:
        from rgbmatrix import RGBMatrix, RGBMatrixOptions
    except ImportError as exc:
        raise RuntimeError(
            "Matrix display requires rpi-rgb-led-matrix Python bindings. "
            "Install them on the Pi, or use --display emulator."
        ) from exc
    return RGBMatrix, RGBMatrixOptions
