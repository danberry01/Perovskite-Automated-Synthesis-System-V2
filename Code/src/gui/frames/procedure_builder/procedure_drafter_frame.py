import customtkinter as ctk
from ...components.constants import *
from .step_item_frame import StepItem


class ProcedureDrafterFrame(ctk.CTkFrame):
    def __init__(self, master, move_registry, procedure_handler, save_callback=None, logger=None, queue_frame=None, **kwargs):
        super().__init__(master, fg_color=FOREGROUND_COLOR, **kwargs)

        self.move_registry = move_registry
        self.procedure_handler = procedure_handler
        self.queue_frame = queue_frame  # 🔥 NEW

        self.move_registry_moves_truncated = [self.truncate_text(s) for s in move_registry.move_dict.keys()]

        self.save_callback = save_callback
        self.steps = []
        self.step_widgets = []
        self.current_file = "No file loaded"

        self.logger = logger

        self.undo_stack = []
        self.redo_stack = []
        self.selected_index = None

        self.insert_index = None
        self.gap_widgets = []

        # Key bindings
        self.master.bind("<Control-z>", self.undo)
        self.master.bind("<Control-Shift-Z>", self.redo)

        # Layout config
        self.grid_rowconfigure(6, weight=1)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=0)

        self.drag_frame = ctk.CTkScrollableFrame(self, fg_color="#1f1f1f", corner_radius=0)
        self.drag_frame.grid(row=0, column=0, rowspan=7, sticky="nsew", padx=10, pady=10)

        # File label
        self.file_label = ctk.CTkLabel(self, text=f"Editing: {self.current_file}", height=40, anchor="w")
        self.file_label.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="new")

        # Dropdown
        self.dropdown = ctk.CTkOptionMenu(
            self,
            height=60,
            width=300,
            corner_radius=0,
            values=self.move_registry_moves_truncated,
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            button_color=PLAIN_TEXT_COLOR,
            button_hover_color=FOREGROUND_COLOR_TWO
        )
        self.dropdown.set(self.move_registry_moves_truncated[0])
        self.dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="new")

        # Buttons
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

        self.quick_run_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Quick Run",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.quick_run
        )
        self.quick_run_button.grid(row=5, column=1, padx=10, pady=5, sticky="new")

    # -------------------------
    # 🔥 NEW: BUILD REAL PROCEDURE
    # -------------------------
    def _get_procedure(self):
        """Convert UI steps into executable procedure format"""
        procedure = []

        for step in self.steps:
            full_name = None

            # Match truncated UI text back to real move name
            for k in self.move_registry.move_dict.keys():
                if self.truncate_text(k) == step:
                    full_name = k
                    break

            if full_name is None:
                raise ValueError(f"Move not found: {step}")

            procedure.append([full_name])  # no args yet

        return {"Procedure": procedure}

    # -------------------------
    # STEP MANAGEMENT
    # -------------------------
    def add_step(self):
        self.save_state()
        step_name = self.dropdown.get()

        if self.insert_index is not None:
            self.steps.insert(self.insert_index, step_name)
            self.insert_index += 1
        else:
            self.steps.append(step_name)

        self.refresh_steps()

    def remove_step(self):
        if self.selected_index is None:
            return

        self.save_state()
        self.steps.pop(self.selected_index)

        if self.selected_index >= len(self.steps):
            self.selected_index = len(self.steps) - 1

        self.refresh_steps()

    # -------------------------
    # 🔥 FIXED QUICK RUN
    # -------------------------
    def quick_run(self):
        """Quickly run the procedure and update queue UI"""
        if not self.procedure_handler:
            raise RuntimeError("Procedure handler not initialized")

        procedure_data = self._get_procedure()
        procedure = procedure_data["Procedure"]

        # Set procedure
        self.procedure_handler.set_procedure(procedure)

        # 🔥 Update queue UI
        if self.queue_frame is not None:
            self.queue_frame._build_steps(procedure)

        # Start execution
        self.procedure_handler.begin()

        if self.logger:
            self.logger.info("Quick Run started!")
        else:
            print("Quick Run started!")

    # -------------------------
    # MOVE + UI LOGIC
    # -------------------------
    def move_step(self, old_index, new_index):
        if new_index < 0 or new_index >= len(self.steps):
            return

        self.save_state()
        self.steps.insert(new_index, self.steps.pop(old_index))
        self.refresh_steps()

    def refresh_steps(self):
        for widget in self.step_widgets:
            widget.destroy()
        self.step_widgets = []

        for gap in self.gap_widgets:
            gap.destroy()
        self.gap_widgets = []

        total_positions = len(self.steps) + 1
        for pos in range(total_positions):
            gap = ctk.CTkFrame(self.drag_frame, height=8, fg_color=BACKGROUND_COLOR)
            gap.pack(fill="x", padx=5, pady=2)
            gap.bind("<Button-1>", lambda e, idx=pos: self.select_gap(idx))
            self.gap_widgets.append(gap)

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

        self.update_selection_visuals()
        self.update_gap_visuals()

    def save_procedure(self):
        if self.save_callback:
            self.save_callback(self.steps)
        else:
            print("Saved:", self.steps)

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
        self.insert_index = index
        self.selected_index = None
        self.update_selection_visuals()
        self.update_gap_visuals()

    def update_gap_visuals(self):
        for i, gap in enumerate(self.gap_widgets):
            gap.configure(fg_color="red" if i == self.insert_index else BACKGROUND_COLOR)

    # -------------------------
    # 🔧 FIXED TRUNCATION
    # -------------------------
    @staticmethod
    def truncate_text(s, max_chars=25):
        return s if len(s) <= max_chars else s[:max_chars] + "..."