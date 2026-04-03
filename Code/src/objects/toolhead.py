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
        # Home each axis separately and wait for completion to avoid
        # firmware-specific combined G28 failures on some boards.
        try:
            self.control_board.send_message("G28 Z", require_lock=True)
            self.control_board.finish_moves()
        except Exception:
            self.control_board.logger.exception("Homing Z failed")
        try:
            self.control_board.send_message("G28 Y", require_lock=True)
            self.control_board.finish_moves()
        except Exception:
            self.control_board.logger.exception("Homing Y failed")
        try:
            self.control_board.send_message("G28 X", require_lock=True)
            self.control_board.finish_moves()
        except Exception:
            self.control_board.logger.exception("Homing X failed")

    def move_to(self, x: float = None, y: float = None, z: float = None, relative: bool = False, feedrate: int = 1000):
        """Move multiple axes using individual per-axis commands for reliability.
        
        Many firmware implementations don't handle multi-axis G0 reliably.
        Instead, move each axis that was specified as a separate G0 command
        to ensure each one completes before the next starts.
        """
        logger = self.control_board.logger
        logger.info(f"move_to called: x={x}, y={y}, z={z}, relative={relative}, feedrate={feedrate}")
        
        # Check if we have any coordinates to move
        has_move = x is not None or y is not None or z is not None
        if not has_move:
            logger.debug("move_to: no coordinates specified")
            return
        
        # Move each axis individually for reliability. Typical order: Z for safety, then X, then Y.
        # Z first so we don't collide with obstacles when moving X/Y.
        # (move_axis will handle G90/G91 mode for each move)
        if z is not None:
            logger.info(f"Moving Z to {z} (absolute={not relative})")
            self.move_axis("Z", z, feedrate_mm_per_minute=feedrate, relative=relative, finish_move=True)
            z_actual = self.get_position("Z")
            logger.info(f"Z move complete; reported position: {z_actual}")
        
        if x is not None:
            logger.info(f"Moving X to {x} (absolute={not relative})")
            self.move_axis("X", x, feedrate_mm_per_minute=feedrate, relative=relative, finish_move=True)
            x_actual = self.get_position("X")
            logger.info(f"X move complete; reported position: {x_actual}")
        
        if y is not None:
            logger.info(f"Moving Y to {y} (absolute={not relative})")
            self.move_axis("Y", y, feedrate_mm_per_minute=feedrate, relative=relative, finish_move=True)
            y_actual = self.get_position("Y")
            logger.info(f"Y move complete; reported position: {y_actual}")
        
        # Final position check
        final_x = self.get_position("X")
        final_y = self.get_position("Y")
        final_z = self.get_position("Z")
        logger.info(f"move_to complete; final position: X={final_x}, Y={final_y}, Z={final_z}")

