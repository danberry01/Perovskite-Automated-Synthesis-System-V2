import customtkinter as ctk
from inspect import signature
from tkinter import filedialog
import logging
import os
import sys

from ...components.constants import *
from .step_item_frame import StepItem

# Import procedure file driver
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(path)
from drivers.procedure_file_driver import ProcedureFile


class ProcedureDrafterFrame(ctk.CTkFrame):
    def __init__(self, master, move_registry, procedure_handler, save_callback=None, logger=None, queue_frame=None, **kwargs):
        super().__init__(master, fg_color=FOREGROUND_COLOR, **kwargs)

        self.move_registry = move_registry
        self.procedure_handler = procedure_handler
        self.queue_frame = queue_frame
        self.save_callback = save_callback
        self.logger = logger

        # Determine procedures directory
        self.procedures_dir = self._get_procedures_dir()

        # Keep the original-style move list, but preserve a direct name mapping
        self.move_names = list(self.move_registry.move_dict.keys())
        self.move_registry_moves_truncated = [self.truncate_text(s) for s in self.move_names]

        # each step is now {"name": str, "args": list}
        self.steps = []
        self.step_widgets = []
        self.current_file = "No file loaded"
        self.current_file_path = None  # Track the full path to the current file

        self.undo_stack = []
        self.redo_stack = []
        self.selected_index = None
        self.insert_index = None
        self.gap_widgets = []

        self.master.bind("<Control-z>", self.undo)
        self.master.bind("<Control-Shift-Z>", self.redo)

        self.grid_rowconfigure(9, weight=1)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=0)

        self.drag_frame = ctk.CTkScrollableFrame(self, fg_color="#1f1f1f", corner_radius=0)
        self.drag_frame.grid(row=0, column=0, rowspan=9, sticky="nsew", padx=10, pady=10)

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

        self.new_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="New Procedure",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.new_procedure
        )
        self.new_button.grid(row=4, column=1, padx=10, pady=5, sticky="new")

        self.load_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Load Procedure",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.load_procedure
        )
        self.load_button.grid(row=5, column=1, padx=10, pady=5, sticky="new")

        self.save_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Save Procedure",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.save_procedure
        )
        self.save_button.grid(row=6, column=1, padx=10, pady=5, sticky="new")

        self.save_as_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Save As",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self._save_as_procedure
        )
        self.save_as_button.grid(row=7, column=1, padx=10, pady=5, sticky="new")

        self.quick_run_button = ctk.CTkButton(
            self,
            height=60,
            corner_radius=0,
            text="Quick Run",
            text_color=BACKGROUND_COLOR,
            fg_color=PLAIN_TEXT_COLOR,
            command=self.quick_run
        )
        self.quick_run_button.grid(row=8, column=1, padx=10, pady=5, sticky="new")

    def new_procedure(self):
        """Clear all steps and start a new procedure"""
        self.save_state()
        self.steps = []
        self.current_file = "Unsaved Procedure"
        self.current_file_path = None
        self.file_label.configure(text=f"Editing: {self.current_file}")
        self.refresh_steps()
        logging.getLogger("Main Logger").info("New procedure started")

    def _get_procedures_dir(self):
        """Get the absolute path to the procedures directory"""
        # Try multiple locations
        possible_dirs = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'procedures')),
            os.path.abspath(os.path.join(os.getcwd(), 'src', 'procedures')),
            os.path.abspath(os.path.join(os.getcwd(), 'procedures')),
        ]
        
        for proc_dir in possible_dirs:
            if os.path.isdir(proc_dir):
                logging.getLogger("Main Logger").debug(f"Using procedures directory: {proc_dir}")
                return proc_dir
        
        # If no directory exists, use the first option and try to create it
        default_dir = possible_dirs[0]
        os.makedirs(default_dir, exist_ok=True)
        logging.getLogger("Main Logger").info(f"Created procedures directory: {default_dir}")
        return default_dir

    def _selected_move_full_name(self):
        """Map the selected truncated dropdown text back to the real move name."""
        selected = self.dropdown.get()
        try:
            idx = self.move_registry_moves_truncated.index(selected)
            return self.move_names[idx]
        except ValueError:
            # fallback: exact match on full names
            if selected in self.move_names:
                return selected
            raise ValueError(f"Move not found: {selected}")

    def _default_args_for_move(self, full_name):
        """Create placeholder args based on the function signature."""
        func = self.move_registry.move_dict[full_name]
        sig = signature(func)

        default_args = []
        for param in list(sig.parameters.values())[1:]:  # keep your existing convention
            if param.default is not param.empty:
                default_args.append(param.default)
            else:
                default_args.append(0)
        return default_args

    def add_step(self):
        self.save_state()

        full_name = self._selected_move_full_name()
        default_args = self._default_args_for_move(full_name)

        step = {
            "name": full_name,
            "args": default_args
        }

        if self.insert_index is not None:
            self.steps.insert(self.insert_index, step)
            self.insert_index += 1
        else:
            self.steps.append(step)

        self.refresh_steps()

    def remove_step(self):
        if self.selected_index is None:
            return

        self.save_state()
        self.steps.pop(self.selected_index)

        if self.selected_index >= len(self.steps):
            self.selected_index = len(self.steps) - 1

        self.refresh_steps()

    def quick_run(self):
        """
        Run the current procedure immediately.
        Send the current steps to the procedure handler and start execution.
        """
        import threading
        import logging
        
        if not self.steps:
            logging.getLogger("Main Logger").warning("No steps to run")
            return
        
        # Convert UI steps into executable procedure format
        procedure = []
        for step in self.steps:
            procedure.append([step["name"], *step["args"]])
        
        # Set the procedure in the handler
        if self.procedure_handler:
            self.procedure_handler.set_procedure(procedure)
            
            # Update the queue frame display if available
            if self.queue_frame:
                self.queue_frame._build_steps(procedure)
                self.queue_frame.current_procedure = "Quick Run"
                self.queue_frame.current_procedure_label.configure(
                    text=f"Current Procedure: Quick Run - {len(procedure)} steps"
                )
            
            # Start execution in a separate thread
            def run_procedure():
                try:
                    self.procedure_handler.begin()
                except Exception as e:
                    logging.getLogger("Main Logger").error(f"Error running procedure: {e}")
            
            threading.Thread(target=run_procedure, daemon=True).start()
            logging.getLogger("Main Logger").info(f"Quick Run: Starting procedure with {len(procedure)} steps")
        else:
            logging.getLogger("Main Logger").error("No procedure handler available")

    def _get_procedure(self):
        """Convert UI steps into executable procedure format."""
        procedure = []
        for step in self.steps:
            procedure.append([step["name"], *step["args"]])
        return {"Procedure": procedure}

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

        # Original layout style: gap, step, gap, step, ...
        total_positions = len(self.steps) + 1
        for pos in range(total_positions):
            gap = ctk.CTkFrame(self.drag_frame, height=8, fg_color=BACKGROUND_COLOR)
            gap.pack(fill="x", padx=5, pady=2)
            gap.bind("<Button-1>", lambda e, idx=pos: self.select_gap(idx))
            self.gap_widgets.append(gap)

            if pos < len(self.steps):
                step = self.steps[pos]
                item = StepItem(
                    self.drag_frame,
                    text=step["name"],
                    index=pos,
                    args=step["args"],
                    move_callback=self.move_step,
                    select_callback=self.select_step
                )
                item.pack(fill="x", padx=5, pady=2)
                self.step_widgets.append(item)

        self.update_selection_visuals()
        self.update_gap_visuals()

    def save_procedure(self):
        """Save the current procedure to a YAML file"""
        if not self.steps:
            logging.getLogger("Main Logger").warning("No steps to save")
            return
        
        # If file already has a path, save to that path directly
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
            return
        
        # Otherwise, ask for a new file
        self._save_as_procedure()

    def _save_as_procedure(self):
        """Save as with file dialog"""
        file_path = filedialog.asksaveasfilename(
            initialdir=self.procedures_dir,
            defaultextension=".yml",
            filetypes=(("YAML files", "*.yml"), ("All files", "*.*"))
        )
        
        if not file_path:
            return
        
        self._save_to_file(file_path)

    def _save_to_file(self, file_path):
        """Actually save the file"""
        try:
            # Ensure .yml extension
            if not file_path.endswith('.yml'):
                file_path += '.yml'
            
            # Convert steps to procedure format
            procedure = []
            for step in self.steps:
                procedure.append([step["name"], *step["args"]])
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save using ProcedureFile driver
            file_driver = ProcedureFile()
            file_driver.Save(file_path, {"Procedure": procedure})
            
            # Verify file was actually created
            if os.path.exists(file_path):
                # Update tracking
                self.current_file_path = file_path
                self.current_file = os.path.basename(file_path)
                self.file_label.configure(text=f"Editing: {self.current_file}")
                
                file_size = os.path.getsize(file_path)
                logging.getLogger("Main Logger").info(f"Procedure saved to {file_path} ({file_size} bytes)")
            else:
                logging.getLogger("Main Logger").error(f"File write failed - file does not exist: {file_path}")
                
        except Exception as e:
            logging.getLogger("Main Logger").error(f"Failed to save procedure: {e}")
            import traceback
            traceback.print_exc()

    def load_procedure(self):
        """Load a procedure from a YAML file"""
        file_path = filedialog.askopenfilename(
            initialdir=self.procedures_dir,
            filetypes=(("YAML files", "*.yml*"),)
        )
        
        if not file_path:
            return
        
        try:
            # Load using ProcedureFile driver
            file_driver = ProcedureFile()
            file_data = file_driver.Open(path=file_path)
            
            if file_data is None:
                logging.getLogger("Main Logger").error(f"Could not open file: {file_path}")
                return
            
            procedure = file_data.get("Procedure")
            if not procedure:
                logging.getLogger("Main Logger").error("No 'Procedure' key found in file")
                return
            
            # Clear current steps
            self.steps = []
            
            # Convert procedure format to step format
            for proc_step in procedure:
                if isinstance(proc_step, list) and len(proc_step) > 0:
                    func_name = proc_step[0]
                    func_args = proc_step[1:]
                    
                    step = {
                        "name": func_name,
                        "args": list(func_args)
                    }
                    self.steps.append(step)
            
            # Update tracking
            self.current_file_path = file_path
            self.current_file = os.path.basename(file_path)
            self.file_label.configure(text=f"Editing: {self.current_file}")
            
            # Refresh display
            self.refresh_steps()
            
            logging.getLogger("Main Logger").info(f"Procedure loaded from {file_path} ({len(self.steps)} steps)")
        except Exception as e:
            logging.getLogger("Main Logger").error(f"Failed to load procedure: {e}")
            import traceback
            traceback.print_exc()

    def set_current_file(self, filename):
        self.current_file = filename
        self.file_label.configure(text=f"Editing: {self.current_file}")

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
            if i == self.insert_index:
                gap.configure(fg_color="red")
            else:
                gap.configure(fg_color=BACKGROUND_COLOR)

    @staticmethod
    def truncate_text(s, max_chars=25):
        return s if len(s) <= max_chars else s[:max_chars] + "..."