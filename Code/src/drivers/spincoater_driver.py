import logging
from time import sleep
import serial
import serial.threaded
import threading
# SPINCOATER COMMANDS
# spc set pcmode
# spc add step {rpm} {time}
# spc get steps
# spc del steps
# spc run
# spc stop

class SpinCoater():
    """ Class to control the spin coater """
    def __init__(self):
        self.logger = logging.getLogger("Main Logger")
        self.serial = None
        self.reader_thread = None
        
        self.done = threading.Event()
        # Track last requested rpm and running state for UI/status reporting
        self.last_rpm = None
        self.is_running = False
        
    def connect(self):
        if self.is_connected():
            self.logger.error("Spin Coater is already connected")
            return
        port = "/dev/spin_coater"
        try:
            # Use a finite timeout to avoid blocking reads that could hang the app
            self.serial = serial.Serial(port, 9600, timeout=1.0)
            self._begin_reader_thread()
            sleep(0.5)
            self.set_pc_mode()
            sleep(0.5)
            self.clear_steps()
            self.logger.info(
                f"Connected to spincoater on port {port}")
        except serial.SerialException as e:
            self.logger.error(f"Error connecting to spincoater: {e}")
               
    def disconnect(self):
        if not self.is_connected():
            return
        self.serial.close()
        self.logger.debug("Spin Coater Disconnected")
        # ensure running state cleared
        try:
            self.is_running = False
        except Exception:
            pass
        
    def is_connected(self) -> bool:
        return (self.serial is not None) and (self.serial.is_open)

    def _begin_reader_thread(self):
        self.reader_thread = serial.threaded.ReaderThread(
            serial_instance=self.serial,
            protocol_factory=lambda: SpinCoaterLineReader(
                self.logger, self)
        )
        self.reader_thread.daemon = True
        self.reader_thread.start()
        
    def send_message(self, message: str):
        if self.serial is None:
            self.logger.error("Serial is not connected")
            return

        try:
            self.reader_thread.write(message.encode("ascii"))
            self.logger.debug(f"Sending command: {message}")
        except Exception as e:
            self.logger.exception(f"Failed to send spincoater command '{message}': {e}")
            return
        sleep(0.2)
        
        
    def stop(self):
        # Mark as not running and request stop
        try:
            self.is_running = False
        except Exception:
            pass
        self.send_message("spc stop")
        
    def run(self, wait_to_finish: bool = False, timeout: float = 120.0):
        """Start the spincoater run and optionally wait for completion.

        Args:
            wait_to_finish (bool): If True, block until the spincoater signals completion.
            timeout (float): Maximum seconds to wait before raising TimeoutError.
        """
        # mark running and start
        try:
            self.is_running = True
        except Exception:
            pass
        self.send_message("spc run")
        self.done.clear()
        if wait_to_finish:
            finished = self.done.wait(timeout=timeout)
            if not finished:
                self.logger.error("SpinCoater run timed out")
                raise TimeoutError("SpinCoater run timed out")
            # if we waited and finished (or timed out) clear running flag
            try:
                self.is_running = False
            except Exception:
                pass
        # clear configured steps once run completes (or was started)
        self.clear_steps()
        
    def add_step(self, rpm: int, time_seconds:float):
        # remember last rpm for UI/status
        try:
            self.last_rpm = int(rpm)
        except Exception:
            self.last_rpm = rpm
        self.send_message(f"spc add step {rpm} {time_seconds}")
    
    def clear_steps(self):
        self.send_message("spc del steps")
        
    def set_pc_mode(self):
        self.send_message("spc set pcmode")
        
    


class SpinCoaterLineReader(serial.threaded.LineReader):
    """Class to read lines from the spin coater on a separate thread"""
    
    TERMINATOR = b"\n"
    def __init__(self, logger: logging.Logger, spin_coater: SpinCoater):
        super().__init__()
        self.logger = logger
        self.spin_coater = spin_coater

    def handle_line(self, line: str):
        line = line.strip()
        self.logger.debug(f"Received: {line}")
        
        if line == "Done":
            # notify waiters and mark not running
            self.spin_coater.done.set()
            try:
                self.spin_coater.is_running = False
            except Exception:
                pass
            
    
    def connection_lost(self, exc):
        """Handle the loss of connection."""
        if exc:
            self.logger.error(f"Serial connection lost: {exc}")
        else:
            self.logger.info("Serial connection closed")
        # ensure spincoater state cleaned up
        try:
            self.spin_coater.is_running = False
        except Exception:
            pass
        self.spin_coater.disconnect()