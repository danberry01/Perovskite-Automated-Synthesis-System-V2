import customtkinter as ctk
from tkinter import filedialog
from ...components.constants import *

from .procedure_drafter_frame import ProcedureDrafterFrame
from .locations_frame import LocationsFrame
from .connection_frame import ConnectionFrame

class ProcedureBuilderFrame(ctk.CTkFrame):
    """Complete interface for creating, saving, loading, and editing procedures"""
    def __init__(self, master, dispatcher, move_registry, procedure_handler, queue_frame, **kwargs):
        super().__init__(master, fg_color = BACKGROUND_COLOR, **kwargs)

        self.dispatcher = dispatcher
        self.move_registry = move_registry
        self.procedure_handler = procedure_handler
        self.queue_frame = queue_frame

        self.columnconfigure(0, weight = 1, minsize = 500)
        self.columnconfigure(1, weight = 0, minsize = 600)
        
        self.rowconfigure(0, weight = 0)
        self.rowconfigure(1, weight = 0)
        self.rowconfigure(2, weight = 1)
        self.rowconfigure(3, weight = 1)

        # CustomTKinter Frames
        self.procedure_drafter_frame = ProcedureDrafterFrame(
            master = self, 
            move_registry = self.move_registry,
            procedure_handler = self.procedure_handler,
            queue_frame = self.queue_frame
        )
        self.procedure_drafter_frame.grid(row = 0, column = 0, rowspan = 4, padx = 10, pady = 10, sticky = "nsew")
        
        # Directory selector frame
        self.dir_config_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR, corner_radius=0)
        self.dir_config_frame.grid(row = 0, column = 1, padx = 10, pady = 10, sticky = "ew")
        
        self.dir_label = ctk.CTkLabel(
            self.dir_config_frame,
            text="Procedures Directory:",
            justify="left",
            anchor="w",
            font=("Arial", 12, "bold")
        )
        self.dir_label.pack(fill="x", padx=10, pady=(10, 5))
        
        self.dir_display = ctk.CTkLabel(
            self.dir_config_frame,
            text=self.procedure_drafter_frame.procedures_dir,
            justify="left",
            anchor="w",
            font=("Arial", 10),
            text_color="gray"
        )
        self.dir_display.pack(fill="x", padx=10, pady=5)
        
        self.dir_select_button = ctk.CTkButton(
            self.dir_config_frame,
            text="Change Directory",
            command=self._change_procedures_dir,
            height=40,
            corner_radius=0
        )
        self.dir_select_button.pack(fill="x", padx=10, pady=(5, 10))
        
        self.connection_frame = ConnectionFrame(master = self, dispatcher = self.dispatcher)
        self.connection_frame.grid(row = 1, column = 1, padx = 10, pady = 10, sticky = "nsew")

        self.locations_frame = LocationsFrame(master = self)
        self.locations_frame.grid(row = 2, column = 1, rowspan = 2, padx = 10, pady = 10, sticky = "nsew")
    
    def _change_procedures_dir(self):
        """Allow user to change the procedures directory"""
        new_dir = filedialog.askdirectory(
            initialdir=self.procedure_drafter_frame.procedures_dir,
            title="Select Procedures Directory"
        )
        
        if new_dir:
            self.procedure_drafter_frame.procedures_dir = new_dir
            self.dir_display.configure(text=new_dir)
            import logging
            logging.getLogger("Main Logger").info(f"Procedures directory changed to: {new_dir}")