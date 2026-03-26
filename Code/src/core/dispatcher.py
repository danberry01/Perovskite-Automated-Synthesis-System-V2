
from drivers.controlboard_driver import ControlBoard
from drivers.spincoater_driver import SpinCoater
from drivers.camera_driver import Camera
from drivers.procedure_file_driver import ProcedureFile
from drivers.spectrometer_driver import Spectrometer

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