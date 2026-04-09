import logging
from tkinter import PhotoImage
import customtkinter as ctk
from gpiozero import AngularServo, Device
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

# -- DRIVER IMPORT --
from drivers.controlboard_driver import ControlBoard
from drivers.spincoater_driver import SpinCoater
from drivers.camera_driver import Camera
from drivers.procedure_file_driver import ProcedureFile
from drivers.spectrometer_driver import Spectrometer
# from drivers import ml_driver

# -- OBJECT IMPORT --
from objects.tip_matrix import TipMatrix
from objects.vial_carousel import VialCarousel
from objects.infeed import Infeed
from objects.hotplate import Hotplate
from objects.gripper import Gripper
from objects.pippete import Pipette, PipetteHandler
from objects.toolhead import Toolhead

from core.dispatcher import Dispatcher

from services.procedure_handler import ProcedureHandler
from services.move_registry import MoveRegistry
from gui import App

if __name__ == "__main__":
    # enable software pwm
    Device.pin_factory = PiGPIOFactory()
    
    # -- LOGGING --
    # Add custom CAMERA logging level for camera/marker updates
    CAMERA_LEVEL = logging.DEBUG - 1
    logging.addLevelName(CAMERA_LEVEL, "CAMERA")
    
    logger = logging.getLogger("Main Logger")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s\t%(asctime)s: %(message)s'))
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)
 
    dispatcher = Dispatcher()

    move_registry = MoveRegistry(dispatcher)
    
    procedure_handler = ProcedureHandler(move_registry = move_registry)
    
    # -- GUI --
    app = App(move_registry, dispatcher, procedure_handler)
    
    move_registry.spectrometer_frame = app.tab_view_frame.procedure_viewer_frame.spectrometer_frame

    # program stalls when not everything is connected and this is called
    # connect to devices
    dispatcher.spectrometer.connect()
    dispatcher.control_board.connect()
    # Use dispatcher helper so preferred resolution is applied to the Camera driver
    dispatcher.connect_camera()
    dispatcher.spin_coater.connect()
    dispatcher.hotplate.connect()
    

    app.mainloop()
    
    # -- CLEANUP --
    dispatcher.hotplate.set_temperature(0)
    sleep(1)
    
    dispatcher.control_board.disconnect()
    dispatcher.spectrometer.disconnect()
    dispatcher.spin_coater.disconnect()
    dispatcher.camera.disconnect()
    dispatcher.hotplate.disconnect()
