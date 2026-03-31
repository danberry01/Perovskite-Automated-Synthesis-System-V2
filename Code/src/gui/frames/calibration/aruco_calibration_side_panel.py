import customtkinter as ctk
from ...components.constants import *


class ArucoCalibrationSidePanel(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color=FOREGROUND_COLOR)
        self.controller = controller

        self.columnconfigure(0, weight=1)

        controls_label = ctk.CTkLabel(self, text="Calibration Controls", font=("Arial", 12, "bold"))
        controls_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR)
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        self.scan_button = ctk.CTkButton(
            button_frame,
            text="Start Calibration Scan",
            command=self.controller._start_calibration_scan,
            fg_color="#000000",
            hover_color=FOREGROUND_COLOR_TWO
        )
        self.scan_button.grid(row=0, column=0, sticky="ew", padx=2, pady=5)

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.controller._cancel_calibration,
            fg_color="#C62828",
            hover_color="#880E4F",
            state="disabled"
        )
        self.cancel_button.grid(row=0, column=1, sticky="ew", padx=2, pady=5)

        self.home_button = ctk.CTkButton(
            button_frame,
            text="Home Gantry",
            command=self.controller._home_gantry,
            fg_color="#000000",
            hover_color=FOREGROUND_COLOR_TWO
        )
        self.home_button.grid(row=1, column=0, sticky="ew", padx=2, pady=5)

        self.refresh_position_button = ctk.CTkButton(
            button_frame,
            text="Refresh Position",
            command=self.controller._refresh_position,
            fg_color="#000000",
            hover_color=FOREGROUND_COLOR_TWO
        )
        self.refresh_position_button.grid(row=1, column=1, sticky="ew", padx=2, pady=5)

        markers_label = ctk.CTkLabel(self, text="Detected Markers", font=("Arial", 25, "bold"))
        markers_label.grid(row=2, column=0, sticky="nsew", padx=5, pady=(10, 5))

        self.markers_display = ctk.CTkTextbox(
            self,
            width=280,
            height=150,
            font=("Courier", 20),
            state="disabled",
            text_color=PLAIN_TEXT_COLOR
        )
        self.markers_display.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)

        positions_label = ctk.CTkLabel(self, text="Calibrated Positions", font=("Arial",25, "bold"))
        positions_label.grid(row=4, column=0, sticky="nsew", padx=5, pady=(10, 5))

        self.positions_listbox = ctk.CTkTextbox(
            self,
            width=280,
            height=150,
            font=("Courier", 20),
            state="disabled",
            text_color=PLAIN_TEXT_COLOR
        )
        self.positions_listbox.grid(row=5, column=0, sticky="nsew", padx=5, pady=5)

        management_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR)
        management_frame.grid(row=6, column=0, sticky="ew", padx=5, pady=5)
        management_frame.columnconfigure(0, weight=1)
        management_frame.columnconfigure(1, weight=1)

        self.save_button = ctk.CTkButton(
            management_frame,
            text="Save Selected",
            command=self.controller._save_selected_position,
            fg_color="#000000",
            hover_color=FOREGROUND_COLOR_TWO,
            state="disabled"
        )
        self.save_button.grid(row=0, column=0, sticky="ew", padx=2, pady=5)

        self.delete_button = ctk.CTkButton(
            management_frame,
            text="Delete Selected",
            command=self.controller._delete_selected_position,
            fg_color="#000000",
            hover_color=FOREGROUND_COLOR_TWO,
            state="disabled"
        )
        self.delete_button.grid(row=0, column=1, sticky="ew", padx=2, pady=5)

        self.clear_all_button = ctk.CTkButton(
            management_frame,
            text="Clear All",
            command=self.controller._clear_all_calibrations,
            fg_color="#000000",
            hover_color=FOREGROUND_COLOR_TWO
        )
        self.clear_all_button.grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=5)

        # Expose handles on controller
        self.controller.scan_button = self.scan_button
        self.controller.cancel_button = self.cancel_button
        self.controller.home_button = self.home_button
        self.controller.refresh_position_button = self.refresh_position_button
        self.controller.markers_display = self.markers_display
        self.controller.positions_listbox = self.positions_listbox
        self.controller.save_button = self.save_button
        self.controller.delete_button = self.delete_button
        self.controller.clear_all_button = self.clear_all_button
