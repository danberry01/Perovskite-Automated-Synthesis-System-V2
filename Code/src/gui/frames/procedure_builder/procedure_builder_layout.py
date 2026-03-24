import customtkinter as ctk
from ...components.constants import *

from .locations_frame import LocationsFrame
from .connection_frame import ConnectionFrame

class ProcedureBuilderFrame(ctk.CTkFrame):
    """Complete interface for creating, saving, loading, and editing procedures"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = BACKGROUND_COLOR)

        self.columnconfigure(0, weight = 1, minsize = 500)
        self.columnconfigure(1, weight = 0)
        
        self.rowconfigure(0, weight = 0)
        self.rowconfigure(1, weight = 1)
        self.rowconfigure(2, weight = 1)

        # CustomTKinter Frames
        # self.procedure_queue_frame = ProcedureQueueFrame(master = self)
        # self.procedure_queue_frame.grid(row = 0, column = 0, rowspan = 3, padx = 10, pady = 10, sticky = "nsew")
        
        # self.camera_frame = CameraFrame(master = self)
        # self.camera_frame.grid(row = 0, column = 1, padx = 10, pady = 10, sticky = "nsew")

        # self.console_frame = ConsoleFrame(master = self)
        # self.console_frame.grid(row = 1, column = 1, padx = 10, pady = 10, sticky = "nsew")
        
        # self.spectrometer_frame = SpectrometerFrame(master = self)
        # self.spectrometer_frame.grid(row = 2, column = 1, padx = 10, pady = 10, sticky = "nsew")