import customtkinter as ctk
from ..components.constants import *

# Place the ConsoleFrame inside the InfoFrame so the console is part of the
# bottom pane and remains visible when the procedure viewer is not active.
from .procedure_viewer.console_frame import ConsoleFrame


class InfoFrame(ctk.CTkFrame):
    """Frame to display miscellaneous information (contains the console)."""
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=FOREGROUND_COLOR_TWO)

        # Make the console expand to fill the InfoFrame
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Console placed at grid 0,0 as requested
        self.console_frame = ConsoleFrame(master=self)
        self.console_frame.grid(row=0, column=0, sticky="nsew")