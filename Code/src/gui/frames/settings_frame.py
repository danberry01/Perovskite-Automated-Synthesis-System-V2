import customtkinter as ctk
from ..components.constants import *
import logging

class SettingsFrame(ctk.CTkFrame):
    """Frame to display and configure system settings"""
    def __init__(self, master, procedure_handler=None, **kwargs):
        super().__init__(master, fg_color = BACKGROUND_COLOR)
        
        self.procedure_handler = procedure_handler
        self.logger = logging.getLogger("Main Logger")
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Settings",
            font=("Arial", 24, "bold"),
            text_color="white"
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="nw")
        
        # Settings container
        self.settings_container = ctk.CTkScrollableFrame(
            self,
            fg_color=FOREGROUND_COLOR,
            corner_radius=10
        )
        self.settings_container.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.settings_container.columnconfigure(0, weight=1)
        
        # Procedure Settings Section
        self.proc_section_label = ctk.CTkLabel(
            self.settings_container,
            text="Procedure Settings",
            font=("Arial", 16, "bold"),
            text_color="white"
        )
        self.proc_section_label.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        
        # Min Step Duration Setting
        self.step_duration_frame = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        self.step_duration_frame.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        self.step_duration_frame.columnconfigure(1, weight=1)
        
        self.step_duration_label = ctk.CTkLabel(
            self.step_duration_frame,
            text="Min Step Duration (seconds):",
            justify="left",
            anchor="w"
        )
        self.step_duration_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.step_duration_value = ctk.CTkLabel(
            self.step_duration_frame,
            text="0.5s",
            text_color="gray"
        )
        self.step_duration_value.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        self.step_duration_slider = ctk.CTkSlider(
            self.step_duration_frame,
            from_=0.0,
            to=5.0,
            number_of_steps=50,
            command=self._on_step_duration_change
        )
        self.step_duration_slider.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        # Set initial value
        if self.procedure_handler:
            self.step_duration_slider.set(self.procedure_handler.min_step_duration)
        else:
            self.step_duration_slider.set(0.5)
        
        # Info
        self.info_label = ctk.CTkLabel(
            self.settings_container,
            text="Minimum time each procedure step will take (useful for hardware simulation or UI feedback)",
            justify="left",
            anchor="nw",
            text_color="gray",
            font=("Arial", 10)
        )
        self.info_label.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
    
    def _on_step_duration_change(self, value):
        """Update the step duration when slider changes"""
        duration = float(value)
        self.step_duration_value.configure(text=f"{duration:.2f}s")
        
        if self.procedure_handler:
            self.procedure_handler.set_min_step_duration(duration)
            self.logger.debug(f"Min step duration set to {duration:.2f}s")