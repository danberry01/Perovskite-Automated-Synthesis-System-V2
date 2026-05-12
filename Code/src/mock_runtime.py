from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta
from typing import Callable

import numpy as np

from drivers.camera_driver import Camera
from drivers.procedure_file_driver import ProcedureFile

# Test functions for running the gui without hardware connected.

LOGGER_NAME = "Main Logger"


def _logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def _load_locations() -> list:
    try:
        locations = ProcedureFile().Open("persistant/locations.yml")
        if isinstance(locations, list) and locations:
            return locations
    except Exception:
        _logger().debug("Falling back to mock locations", exc_info=True)

    return [
        ["home", 0, 0, 0],
        ["camera", 125, 75, 40],
        ["hotplate", 250, 150, 20],
    ]


class MockConnectionDevice:
    def __init__(self, name: str):
        self.name = name
        self.logger = _logger()
        self._connected = False

    def connect(self):
        self._connected = True
        self.logger.info("Mock %s connected", self.name)
        return True

    def disconnect(self):
        if self._connected:
            self.logger.info("Mock %s disconnected", self.name)
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def send_message(self, message: str):
        self.logger.info("[%s] %s", self.name, message)


class MockControlBoard(MockConnectionDevice):
    def __init__(self):
        super().__init__("control board")
        self.positions = {"X": 0.0, "Y": 0.0, "Z": 0.0, "A": 0.0, "B": 0.0}
        self.received_ok = threading.Event()
        self._kill_event = threading.Event()

    def connect(self):
        self._kill_event.clear()
        return super().connect()

    def kill(self):
        self._kill_event.set()
        self.received_ok.set()
        self.logger.warning("Mock emergency stop requested")

    def reset_kill(self):
        self._kill_event.clear()

    def is_killed(self) -> bool:
        return self._kill_event.is_set()

    def request_position(self, wait: bool = False, timeout: float = 1.0):
        return self.positions.copy()


class MockCamera:
    def __init__(self, width: int = 600, height: int = 400):
        self.logger = _logger()
        self._connected = False
        self._width = width
        self._height = height
        self._frame = self._build_placeholder_frame(width, height)

    def _build_placeholder_frame(self, width: int, height: int):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = 35
        frame[:, :, 1] = 70
        frame[:, :, 2] = 95
        frame[20:60, 20:width - 20, :] = (60, 120, 160)
        frame[height - 60:height - 20, 20:width - 20, :] = (20, 40, 55)
        return frame

    def connect(self, device_index: int = 0, width: int = None, height: int = None):
        if width is not None and height is not None:
            self._width = int(width)
            self._height = int(height)
            self._frame = self._build_placeholder_frame(self._width, self._height)
        self._connected = True
        self.logger.info("Mock camera connected")
        return True

    def disconnect(self):
        self._connected = False
        self.logger.info("Mock camera disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def get_frame(self):
        if not self._connected:
            return None
        return self._frame.copy()


class MockArucoDetector:
    def detect_markers(self, frame):
        return {"frame": frame, "count": 0, "markers": []}

    def log_detection_results(self, result):
        return None


class MockHotplate(MockConnectionDevice):
    def __init__(self):
        super().__init__("hotplate")
        self.current_temperature_c = 25
        self.target_temperature_c = 25

    def set_temperature(self, temperature):
        self.target_temperature_c = temperature
        self.current_temperature_c = temperature
        self.logger.info("Mock hotplate target set to %s C", temperature)


class MockSpinCoater(MockConnectionDevice):
    def __init__(self):
        super().__init__("spin coater")
        self.done = threading.Event()
        self.last_rpm = None
        self.is_running = False

    def add_step(self, rpm: int, time_seconds: int):
        self.last_rpm = rpm
        self.logger.info("Mock spin step added: %s rpm for %s s", rpm, time_seconds)

    def clear_steps(self):
        self.logger.info("Mock spin steps cleared")

    def stop(self):
        self.is_running = False
        self.done.set()
        self.logger.info("Mock spin coater stopped")

    def run(self, wait_to_finish: bool = False, timeout: float = 120.0):
        self.is_running = True
        self.done.clear()

        def _finish():
            time.sleep(0.1)
            self.is_running = False
            self.done.set()

        threading.Thread(target=_finish, daemon=True).start()
        if wait_to_finish:
            self.done.wait(timeout=timeout)


class MockSpectrometer(MockConnectionDevice):
    def __init__(self):
        super().__init__("spectrometer")
        self.measurements = {}

    def send_command(self, command: str):
        self.logger.info("[spectrometer] %s", command)
        return ""


class MockServoBackedDevice(MockConnectionDevice):
    def __init__(self, name: str):
        super().__init__(name)
        self.angle = 0

    def set_angle(self, angle: int):
        self.angle = angle
        self.logger.info("Mock %s angle set to %s", self.name, angle)


class MockToolhead:
    def __init__(self, control_board: MockControlBoard):
        self.control_board = control_board
        self.logger = _logger()

    def home(self):
        self.control_board.positions.update({"X": 0.0, "Y": 0.0, "Z": 0.0})
        self.logger.info("Mock toolhead homed")

    def get_position(self, axis: str):
        return self.control_board.positions.get(axis, 0.0)

    def move_to(self, x: float, y: float, z: float, relative: int = 0):
        if relative:
            self.control_board.positions["X"] += x
            self.control_board.positions["Y"] += y
            self.control_board.positions["Z"] += z
        else:
            self.control_board.positions.update({"X": x, "Y": y, "Z": z})
        self.logger.info(
            "Mock toolhead moved to X=%s Y=%s Z=%s (relative=%s)",
            self.control_board.positions["X"],
            self.control_board.positions["Y"],
            self.control_board.positions["Z"],
            relative,
        )


class MockDispatcher:
    def __init__(self, use_local_camera: bool = True, camera_index: int = 0):
        self.logger = _logger()
        self.camera_width = 600
        self.camera_height = 400
        self.camera_index = int(camera_index)
        self.use_local_camera = use_local_camera

        self.control_board = MockControlBoard()
        self.spin_coater = MockSpinCoater()
        self.hotplate = MockHotplate()
        self.camera = Camera() if use_local_camera else MockCamera(self.camera_width, self.camera_height)
        self.spectrometer = MockSpectrometer()
        self.toolhead = MockToolhead(self.control_board)
        self.infeed = MockServoBackedDevice("infeed")
        self.gripper = MockServoBackedDevice("gripper")
        self.pipette_handler = MockConnectionDevice("pipette handler")
        self.vial_carousel = MockConnectionDevice("vial carousel")
        self.tip_matrix = MockConnectionDevice("tip matrix")

        self._aruco_detector = MockArucoDetector()
        self._camera_connection_callbacks: list[Callable[[bool], None]] = []
        self._emergency_stop_callbacks: list[Callable[[], None]] = []

    @property
    def aruco_detector(self):
        return self._aruco_detector

    def register_camera_connection_callback(self, callback):
        self._camera_connection_callbacks.append(callback)

    def unregister_camera_connection_callback(self, callback):
        if callback in self._camera_connection_callbacks:
            self._camera_connection_callbacks.remove(callback)

    def _notify_camera_connection_changed(self, is_connected: bool):
        for callback in list(self._camera_connection_callbacks):
            try:
                callback(is_connected)
            except Exception:
                self.logger.exception("Mock camera callback failed")

    def register_emergency_stop_callback(self, callback):
        self._emergency_stop_callbacks.append(callback)

    def unregister_emergency_stop_callback(self, callback):
        if callback in self._emergency_stop_callbacks:
            self._emergency_stop_callbacks.remove(callback)

    def notify_emergency_stop(self):
        for callback in list(self._emergency_stop_callbacks):
            try:
                callback()
            except Exception:
                self.logger.exception("Mock emergency-stop callback failed")

    def connect_camera(self):
        self.camera.connect(
            device_index=self.camera_index,
            width=self.camera_width,
            height=self.camera_height,
        )
        is_connected = self.camera.is_connected()
        if is_connected:
            self.logger.info("Local camera connected on device index %s", self.camera_index)
        elif self.use_local_camera:
            self.logger.warning("Local camera connection failed on device index %s", self.camera_index)
        self._notify_camera_connection_changed(is_connected)
        return is_connected


class MockProcedureHandler:
    def __init__(self, move_registry):
        self.logger = _logger()
        self.move_registry = move_registry
        self.procedure = None
        self.current_step = 0
        self.error_flag = False
        self.error_step_index = None
        self.min_step_duration = 0.5

        self.started = threading.Event()
        self.paused = threading.Event()
        self._stop_requested = threading.Event()
        self._started_at = None
        self._elapsed_before_run = 0.0
        threading.Thread(target=self._run, name="MockProcedureHandler", daemon=True).start()

    def set_procedure(self, procedure: list):
        if self.started.is_set():
            self.logger.error("Cannot replace the mock procedure while it is running")
            return
        self.procedure = procedure
        self.current_step = 0
        self.error_flag = False
        self.error_step_index = None
        self._elapsed_before_run = 0.0

    def begin(self):
        if not self.procedure:
            self.logger.warning("No procedure loaded in mock mode")
            return
        self.move_registry.reset_kill()
        self.current_step = 0
        self.error_flag = False
        self.error_step_index = None
        self._stop_requested.clear()
        self.paused.clear()
        self.started.set()
        self._started_at = time.monotonic()
        self._elapsed_before_run = 0.0
        self.logger.info("Mock procedure started with %s steps", len(self.procedure))

    def pause(self):
        if not self.started.is_set() or self.paused.is_set():
            return
        self._elapsed_before_run += max(0.0, time.monotonic() - self._started_at)
        self.paused.set()
        self.logger.info("Mock procedure paused")

    def resume(self):
        if not self.started.is_set() or not self.paused.is_set():
            return
        self._started_at = time.monotonic()
        self.paused.clear()
        self.logger.info("Mock procedure resumed")

    def stop(self):
        if self.started.is_set() and not self.paused.is_set() and self._started_at is not None:
            self._elapsed_before_run += max(0.0, time.monotonic() - self._started_at)
        self._started_at = None
        self._stop_requested.set()
        self.started.clear()
        self.paused.clear()

    def kill(self):
        self.move_registry.kill()
        self.stop()
        self.logger.warning("Mock procedure killed")

    def _run(self):
        while True:
            self.started.wait()
            while self.started.is_set() and self.procedure and self.current_step < len(self.procedure):
                if self._stop_requested.is_set():
                    break
                if self.paused.is_set():
                    time.sleep(0.05)
                    continue
                time.sleep(max(self.min_step_duration, 0.05))
                if not self.started.is_set() or self.paused.is_set() or self._stop_requested.is_set():
                    continue
                self.current_step += 1

            if self.procedure and self.current_step >= len(self.procedure):
                self.logger.info("Mock procedure completed")
            self.stop()

    def get_progress(self) -> float:
        if not self.procedure:
            return 0.0
        return self.current_step / len(self.procedure)

    def get_time_elapsed(self) -> timedelta:
        elapsed = self._elapsed_before_run
        if self.started.is_set() and not self.paused.is_set() and self._started_at is not None:
            elapsed += max(0.0, time.monotonic() - self._started_at)
        return timedelta(seconds=int(elapsed))

    def get_current_step_index(self):
        return self.current_step

    def has_error(self):
        return self.error_flag

    def get_error_step_index(self):
        return self.error_step_index

    def set_min_step_duration(self, duration_seconds: float):
        self.min_step_duration = max(0.0, float(duration_seconds))


class MockMoveRegistry:
    def __init__(self, dispatcher: MockDispatcher):
        self.logger = _logger()
        self.dispatcher = dispatcher
        self.control_board = dispatcher.control_board
        self.toolhead = dispatcher.toolhead
        self.infeed = dispatcher.infeed
        self.pipette_handler = dispatcher.pipette_handler
        self.spin_coater = dispatcher.spin_coater
        self.camera = dispatcher.camera
        self.gripper = dispatcher.gripper
        self.hotplate = dispatcher.hotplate
        self.vial_carousel = dispatcher.vial_carousel
        self.spectrometer = dispatcher.spectrometer
        self.tip_matrix = dispatcher.tip_matrix
        self.spectrometer_frame = None
        self.locations = _load_locations()
        self.vial = 0

        self.move_dict = {
            "example_move": self.example_move,
            "log": self.log,
            "wait": self.wait,
            "home": self.home,
            "aruco_home": self.aruco_home,
            "move_toolhead": self.move_toolhead,
            "soft_limit_axis_move": self.soft_limit_axis_move,
            "move_to_location": self.move_to_location,
            "set_temperature": self.set_temperature,
            "wait_for_temperature": self.wait_for_temperature,
            "align_gripper": self.align_gripper,
            "set_finger_angle": self.set_finger_angle,
            "set_gripper_angle": self.set_gripper_angle,
            "open_gripper": self.open_gripper,
            "close_gripper": self.close_gripper,
            "add_spin_coater_step": self.add_spin_coater_step,
            "run_spin_coater": self.run_spin_coater,
            "set_infeed_angle": self.set_infeed_angle,
            "open_infeed": self.open_infeed,
            "close_infeed": self.close_infeed,
            "set_actuator": self.set_actuator,
            "set_pipette": self.set_pipette,
            "put_away_pipette": self.put_away_pipette,
            "set_eject_angle": self.set_eject_angle,
            "set_vial": self.set_vial,
            "extract_from_vial": self.extract_from_vial,
            "dispense": self.dispense,
            "mix_fluid": self.mix_fluid,
            "eject_tip": self.eject_tip,
            "set_grab_angle": self.set_grab_angle,
            "measure_spectrum": self.measure_spectrum,
            "automated_measurement": self.automated_measurement,
            "put_0": self.put_0,
            "put_1": self.put_1,
            "set_0": self.set_0,
            "set_1": self.set_1,
        }

    def validate_moves(self, moves: list) -> bool:
        return isinstance(moves, list) and len(moves) > 0

    def reset_kill(self):
        self.control_board.reset_kill()

    def home(self):
        self.toolhead.home()

    def kill(self):
        self.dispatcher.notify_emergency_stop()
        self.control_board.kill()
        self.spin_coater.stop()

    def log(self, message: str):
        self.logger.info("Mock move log: %s", message)

    def wait(self, wait_time_seconds: int):
        time.sleep(min(float(wait_time_seconds), 0.1))

    def example_move(self, value_1: int, value_2: float, value_3: str):
        self.logger.info("Mock example move: %s %s %s", value_1, value_2, value_3)

    def set_temperature(self, temperature_c: int):
        self.hotplate.set_temperature(temperature_c)

    def wait_for_temperature(self, target_temperature: int, threshold: int):
        self.hotplate.set_temperature(target_temperature)

    def move_toolhead(self, x: float, y: float, z: float, relative: int):
        self.toolhead.move_to(x, y, z, relative)

    def soft_limit_axis_move(self, x: float, y: float, z: float, relative: int):
        self.toolhead.move_to(x, y, z, relative)

    def aruco_home(self):
        self.home()

    def move_to_location(self, destination: str):
        for location in self.locations:
            if location and location[0] == destination and len(location) >= 4:
                self.toolhead.move_to(float(location[1]), float(location[2]), float(location[3]), 0)
                return
        self.logger.warning("Mock location '%s' not found", destination)

    def add_spin_coater_step(self, rpm: int, spin_time_seconds: int):
        self.spin_coater.add_step(rpm, spin_time_seconds)

    def run_spin_coater(self):
        self.spin_coater.run(wait_to_finish=False)

    def open_gripper(self):
        self.gripper.set_angle(0)

    def close_gripper(self):
        self.gripper.set_angle(90)

    def set_gripper_angle(self, angle: int):
        self.gripper.set_angle(angle)

    def set_finger_angle(self, angle: int):
        self.gripper.set_angle(angle)

    def align_gripper(self):
        self.logger.info("Mock gripper alignment complete")

    def set_actuator(self, position: float):
        self.logger.info("Mock actuator set to %s", position)

    def extract_from_vial(self, vial_num: int, volume_ul: int):
        self.logger.info("Mock extract %s uL from vial %s", volume_ul, vial_num)

    def mix_fluid(self, source_vial_1: int, amount_1: int, source_vial_2: int, amount_2: int, destination_vial: int):
        self.logger.info(
            "Mock mix %s/%s into %s using %s and %s uL",
            source_vial_1,
            source_vial_2,
            destination_vial,
            amount_1,
            amount_2,
        )

    def dispense(self, duration_s: int):
        self.logger.info("Mock dispense for %s s", duration_s)

    def set_grab_angle(self, angle: int):
        self.gripper.set_angle(angle)

    def put_away_pipette(self):
        self.logger.info("Mock pipette parked")

    def set_0(self):
        self.logger.info("Mock set_0")

    def set_1(self):
        self.logger.info("Mock set_1")

    def put_0(self):
        self.logger.info("Mock put_0")

    def put_1(self):
        self.logger.info("Mock put_1")

    def set_pipette(self, target_pipette: int):
        self.logger.info("Mock pipette set to %s", target_pipette)

    def eject_tip(self):
        self.logger.info("Mock tip ejected")

    def set_eject_angle(self, angle: int):
        self.logger.info("Mock eject angle set to %s", angle)

    def measure_spectrum(self, measurement_type: str):
        self.spectrometer.measurements[measurement_type] = []
        self.logger.info("Mock spectrum captured for %s", measurement_type)

    def automated_measurement(self):
        self.logger.info("Mock automated measurement complete")

    def set_vial(self, vial_num: int):
        self.vial = vial_num
        self.logger.info("Mock vial set to %s", vial_num)

    def set_infeed_angle(self, angle: int):
        self.infeed.set_angle(angle)

    def open_infeed(self):
        self.infeed.set_angle(0)

    def close_infeed(self):
        self.infeed.set_angle(90)


def create_mock_runtime(camera_index: int = 0, use_local_camera: bool = True):
    dispatcher = MockDispatcher(use_local_camera=use_local_camera, camera_index=camera_index)
    move_registry = MockMoveRegistry(dispatcher)
    procedure_handler = MockProcedureHandler(move_registry)
    return dispatcher, move_registry, procedure_handler