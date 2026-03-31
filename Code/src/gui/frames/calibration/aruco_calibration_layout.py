import customtkinter as ctk
from .aruco_calibration_main_panel import ArucoCalibrationMainPanel
from .aruco_calibration_side_panel import ArucoCalibrationSidePanel


class ArucoCalibrationLayout(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1, minsize = 400)
        self.rowconfigure(0, weight=1)

        self.main_panel = ArucoCalibrationMainPanel(self, controller=controller)
        self.main_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.side_panel = ArucoCalibrationSidePanel(self, controller=controller)
        self.side_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
