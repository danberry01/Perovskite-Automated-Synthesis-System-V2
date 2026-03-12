import customtkinter as ctk
from ..components.constants import *

class InfoFrame(ctk.CTkFrame):
    """Frame to display miscellaneous information"""
    def __init__(self, master, **kwargs):
            super().__init__(
                master,
                width = 730,
                height = 150,
                corner_radius = 0,
                fg_color = FOREGROUND_COLOR
            )