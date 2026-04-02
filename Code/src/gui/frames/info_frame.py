import customtkinter as ctk
from ..components.constants import *
import logging
from time import sleep

# Place the ConsoleFrame inside the InfoFrame so the console is part of the
# bottom pane and remains visible when the procedure viewer is not active.
from .procedure_viewer.console_frame import ConsoleFrame


class InfoFrame(ctk.CTkFrame):
    """Frame to display miscellaneous information (contains console + status)."""
    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=FOREGROUND_COLOR_TWO)

        self.controller = controller
        # MoveRegistry and procedure_handler (may be None during early init)
        self.move_registry = getattr(controller, 'move_registry', None)
        self.procedure_handler = getattr(controller, 'procedure_handler', None)

        # Layout: top row = status (coords + progress + step info), bottom = console
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        # Status frame in the top-right of this InfoFrame
        self.status_frame = ctk.CTkFrame(master=self, fg_color=FOREGROUND_COLOR_TWO)
        self.status_frame.grid(row=0, column=1, sticky="ne", padx=10, pady=6)

        # Position labels (X Y Z) grouped to the right
        self.pos_label = ctk.CTkLabel(self.status_frame, text="X: --  Y: --  Z: --", anchor="e",
                                      font=("Arial", 14))
        self.pos_label.grid(row=0, column=0, sticky="ne")

        # Procedure step info
        self.step_info_label = ctk.CTkLabel(self.status_frame, text="No Procedure Loaded - Use Import to load one",
                                            anchor="e", font=("Arial", 12))
        self.step_info_label.grid(row=1, column=0, sticky="ne", pady=(4, 0))

        # Progress bar (0.0 - 1.0)
        self.progress = ctk.CTkProgressBar(master=self.status_frame, width=240)
        self.progress.set(0.0)
        self.progress.grid(row=2, column=0, sticky="ne", pady=(6, 0))

        # Console placed in the bottom area
        self.console_frame = ConsoleFrame(master=self)
        self.console_frame.grid(row=0, column=0, sticky="nsew")

        # Start periodic update loop
        try:
            self._after_id = None
            self._update_loop()
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to start InfoFrame update loop")

    def _format_pos(self, v):
        try:
            if v is None:
                return "--"
            return f"{float(v):.2f}"
        except Exception:
            return str(v)

    def _update_loop(self):
        """Periodic UI update: refresh positions, progress, and step info."""
        try:
            # Update positions from control board if available
            x = y = z = None
            try:
                if self.move_registry and hasattr(self.move_registry, 'control_board') and self.move_registry.control_board:
                    # Ask the control board to report a position (non-blocking)
                    try:
                        self.move_registry.control_board.request_position()
                    except Exception:
                        pass
                    # Read last-known positions
                    x = self.move_registry.toolhead.get_position('X')
                    y = self.move_registry.toolhead.get_position('Y')
                    z = self.move_registry.toolhead.get_position('Z')
            except Exception:
                pass

            pos_text = f"X: {self._format_pos(x)}  Y: {self._format_pos(y)}  Z: {self._format_pos(z)}"
            try:
                self.pos_label.configure(text=pos_text)
            except Exception:
                pass

            # Update procedure progress and current step info
            try:
                ph = getattr(self.controller, 'procedure_handler', None)
                if ph and ph.procedure:
                    progress = ph.get_progress()
                    self.progress.set(progress)

                    cur = ph.get_current_step_index()
                    total = len(ph.procedure)
                    if cur < total and total > 0:
                        step = ph.procedure[cur]
                        func_name = step[0]
                        args = step[1:]
                        step_text = f"Step {cur+1}/{total}: {func_name}({', '.join(map(str,args))})"
                    else:
                        step_text = "Procedure idle"
                else:
                    self.progress.set(0.0)
                    step_text = "No Procedure Loaded - Use Import to load one"

                try:
                    self.step_info_label.configure(text=step_text)
                except Exception:
                    pass
            except Exception:
                logging.getLogger("Main Logger").exception("Error updating procedure info")

        finally:
            # Schedule next update
            try:
                self._after_id = self.after(300, self._update_loop)
            except Exception:
                pass