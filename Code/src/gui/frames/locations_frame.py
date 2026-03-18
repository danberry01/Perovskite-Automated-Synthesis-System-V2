import customtkinter as ctk
from ..components.constants import *

class LocationsFrame(ctk.CTkFrame):
    """Frame to display locations list (might remove)"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)