from types import SimpleNamespace
import threading
import time

import sys
import types

# Provide a lightweight fake for drivers.procedure_file_driver to avoid yaml dependency
fake_proc = types.ModuleType("drivers.procedure_file_driver")
class FakeProcedureFile:
    def Open(self, path):
        return []
    def Save(self, path, procedure):
        return True
fake_proc.ProcedureFile = FakeProcedureFile
sys.modules['drivers.procedure_file_driver'] = fake_proc

# Provide lightweight fake 'serial' and 'serial.threaded' to avoid pyserial dependency
fake_serial = types.ModuleType('serial')
fake_threaded = types.ModuleType('serial.threaded')

class FakeLineReader:
    def __init__(self):
        pass

fake_threaded.LineReader = FakeLineReader

class FakeReaderThread:
    def __init__(self, serial_instance=None, protocol_factory=None):
        self.serial_instance = serial_instance
        self.protocol_factory = protocol_factory
        self.daemon = False
        self._started = False
    def start(self):
        self._started = True
    def write(self, data):
        # pretend to write to serial
        return len(data)

fake_threaded.ReaderThread = FakeReaderThread

fake_serial.threaded = fake_threaded
def fake_serial_Serial(*args, **kwargs):
    class _S:
        is_open = False
        def close(self):
            pass
    return _S()
fake_serial.Serial = fake_serial_Serial
sys.modules['serial'] = fake_serial
sys.modules['serial.threaded'] = fake_threaded

# This creates a fake gpiozero instance with a class for the servos that would make the system crash otherwise
fake_gpiozero = types.ModuleType('gpiozero')
class AngularServo:
    def __init__(self, *args, **kwargs):
        self.angle = None
    def detach(self):
        pass
fake_gpiozero.AngularServo = AngularServo
sys.modules['gpiozero'] = fake_gpiozero

# Provide a minimal recreation of cv2 so it doesnt need to be installed for tests
fake_cv2 = types.ModuleType('cv2')
fake_aruco = types.ModuleType('cv2.aruco')
def getPredefinedDictionary(x):
    return None
class DetectorParameters:
    def __init__(self):
        pass
class ArucoDetector:
    def __init__(self, dictionary, parameters):
        pass
fake_aruco.getPredefinedDictionary = getPredefinedDictionary
fake_aruco.DetectorParameters = DetectorParameters
fake_aruco.ArucoDetector = ArucoDetector
fake_cv2.aruco = fake_aruco
sys.modules['cv2'] = fake_cv2
sys.modules['cv2.aruco'] = fake_aruco

from services.move_registry import MoveRegistry

# This tests things that are present in the normal system while not connected to them via hardware.
class FakeControlBoard:
    def __init__(self):
        self.received_ok = threading.Event()
        self._kill_sent = False
    def kill(self):
        print("FakeControlBoard.kill called")
        self._kill_sent = True
    def reset_kill(self):
        print("FakeControlBoard.reset_kill called")
        self._kill_sent = False

class FakeSpinCoater:
    def __init__(self):
        self.done = threading.Event()
    def stop(self):
        print("FakeSpinCoater.stop called")
    def clear_steps(self):
        print("FakeSpinCoater.clear_steps called")

class FakeGripper:
    def set_finger_angle(self,a):
        print("FakeGripper.set_finger_angle",a)
    def set_arm_angle(self,a):
        print("FakeGripper.set_arm_angle",a)

class FakePipetteHandler:
    def kill(self):
        print("FakePipetteHandler.kill called")

fake_dispatcher = SimpleNamespace(
    toolhead=None,
    control_board=FakeControlBoard(),
    infeed=None,
    pipette_handler=FakePipetteHandler(),
    spin_coater=FakeSpinCoater(),
    camera=None,
    gripper=FakeGripper(),
    hotplate=None,
    vial_carousel=None,
    spectrometer=None,
    tip_matrix=None
)

mr = MoveRegistry(fake_dispatcher)
print("Calling kill()")
mr.kill()
print("Calling reset_kill()")
mr.reset_kill()
print("Done")
