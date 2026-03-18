# Imports
import customtkinter as ctk
from ..components.constants import *
from .camera_frame import CameraFrame
from .spectrometer_frame import SpectrometerFrame
from .procedure_queue_frame import ProcedureQueueFrame
from .console_frame import ConsoleFrame

class ProcedureViewerFrame(ctk.CTkFrame):
    """Frame to display current state of procedure"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = BACKGROUND_COLOR)
    
        self.rowconfigure(0, weight = 0)
        self.columnconfigure(0, weight = 1)

        self.rowconfigure(1, weight = 1)
        self.columnconfigure(1,weight = 0)

        # CustomTKinter Frames
        self.procedure_queue_frame = ProcedureQueueFrame(master = self, corner_radius = 0)
        self.procedure_queue_frame.grid(row = 0, column = 0, padx = 10, pady = 10, sticky = "nsew")

        self.camera_frame = CameraFrame(master = self)
        self.camera_frame.grid(row = 0, column = 1, padx = 10, pady = 10, sticky = "ne")

        self.console_frame = ConsoleFrame(master = self, corner_radius = 0)
        self.console_frame.grid(row = 1, column = 1, padx = 10, pady = 10, sticky = "nsew")
        
        self.spectrometer_frame = SpectrometerFrame(master = self, corner_radius = 0)
        self.spectrometer_frame.grid(row = 1, column = 1, padx = 10, pady = 10, sticky = "nsew")




