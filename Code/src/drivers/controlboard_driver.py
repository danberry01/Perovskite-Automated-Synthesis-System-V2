from queue import Queue
import logging
import threading
import time
from time import sleep
import serial
import serial.threaded


# DEFAULT_SPEED = 1000


class ControlBoard():
    """Class to control the Octopus v1.1 control board"""

    def __init__(self):

        self.logger = logging.getLogger("Main Logger")

        self.positions = {"X": 0,
                          "Y": 0,
                          "Z": 0,
                          "A": 0,
                          "B": 0}
        self.serial = None
        self.reader_thread = None

        self.received_ok = threading.Event()
        
        self.relative_positioning_enabled = False
        # Internal event used to signal an emergency stop / kill
        self._kill_event = threading.Event()
        # Lock to protect concurrent access to positions
        self._positions_lock = threading.Lock()

    def connect(self):
        """Connect to the control board and start the reader thread."""
        if self.is_connected():
            self.logger.error("Control board is already connected")
        port = "/dev/control_board"
        try:
            self.serial = serial.Serial(port, 115200, timeout=None)
            self._begin_reader_thread()
            self.send_message("M501")
            self.logger.info(f"Connected to control board on port {port}")
        except serial.SerialException as e:
            self.logger.error(f"Error connecting to control board: {e}")
    
    def disconnect(self):
        if not self.is_connected():
            return
        self.serial.close()
        self.logger.debug("Control Board Disconnected")
            
    def is_connected(self) -> bool:
        return self.serial is not None and self.serial.is_open
    
    def kill(self):
        """Send emergency stop to the control board and unblock waits.

        This sets an internal kill event, sends the firmware emergency stop
        (`M112`) and ensures any threads waiting for move completion are
        unblocked.
        """
        self.logger.error("Emergency stop requested on control board")
        # Mark kill so other methods can abort early
        try:
            self._kill_event.set()
        except Exception:
            pass

        # Try to send the emergency stop command
        try:
            if self.is_connected():
                self.send_message("M112")
        except Exception as e:
            self.logger.exception(f"Failed to send emergency stop: {e}")

        # Wake any threads waiting on OK so they can exit quickly
        try:
            self.received_ok.set()
        except Exception:
            pass

    def request_position(self):
        """Request the control board to report its current position (M114).

        The board's reader thread will pick up the response and update
        `self.positions`.
        """
        try:
            if self.is_connected():
                # best-effort; do not block here
                self.send_message("M114")
        except Exception:
            self.logger.exception("Failed to request position from control board")

    def get_position(self, axis: str):
        """Thread-safe getter for axis position."""
        with self._positions_lock:
            return self.positions.get(axis)

    def _update_positions_from_line(self, line: str):
        """Parse a status line containing X:,Y:,Z: etc and update positions."""
        try:
            # Expect lines like: 'X:0.00 Y:0.00 Z:0.00 A:0.00 B:0.00'
            for substr, key in zip(ControlBoardLineReader.POSITION_PREFIXS, self.positions):
                if substr in line:
                    try:
                        number = (line.split(substr)[1]).split(" ")[0]
                        val = float(number)
                        with self._positions_lock:
                            self.positions[key] = val
                    except Exception:
                        # ignore parse errors for individual values
                        pass
        except Exception:
            self.logger.exception("Failed to parse position line")

    def reset_kill(self):
        """Clear the internal kill state so operations can resume.

        Sends a firmware reset (`M999`) followed by a settings reload (`M501`) if
        the board is connected. Clears internal events so waiting loops can run
        again.
        """
        try:
            self._kill_event.clear()
            # Clear any previous ok marker
            try:
                self.received_ok.clear()
            except Exception:
                pass
            self.logger.debug("Control board kill state cleared")

            # If connected, attempt to restart firmware and reload settings
            if self.is_connected():
                try:
                    # Request firmware restart to clear M112 state
                    self.logger.info("Sending firmware reset (M999) to control board")
                    self.send_message("M999")
                    sleep(0.5)
                    # Reload stored settings
                    self.send_message("M501")
                    sleep(0.2)
                except Exception as e:
                    self.logger.exception(f"Failed to send firmware reset commands: {e}")
        except Exception:
            self.logger.exception("Failed to clear control board kill state")
        
    def _begin_reader_thread(self):
        self.reader_thread = serial.threaded.ReaderThread(
            serial_instance=self.serial,
            protocol_factory=lambda: ControlBoardLineReader(
                self.logger, self)
        )
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def send_message(self, message: str):
        """Send a message to the control board.

        ### Args:
            message (str): The message to send.
        """
        if not self.is_connected():
            self.logger.error("Serial is not connected")
            return

        if self.reader_thread is None:
            self.logger.error("Reader thread is not running")
            return

        if '\r\n' not in message:
            message += "\r\n"
        try:
            # If a kill was requested, still attempt to send the emergency stop command,
            # otherwise write normally and log any serial errors.
            self.reader_thread.write(message.encode("utf-8"))
            self.logger.debug(f"Sending message: {message}")
        except Exception as e:
            self.logger.exception(f"Failed to send message '{message}': {e}")
        
    def move_axis(self, axis: str, distance_mm: float, feedrate_mm_per_minute: int = 2000, relative: bool = False, finish_move: bool = True):
        """ Takes in a list of axes, distances and speeds to move the gantry"""
        if axis not in self.positions.keys():
            raise f"Invalid axis {axis}"
  
        if relative and distance_mm == 0:
            return

        # Abort early if an emergency kill has been requested
        if getattr(self, '_kill_event', None) is not None and self._kill_event.is_set():
            self.logger.warning("Move aborted: control board in kill state")
            raise RuntimeError("ControlBoard is in kill state")
        
        if relative:
            self.send_message("G91")
        sleep(0.1)
        # dont go crazy with these axes,
        if (axis == "Z" or axis == "A" or axis == "B") and feedrate_mm_per_minute == 2000:
            feedrate_mm_per_minute = 600
            
        self.send_message(f"G0 {axis}{distance_mm} F{feedrate_mm_per_minute}")
        sleep(0.1)
            
        
        if finish_move:
            self.finish_moves()
            sleep(0.1)
        if relative:
            self.send_message("G90")
            sleep(0.1)

    def finish_moves(self):
        """Wait for the move to finish"""
        if not self.is_connected():
            self.logger.error("Serial is not connected")
            return
        # Clear any previous OK marker and request move completion
        self.received_ok.clear()
        sleep(0.1)
        try:
            self.send_message("M400")
        except Exception:
            # send_message already logs failures
            pass

        self.logger.debug("Waiting for move to finish (interruptible)")

        # Wait in small increments so we can be interrupted by a kill event
        timeout = 120.0
        poll_interval = 0.1
        request_interval = 0.5
        waited = 0.0
        last_request = time.time()
        while waited < timeout:
            # If a kill has been requested, break out early
            if getattr(self, '_kill_event', None) is not None and self._kill_event.is_set():
                self.logger.info("Finish moves interrupted by kill")
                break

            # Periodically request position updates so UI can show current coords
            now = time.time()
            if now - last_request >= request_interval:
                try:
                    self.request_position()
                except Exception:
                    pass
                last_request = now

            if self.received_ok.wait(timeout=poll_interval):
                break
            waited += poll_interval
        




class ControlBoardLineReader(serial.threaded.LineReader):
    """Class to read lines from the control board on a separate thread."""
    TERMINATOR = b"\n"
    POSITION_PREFIXS = ["X:", "Y:", "Z:", "A:", "B:"]
    
    def __init__(self, logger: logging.Logger, control_board: ControlBoard):
        """Initialize with optional logger."""
        super().__init__()
        self.logger = logger
        self.control_board = control_board
        self.logger.debug("Line Reader Started")

    def handle_line(self, line):
        """Process each received line."""
        line = line.strip()
        #self.logger.debug(f"Received: {line}")

        # check if we receive position data (e.g., 'X:.. Y:.. Z:..')
        received_position_data = True
        for prefix in self.POSITION_PREFIXS:
            if prefix not in line:
                received_position_data = False
                self.logger.debug(f"Received: {line}")
                break

        if line == "ok":
            self.control_board.received_ok.set()  # Set the event when "ok" is received
        elif received_position_data:
            # Delegate parsing to the control board to update positions thread-safely
            try:
                self.control_board._update_positions_from_line(line)
            except Exception:
                self.logger.exception("Failed to update positions from line")
            
    def connection_lost(self, exc):
        """Handle the loss of connection."""
        if exc:
            self.logger.error(f"Serial connection lost: {exc}")
        else:
            self.logger.info("Serial connection closed")
        self.control_board.disconnect()


