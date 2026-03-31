import customtkinter as ctk
from ...components.constants import *


class ArucoCalibrationMainPanel(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color=FOREGROUND_COLOR)
        self.controller = controller

        # Layout configuration
        self.columnconfigure(0, weight=1)

        camera_label = ctk.CTkLabel(self, text="Camera Feed", font=("Arial", 25 "bold"))
        camera_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.camera_display = ctk.CTkLabel(
            self,
            width=600,
            height=400,
            bg_color="#000000",
            text="",
            corner_radius=0
        )
        self.camera_display.grid(row=1, column=0, padx=5, pady=5)

        status_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR_TWO)
        status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        status_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(status_frame, text="Status:", font=("Arial", 20, "bold")).grid(row=0, column=0, padx=5, pady=3)
        self.status_label = ctk.CTkLabel(status_frame, text="Ready", font=("Arial", 20))
        self.status_label.grid(row=0, column=1, padx=5, pady=3, sticky="nsew")

        position_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR_TWO)
        position_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        position_frame.columnconfigure(0, weight=1)

        self.position_label = ctk.CTkLabel(
            position_frame,
            text="Gantry Position: X=0.00mm Y=0.00mm Z=0.00mm",
            font=("Arial", 20),
            justify="left"
        )
        self.position_label.grid(row=0, column=0, padx=5, pady=3, sticky="ew")

        # Expose handles on controller
        self.controller.camera_display = self.camera_display
        self.controller.status_label = self.status_label
        self.controller.position_label = self.position_label
