import os
import sys
pp=os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(pp)

from drivers.controlboard_driver import ControlBoard

class Toolhead():
    def __init__(self, control_board: ControlBoard):
        self.control_board = control_board
        
    def move_axis(self, axis: str, distance_mm: float, relative: bool = False, finish_move: bool = True):
        self.control_board.move_axis(axis, distance_mm, 1000, relative=relative, finish_move=finish_move)
        
    def get_position(self, axis):
        # Use control board's thread-safe getter
        try:
            return self.control_board.get_position(axis)
        except Exception:
            return None
    
    def home(self):
        self.control_board.send_message("G28 Z")
        self.control_board.send_message("G28 Y")
        self.control_board.send_message("G28 X")

    def move_to(self, x: float = None, y: float = None, z: float = None, relative: bool = False, feedrate: int = 1000):
        """Move multiple axes in a single coordinated command.

        Provides a single `G0` with X/Y/Z to avoid per-axis mode/coordination issues.
        """
        # Build the coordinate components
        parts = []
        if x is not None:
            parts.append(f"X{x}")
        if y is not None:
            parts.append(f"Y{y}")
        if z is not None:
            parts.append(f"Z{z}")

        if not parts:
            return

        # Ensure mode is explicit for the move
        if relative:
            self.control_board.send_message("G91")
        else:
            self.control_board.send_message("G90")

        # Send combined move
        cmd = "G0 " + " ".join(parts) + f" F{feedrate}"
        self.control_board.send_message(cmd)

        # Wait for completion using control board's finishing logic
        self.control_board.finish_moves()

        # Revert to absolute mode after a relative move for consistent behavior
        if relative:
            self.control_board.send_message("G90")

