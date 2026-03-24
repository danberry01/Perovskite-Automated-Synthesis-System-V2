import customtkinter as ctk
from ...components.constants import *

class ConnectionFrame(ctk.CTkFrame):
    """Frame to establish and display system connections"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)