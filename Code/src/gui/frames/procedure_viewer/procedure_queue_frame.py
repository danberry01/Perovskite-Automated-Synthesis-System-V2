from logging import Logger
import logging
import customtkinter as ctk
from tkinter import filedialog
import sys
import os

from services.procedure_handler import ProcedureHandler
from ...components.constants import *

# get current directory so we can import from outside guiFrames folder
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(path)
from drivers.procedure_file_driver import ProcedureFile


class StepStateFrame(ctk.CTkFrame):
    """Visual representation of a single procedure step"""

    def __init__(self, master, text):
        super().__init__(master, corner_radius=5, height=40)

        self.label = ctk.CTkLabel(self, text=text, anchor="w")
        self.label.pack(fill="both", expand=True, padx=10)

        self.set_state("idle")

    def set_state(self, state):
        """Update color based on state"""
        if state == "idle":
            self.configure(fg_color="#808080")  # gray
        elif state == "running":
            self.configure(fg_color="#51aef6")  # blue
        elif state == "complete":
            self.configure(fg_color="#32de3b")  # green
        elif state == "error":
            self.configure(fg_color="#fc1e3c")  # red


class ProcedureQueueFrame(ctk.CTkFrame):
    """Frame to establish and display procedure execution queue"""

    def __init__(self, master, procedure_handler, **kwargs):
        super().__init__(master, fg_color=FOREGROUND_COLOR, corner_radius=0, height=800, width=300)

        self.procedure_handler = procedure_handler
        self.killed = False
        self.logger = logging.getLogger("Main Logger")

        self.steps = []
        self.step_frames = []

        # --- TITLE ---
        self.title_label = ctk.CTkLabel(
            master=self,
            text="Procedure Overview",
            anchor="w",
            font=("Arial", 20, "bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=4, padx=20, pady=20, sticky="nswe")

        # --- CONTROLS ---
        self.start_button = ctk.CTkButton(self, text="Start", width=80, height=50, command=self._start_procedure)
        self.start_button.grid(row=1, column=0, padx=5, pady=20)

        self.pause_button = ctk.CTkButton(self, text="Pause", width=80, height=50, command=self._toggle_pause)
        self.pause_button.grid(row=1, column=1, padx=5, pady=20)

        self.stop_button = ctk.CTkButton(self, text="Stop", width=80, height=50, command=self._stop_procedure)
        self.stop_button.grid(row=1, column=2, padx=5, pady=20)

        self.kill_button = ctk.CTkButton(
            self, text="Kill",
            fg_color="#a10e22", hover_color="#45060f",
            width=80, height=50,
            command=self._kill_procedure
        )
        self.kill_button.grid(row=1, column=3, padx=5, pady=20)

        # --- PROGRESS ---
        self.time_label = ctk.CTkLabel(self, text="")
        self.time_label.grid(row=2, column=0, padx=5, pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate", width=200)
        self.progress_bar.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="nw")

        self.progress_label = ctk.CTkLabel(self, text="0%")
        self.progress_label.grid(row=2, column=3, padx=5, pady=5)

        # --- PROCEDURE IMPORT ---
        self.current_procedure = "default_procedure.yml"

        self.import_button = ctk.CTkButton(
            self, text="Import", width=80, height=30,
            command=self._import_procedure
        )
        self.import_button.grid(row=3, column=0, padx=5, pady=5)

        self.current_procedure_label = ctk.CTkLabel(
            self, text=f"Current Procedure: {self.current_procedure}"
        )
        self.current_procedure_label.grid(row=3, column=1, columnspan=3, padx=5, pady=5)

        # --- STEP DISPLAY AREA ---
        self.steps_container = ctk.CTkScrollableFrame(self, fg_color="#1f1f1f")
        self.steps_container.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)

        self.grid_rowconfigure(4, weight=1)

        self._update()

    # -------------------------
    # STEP UI MANAGEMENT
    # -------------------------

    def _build_steps(self, steps):
        """Rebuild UI step list"""
        # Clear old
        for frame in self.step_frames:
            frame.destroy()

        self.step_frames = []
        self.steps = steps

        # Create new
        for step in steps:
            frame = StepStateFrame(self.steps_container, text=step)
            frame.pack(fill="x", padx=5, pady=3)
            self.step_frames.append(frame)

    def _update_step_states(self):
        """Update step colors based on handler state"""

        if not self.steps:
            return

        try:
            current_index = self.procedure_handler.get_current_step_index()
            error = self.procedure_handler.has_error()
        except Exception:
            return

        for i, frame in enumerate(self.step_frames):
            if error and i == current_index:
                frame.set_state("error")
            elif i < current_index:
                frame.set_state("complete")
            elif i == current_index:
                frame.set_state("running")
            else:
                frame.set_state("idle")

    # -------------------------
    # MAIN UPDATE LOOP
    # -------------------------

    def _update(self):
        """Update UI continuously"""

        # Button states
        if not self.procedure_handler.started.is_set():
            self.start_button.configure(state="normal")
            self.pause_button.configure(state="disabled", text="Pause")
            self.stop_button.configure(state="disabled")
            self.import_button.configure(state="normal")
        else:
            self.start_button.configure(state="disabled")
            self.pause_button.configure(state="normal")
            self.stop_button.configure(state="normal")
            self.import_button.configure(state="disabled")

        if self.killed:
            self.start_button.configure(state="disabled")
            self.pause_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.kill_button.configure(state="disabled")
            self.import_button.configure(state="disabled")

        # Progress
        self.time_label.configure(text=self.procedure_handler.get_time_elapsed())
        progress = self.procedure_handler.get_progress()
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"{int(progress * 100)}%")

        # Step state updates
        self._update_step_states()

        self.after(300, self._update)

    # -------------------------
    # BUTTON CALLBACKS
    # -------------------------

    def _start_procedure(self):
        if self.procedure_handler.started.is_set():
            self.logger.warning("Procedure already started")
            return

        self.procedure_handler.begin()

    def _toggle_pause(self):
        if not self.procedure_handler.paused.is_set():
            self.procedure_handler.pause()
            self.pause_button.configure(text="Resume")
        else:
            self.procedure_handler.resume()
            self.pause_button.configure(text="Pause")

        self.pause_button.configure(state="disabled")

    def _stop_procedure(self):
        self.procedure_handler.stop()

    def _kill_procedure(self):
        self.killed = True
        self.procedure_handler.kill()

    # -------------------------
    # IMPORT + REFRESH
    # -------------------------

    def _import_procedure(self):
        file_path = filedialog.askopenfilename(
            initialdir="src/procedures/",
            title="Select a File",
            filetypes=(("Yaml files", "*.yml*"),)
        )

        if file_path != "":
            file = ProcedureFile().Open(path=file_path)
            procedure = file["Procedure"]

            # SET PROCEDURE
            self.procedure_handler.set_procedure(procedure)

            # UPDATE LABEL
            procedure_name = os.path.basename(file_path)
            self.current_procedure = procedure_name
            self.current_procedure_label.configure(
                text=f"Current Procedure: {self.current_procedure}"
            )

            # BUILD STEP UI (RESET OLD)
            step_names = [step["name"] if isinstance(step, dict) and "name" in step else str(step)
                          for step in procedure]

            self._build_steps(step_names)