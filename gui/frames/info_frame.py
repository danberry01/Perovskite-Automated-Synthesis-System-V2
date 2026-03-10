import customtkinter as ctk
from ..components.theme import *

class InfoFrame(ctk.CTkFrame):
    """Frame to display miscellaneous information"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)