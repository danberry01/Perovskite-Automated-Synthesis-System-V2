import customtkinter as ctk
from ..components.constants import *

from ..frames import FileManagerFrame, SettingsFrame

from .procedure_viewer import ProcedureViewerFrame
from .procedure_builder import ProcedureBuilderFrame

class TabViewFrame(ctk.CTkFrame):
    """Shell for managing ___, ___, and ____ tabs"""
    def __init__(self, master, dispatcher, move_registry, procedure_handler, **kwargs):
        super().__init__(master, width=930, height=700, corner_radius=0, fg_color=FOREGROUND_COLOR)
        
        self.dispatcher = dispatcher
        self.move_registry = move_registry
        self.procedure_handler = procedure_handler

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Initialize the dictionary with None
        self.frames = {
            "procedure_builder": None,
            "procedure_viewer": None,
            "file_manager": None,
            "settings": None
        }

        self.current_tab_name = None
        # Start by loading the default tab
        self.goto_tab("file_manager")

    def _create_frame(self, tab):
        """Factory method to instantiate frames only when needed."""
        if tab == "procedure_builder":
            # We need to ensure ProcedureViewer is initialized if Builder needs it
            if self.frames["procedure_viewer"] is None:
                self._create_frame("procedure_viewer")
                
            frame = ProcedureBuilderFrame(
                master=self,
                dispatcher=self.dispatcher,
                move_registry=self.move_registry,
                procedure_handler=self.procedure_handler,
                queue_frame=self.frames["procedure_viewer"].procedure_queue_frame
            )
        elif tab == "procedure_viewer":
            frame = ProcedureViewerFrame(master=self, procedure_handler=self.procedure_handler)
        elif tab == "settings":
            frame = SettingsFrame(master=self)
        elif tab == "file_manager":
            frame = FileManagerFrame(master=self)
        else:
            raise ValueError(f"Unknown tab: {tab}")
        
        frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        return frame

    def goto_tab(self, tab):
        if self.current_tab_name == tab:
            return
        if tab not in self.frames:
            raise ValueError("Tab does not exist")

        # Hide current
        if self.current_tab_name and self.frames[self.current_tab_name]:
            self.frames[self.current_tab_name].grid_remove()

        # Load/Create if necessary
        if self.frames[tab] is None:
            self.frames[tab] = self._create_frame(tab)

        # Show new
        self.frames[tab].grid()
        self.current_tab_name = tab