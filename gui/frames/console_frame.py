import customtkinter as ctk
from ..components.constants import *

class ConsoleFrame(ctk.CTkFrame):
    """Frame that displays the console"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)