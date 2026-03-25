import customtkinter as ctk
from ...components.constants import *
from .step_item_frame import StepItem   # <-- change to the correct path

PROCEDURE_STEPS = [
    "Step 1",
    "Step 2",
    "Step n",
    "Really long step with many words to see what would happen on the gui screen if it was there"
    "Step 4"
]

class ProcedureDrafterFrame(ctk.CTkFrame):
    def __init__(self, master, save_callback=None, **kwargs):
        super().__init__(master, fg_color=FOREGROUND_COLOR, **kwargs)

        self.procedure_steps_truncated = [self.truncate_text(s) for s in PROCEDURE_STEPS]

        self.save_callback = save_callback
        self.steps = []
        self.step_widgets = []
        self.current_file = "No file loaded"  # NEW

        self.undo_stack = []
        self.redo_stack = []
        self.selected_index = None  # for feature 2

        self.insert_index = None  # None means no gap is selected
        self.gap_widgets = []  # track all gap frames

        # Key bindings
        self.master.bind("<Control-z>", self.undo)
        self.master.bind("<Control-Shift-Z>", self.redo)

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)

        self.grid_columnconfigure(0, weight=4)  # drag area
        self.grid_columnconfigure(1, weight=0)  # controls

        self.drag_frame = ctk.CTkScrollableFrame(self, fg_color="#1f1f1f", corner_radius=0)
        self.drag_frame.grid(row=0, column=0, rowspan=5, sticky="nsew", padx=10, pady=10)

        # NEW: Current file label
        self.file_label = ctk.CTkLabel(
            self,
            text=f"Editing: {self.current_file}",
            height=40,
            anchor="w"
        )
        self.file_label.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="new")

        self.dropdown = ctk.CTkOptionMenu(
            self,
            height=60,
            width = 300,
            corner_radius=0,
            values=self.procedure_steps_truncated,
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            button_color=PLAIN_TEXT_COLOR,
            button_hover_color=FOREGROUND_COLOR_TWO
        )
        self.dropdown.set(self.procedure_steps_truncated[0])
        self.dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="new")

        self.add_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Add Step",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.add_step
        )
        self.add_button.grid(row=2, column=1, padx=10, pady=5, sticky="new")

        # NEW: Remove button
        self.remove_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Remove Step",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.remove_step
        )
        self.remove_button.grid(row=3, column=1, padx=10, pady=5, sticky="new")

        self.save_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Save Procedure",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.save_procedure
        )
        self.save_button.grid(row=4, column=1, padx=10, pady=5, sticky="new")

    def add_step(self):
        self.save_state()
        step_name = self.dropdown.get()

        if self.insert_index is not None:
            self.steps.insert(self.insert_index, step_name)
            self.insert_index += 1  # keep selection on new gap after inserted step
        else:
            self.steps.append(step_name)

        self.refresh_steps()

    # NEW: remove function
    def remove_step(self):
        if self.selected_index is None:
            return  # nothing selected

        self.save_state()
        # Remove by index, not by name
        self.steps.pop(self.selected_index)

        # Adjust selection
        if self.selected_index >= len(self.steps):
            self.selected_index = len(self.steps) - 1

        self.refresh_steps()

    def move_step(self, old_index, new_index):
        if new_index < 0 or new_index >= len(self.steps):
            return

        self.save_state()
        self.steps.insert(new_index, self.steps.pop(old_index))
        self.refresh_steps()

    def refresh_steps(self):
        # Destroy all existing step widgets
        for widget in self.step_widgets:
            widget.destroy()
        self.step_widgets = []

        # Destroy all existing gap widgets
        for gap in self.gap_widgets:
            gap.destroy()
        self.gap_widgets = []

        # Build the layout: top gap, step, gap, step, ..., bottom gap
        total_positions = len(self.steps) + 1  # one gap above each step + one at bottom
        for pos in range(total_positions):
            # Create gap frame
            gap = ctk.CTkFrame(self.drag_frame, height=4, fg_color=BACKGROUND_COLOR)
            gap.pack(fill="x", padx=5, pady=2)
            gap.bind("<Button-1>", lambda e, idx=pos: self.select_gap(idx))
            self.gap_widgets.append(gap)

            # If this is not the bottom-most gap, add the step widget below it
            if pos < len(self.steps):
                step_name = self.steps[pos]
                item = StepItem(
                    self.drag_frame,
                    text=step_name,
                    index=pos,
                    move_callback=self.move_step,
                    select_callback=self.select_step
                )
                item.pack(fill="x", padx=5, pady=2)
                self.step_widgets.append(item)

        # Update visual highlights
        self.update_selection_visuals()
        self.update_gap_visuals()


    def save_procedure(self):
        if self.save_callback:
            self.save_callback(self.steps)
        else:
            print("Saved:", self.steps)

    # OPTIONAL: call this when loading a file
    def set_current_file(self, filename):
        self.current_file = filename
        self.file_label.configure(text=f"Editing: {self.current_file}")

    # Save State Functions to track a list of undo and redo options
    def undo(self, event=None):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.steps.copy())
        self.steps = self.undo_stack.pop()
        self.refresh_steps()

    def redo(self, event=None):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.steps.copy())
        self.steps = self.redo_stack.pop()
        self.refresh_steps()

    def save_state(self):
        self.undo_stack.append(self.steps.copy())
        self.redo_stack.clear()

    def select_step(self, index):
        self.selected_index = index
        self.insert_index = None
        self.update_selection_visuals()
        self.update_gap_visuals()

    def update_selection_visuals(self):
        for i, widget in enumerate(self.step_widgets):
            widget.set_selected(i == self.selected_index)

    def select_gap(self, index):
        """Select a gap between steps. `index` is where new step will be inserted."""
        self.insert_index = index
        self.selected_index = None  # deselect any step
        self.update_selection_visuals()
        self.update_gap_visuals()

    def update_gap_visuals(self):
        for i, gap in enumerate(self.gap_widgets):
            if i == self.insert_index:
                gap.configure(fg_color="red")  # selected gap
            else:
                gap.configure(fg_color=BACKGROUND_COLOR)

    @staticmethod
    def truncate_text(s, max_chars=25):
        """Truncate string and add ellipsis if too long"""
        return s if len(s) <= max_chars else s[:38] + "..."