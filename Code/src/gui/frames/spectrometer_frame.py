import customtkinter as ctk
from ..components.constants import *

class SpectrometerFrame(ctk.CTkFrame):
    """Frame to display spectrometer readings"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)