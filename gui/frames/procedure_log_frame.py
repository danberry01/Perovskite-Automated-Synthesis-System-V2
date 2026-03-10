import customtkinter as ctk
from ..components.theme import *

class ProcedureLogFrame(ctk.CTkFrame):
    """Frame to display current state of procedure"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)