import os
import sys
pp=os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(pp)

from drivers.controlboard_driver import ControlBoard

class Toolhead():
    def __init__(self, control_board: ControlBoard):
        self.control_board = control_board
        
    def move_axis(self, axis: str, distance_mm: float, feedrate_mm_per_minute: int = 1000, relative: bool = False, finish_move: bool = True):
        """Move a single axis through the control board.

        Accepts an optional `feedrate_mm_per_minute` (defaults to 1000) and
        passes through to the lower-level `ControlBoard.move_axis`.
        """
        self.control_board.move_axis(axis, distance_mm, feedrate_mm_per_minute, relative=relative, finish_move=finish_move)
        
    def get_position(self, axis):
        # Use control board's thread-safe getter
        try:
            return self.control_board.get_position(axis)
        except Exception:
            return None
    
    def home(self):
        # Home each axis separately and wait for completion to avoid
        # firmware-specific combined G28 failures on some boards. If X does
        # not appear to change after a per-axis homing attempt, try a
        # combined homing fallback for robustness.
        logger = self.control_board.logger

        def _pos_close(a, b, tol=0.5):
            try:
                return a is not None and b is not None and abs(float(a) - float(b)) <= tol
            except Exception:
                return False

        start_x = self.get_position("X")
        try:
            self.control_board.send_message("G28 Z", require_lock=True)
            self.control_board.finish_moves()
            logger.info(f"Homed Z; position Z={self.get_position('Z')}")
        except Exception:
            self.control_board.logger.exception("Homing Z failed")
        try:
            self.control_board.send_message("G28 Y", require_lock=True)
            self.control_board.finish_moves()
            logger.info(f"Homed Y; position Y={self.get_position('Y')}")
        except Exception:
            self.control_board.logger.exception("Homing Y failed")

        try:
            self.control_board.send_message("G28 X", require_lock=True)
            self.control_board.finish_moves()
            logger.info(f"Homed X attempt; position X={self.get_position('X')}")
            new_x = self.get_position("X")
            # If X didn't change, try a conservative combined homing fallback
            if not _pos_close(start_x, new_x):
                logger.info("X homing changed position; good.")
            else:
                logger.warning("X homing did not change position; attempting combined homing fallback")
                try:
                    # Try homing all axes together as a fallback
                    self.control_board.send_message("G28 X Y Z", require_lock=True)
                    self.control_board.finish_moves()
                    logger.info(f"Combined homing complete; position X={self.get_position('X')}")
                except Exception:
                    self.control_board.logger.exception("Fallback combined homing failed for X")
        except Exception:
            self.control_board.logger.exception("Homing X failed")

    def move_to(self, x: float = None, y: float = None, z: float = None, relative: bool = False, feedrate: int = 1000, coordinated: bool = True):
        """Move multiple axes.

        By default this attempts a coordinated multi-axis `G0` (if
        `coordinated=True`). If the firmware does not reach the requested
        coordinates the method falls back to per-axis moves (Z->X->Y) to
        ensure reliability.
        """
        logger = self.control_board.logger
        logger.info(f"move_to called: x={x}, y={y}, z={z}, relative={relative}, feedrate={feedrate}, coordinated={coordinated}")

        # Check if we have any coordinates to move
        has_move = x is not None or y is not None or z is not None
        if not has_move:
            logger.debug("move_to: no coordinates specified")
            return

        def _position_close(a, b, tol=0.5):
            try:
                return abs(float(a) - float(b)) <= tol
            except Exception:
                return False

        # First attempt coordinated move if requested
        if coordinated:
            try:
                # Ensure mode and send combined move
                if relative:
                    self.control_board.send_message("G91", require_lock=True)
                else:
                    self.control_board.send_message("G90", require_lock=True)

                parts = []
                if x is not None:
                    parts.append(f"X{x}")
                if y is not None:
                    parts.append(f"Y{y}")
                if z is not None:
                    parts.append(f"Z{z}")

                cmd = "G0 " + " ".join(parts) + f" F{feedrate}"
                self.control_board.send_message(cmd, require_lock=True)
                self.control_board.finish_moves()

                # Verify positions; if any axis didn't reach target, fall back
                need_fallback = False
                if z is not None and not _position_close(self.get_position("Z"), z):
                    logger.warning(f"Coordinated move: Z did not reach {z}, actual={self.get_position('Z')} -> falling back")
                    need_fallback = True
                if x is not None and not _position_close(self.get_position("X"), x):
                    logger.warning(f"Coordinated move: X did not reach {x}, actual={self.get_position('X')} -> falling back")
                    need_fallback = True
                if y is not None and not _position_close(self.get_position("Y"), y):
                    logger.warning(f"Coordinated move: Y did not reach {y}, actual={self.get_position('Y')} -> falling back")
                    need_fallback = True

                if need_fallback:
                    logger.info("Falling back to per-axis moves")
                    raise RuntimeError("Coordinated move incomplete; fallback requested")

                # Coordinated move succeeded
                logger.info(f"Coordinated move complete; final positions: X={self.get_position('X')}, Y={self.get_position('Y')}, Z={self.get_position('Z')}")
                # Revert to absolute if needed
                if relative:
                    self.control_board.send_message("G90", require_lock=True)
                return
            except Exception as e:
                logger.debug(f"Coordinated move failed or incomplete: {e}")

        # Fallback or non-coordinated: move axes individually (Z->X->Y)
        if z is not None:
            logger.info(f"Moving Z to {z} (absolute={not relative})")
            self.move_axis("Z", z, feedrate_mm_per_minute=feedrate, relative=relative, finish_move=True)
            logger.info(f"Z move complete; reported position: {self.get_position('Z')}")

        if x is not None:
            logger.info(f"Moving X to {x} (absolute={not relative})")
            self.move_axis("X", x, feedrate_mm_per_minute=feedrate, relative=relative, finish_move=True)
            logger.info(f"X move complete; reported position: {self.get_position('X')}")

        if y is not None:
            logger.info(f"Moving Y to {y} (absolute={not relative})")
            self.move_axis("Y", y, feedrate_mm_per_minute=feedrate, relative=relative, finish_move=True)
            logger.info(f"Y move complete; reported position: {self.get_position('Y')}")

        logger.info(f"move_to complete; final position: X={self.get_position('X')}, Y={self.get_position('Y')}, Z={self.get_position('Z')}")

