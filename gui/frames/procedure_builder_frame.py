import customtkinter as ctk
from ..components.theme import *

class ProcedureBuilderFrame(ctk.CTkFrame):
    """Complete interface for creating, saving, loading, and editing procedures"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)