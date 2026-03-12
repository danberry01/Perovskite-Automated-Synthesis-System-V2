import customtkinter as ctk
from ..components.constants import *

class SettingsFrame(ctk.CTkFrame):
    """Frame to display current state of procedure"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = "#1500FF")