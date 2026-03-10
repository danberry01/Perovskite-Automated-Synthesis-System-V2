import customtkinter as ctk
from ..components.theme import *

class CameraFrame(ctk.CTkFrame):
    """Frame for displaying camera feed with coordinate projection, and filter buttons"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)
        