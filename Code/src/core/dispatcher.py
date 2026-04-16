
from drivers.controlboard_driver import ControlBoard
from drivers.spincoater_driver import SpinCoater
from drivers.camera_driver import Camera
from drivers.procedure_file_driver import ProcedureFile
from drivers.spectrometer_driver import Spectrometer
from drivers.aruco_detector_driver import ArucoDetector

from objects.tip_matrix import TipMatrix
from objects.vial_carousel import VialCarousel
from objects.infeed import Infeed
from objects.hotplate import Hotplate
from objects.gripper import Gripper
from objects.pippete import Pipette, PipetteHandler
from objects.toolhead import Toolhead

from gpiozero import AngularServo

class Dispatcher:
    def __init__(self):
        # Instantiate all hardware here
        self.control_board = ControlBoard()
        self.spin_coater = SpinCoater()
        self.hotplate = Hotplate()
        self.camera = Camera()
        self.spectrometer = Spectrometer()
        self.toolhead = Toolhead(self.control_board)
        
        # Shared camera vision resources
        self.camera_width = 600
        self.camera_height = 400
        
        # Shared ArUco detector (created on demand to avoid re-initializing)
        self._aruco_detector = None
        
        # Camera connection callbacks - for linking buttons
        self._camera_connection_callbacks = []
        self._emergency_stop_callbacks = []
        
        # Pipette handler
        self.pipettes = [
            Pipette(200, 97, 17, 3, False),
            Pipette(1000, 97, 17, 3, True)
        ]
        self.tip_eject_servo = AngularServo(pin=27, min_angle=0, max_angle=270, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
        self.grabber_servo = AngularServo(pin=22, min_angle=0, max_angle=180, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
        self.grabber_servo.angle = 180
        self.pipette_handler = PipetteHandler(control_board=self.control_board, tip_eject_servo=self.tip_eject_servo, grabber_servo=self.grabber_servo, pipettes=self.pipettes)
        
        self.tip_matrix = TipMatrix()
        self.vial_carousel = VialCarousel(self.control_board)
        self.infeed = Infeed(AngularServo(pin=24, min_angle=0, max_angle=180, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000))
        self.gripper = Gripper(
            arm_servo=AngularServo(pin=17, min_angle=0, max_angle=180, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000),
            finger_servo=AngularServo(pin=18, min_angle=0, max_angle=180, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
        )

    @property
    def aruco_detector(self):
        """Lazy-load the ArUco detector on first access"""
        if self._aruco_detector is None:
            self._aruco_detector = ArucoDetector(
                calibration_file="gui/components/calibration_data.npz",
                marker_length=0.05,  # 50 mm
                frame_width=self.camera_width,
                frame_height=self.camera_height
            )
        return self._aruco_detector

    def register_camera_connection_callback(self, callback):
        """
        Register a callback to be notified when camera connection state changes.
        Callback should accept: callback(is_connected: bool)
        """
        self._camera_connection_callbacks.append(callback)

    def unregister_camera_connection_callback(self, callback):
        """Unregister a camera connection callback"""
        if callback in self._camera_connection_callbacks:
            self._camera_connection_callbacks.remove(callback)

    def _notify_camera_connection_changed(self, is_connected: bool):
        """Notify all registered callbacks about camera connection state change"""
        for callback in self._camera_connection_callbacks:
            try:
                callback(is_connected)
            except Exception as e:
                import logging
                logger = logging.getLogger("Main Logger")
                logger.error(f"Error in camera connection callback: {e}")

    def register_emergency_stop_callback(self, callback):
        """Register a callback to be notified when an emergency stop is triggered."""
        self._emergency_stop_callbacks.append(callback)

    def unregister_emergency_stop_callback(self, callback):
        """Unregister an emergency stop callback."""
        if callback in self._emergency_stop_callbacks:
            self._emergency_stop_callbacks.remove(callback)

    def notify_emergency_stop(self):
        """Notify all registered listeners that an emergency stop was requested."""
        for callback in list(self._emergency_stop_callbacks):
            try:
                callback()
            except Exception as e:
                import logging
                logger = logging.getLogger("Main Logger")
                logger.error(f"Error in emergency stop callback: {e}")

    def connect_camera(self):
        """
        Connect to the camera through the Camera driver.
        Notifies all registered callbacks of the connection state change.
        """
        # Pass preferred resolution to the Camera driver so only one
        # VideoCapture instance exists in the process.
        self.camera.connect(width=self.camera_width, height=self.camera_height)
        is_connected = self.camera.is_connected()
        self._notify_camera_connection_changed(is_connected)
        return is_connected

    @classmethod
    def create_default(cls):
        """Optional helper to create all hardware objects in one call"""
        return cls(
            control_board=ControlBoard(),
            spin_coater=SpinCoater(),
            hotplate=Hotplate(),
            camera=Camera(),
            spectrometer=Spectrometer(),
            pipette_handler=PipetteHandler(),
            vial_carousel=VialCarousel()
        )