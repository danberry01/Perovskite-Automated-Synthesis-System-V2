import customtkinter as ctk
from ...components.constants import *

class ProcedureQueueFrame(ctk.CTkFrame):
    """Frame to establish and display system connections"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR, corner_radius = 0, height = 800, width = 300)

        self.grid_propagate(False)