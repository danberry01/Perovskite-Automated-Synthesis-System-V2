from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from gui import App
from mock_runtime import create_mock_runtime


def _configure_logging():
    logger = logging.getLogger("Main Logger")
    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)s\t%(asctime)s: %(message)s"))
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    return logger


def _set_working_directory():
    src_dir = Path(__file__).resolve().parent
    os.chdir(src_dir)
    return src_dir


def build_app(camera_index: int = 0, use_local_camera: bool = True):
    _set_working_directory()
    _configure_logging()

    dispatcher, move_registry, procedure_handler = create_mock_runtime(
        camera_index=camera_index,
        use_local_camera=use_local_camera,
    )
    app = App(
        move_registry=move_registry,
        dispatcher=dispatcher,
        procedure_handler=procedure_handler,
        show_splash=False,
    )
    move_registry.spectrometer_frame = app.tab_view_frame.procedure_viewer_frame.spectrometer_frame
    return app


def _parse_args():
    parser = argparse.ArgumentParser(description="Launch the PASS GUI with mocked hardware and an optional local camera.")
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="OpenCV camera device index to use for the local webcam.",
    )
    parser.add_argument(
        "--mock-camera",
        action="store_true",
        help="Use the placeholder mock camera instead of a real local webcam.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    app = build_app(camera_index=args.camera_index, use_local_camera=not args.mock_camera)
    app.mainloop()


if __name__ == "__main__":
    main()