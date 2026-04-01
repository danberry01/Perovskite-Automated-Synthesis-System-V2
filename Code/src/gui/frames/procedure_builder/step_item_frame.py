import customtkinter as ctk
import os
import sys

# Import procedure file driver
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(path)
from drivers.procedure_file_driver import ProcedureFile


class StepItem(ctk.CTkFrame):
    def __init__(self, master, text, index, args, move_callback, select_callback, move_registry=None):
        super().__init__(master, corner_radius=5, fg_color="transparent")

        self.index = index
        self.move_callback = move_callback
        self.select_callback = select_callback
        self.move_registry = move_registry

        self.args = list(args)
        self.entries = []
        self.dropdowns = []
        self.checkboxes = []

        self._selected = False

        # --- Top row: arrows + step name ---
        self.top_row = ctk.CTkFrame(self, fg_color="transparent")
        self.top_row.pack(fill="x", padx=5, pady=(4, 2))

        self.up_button = ctk.CTkButton(
            self.top_row,
            text="↑",
            width=30,
            height=28,
            corner_radius=4,
            command=self.move_up
        )
        self.up_button.pack(side="left", padx=(0, 4))

        self.label = ctk.CTkLabel(
            self.top_row,
            text=text,
            anchor="w",
            text_color="white"  # explicitly visible
        )
        self.label.pack(side="left", fill="x", expand=True)
        self.label.bind("<Button-1>", lambda e: self.select_callback(self.index))
        self.top_row.bind("<Button-1>", lambda e: self.select_callback(self.index))

        self.down_button = ctk.CTkButton(
            self.top_row,
            text="↓",
            width=30,
            height=28,
            corner_radius=4,
            command=self.move_down
        )
        self.down_button.pack(side="right", padx=(4, 0))

        # --- Argument row: only if args exist ---
        if self.args:
            self.args_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.args_frame.pack(fill="x", padx=5, pady=(0, 5))

            self.arg_labels = []
            for i, val in enumerate(self.args):
                container = ctk.CTkFrame(self.args_frame, fg_color="transparent")
                container.pack(side="left", padx=(0, 8), pady=2)

                arg_label = ctk.CTkLabel(container, text=f"{i}:", width=16, text_color="white")
                arg_label.pack(side="left")

                # Special handling for specific functions
                if text == "move_to_location" and i == 0:
                    # Dropdown for location names
                    location_names = self._get_location_names()
                    dropdown = ctk.CTkOptionMenu(
                        container, 
                        width=120,
                        values=location_names,
                        command=lambda selected, idx=i: self.update_arg(idx, selected)
                    )
                    if str(val) in location_names:
                        dropdown.set(str(val))
                    else:
                        dropdown.set(location_names[0] if location_names else "")
                    dropdown.pack(side="left")
                    self.dropdowns.append(dropdown)
                    
                elif text == "move_toolhead" and i == 3:
                    # Checkbox for relative
                    checkbox = ctk.CTkCheckBox(
                        container,
                        text="",
                        width=20,
                        command=lambda idx=i: self.update_checkbox_arg(idx)
                    )
                    checkbox.pack(side="left")
                    # Set initial state
                    if val and int(val) >= 1:
                        checkbox.select()
                    self.checkboxes.append((checkbox, i))
                    
                else:
                    # Default entry for other args
                    entry = ctk.CTkEntry(container, width=72)
                    entry.insert(0, str(val))
                    entry.pack(side="left")
                    entry.bind("<FocusOut>", self._make_update_callback(i))
                    self.entries.append(entry)
                    
                self.arg_labels.append(arg_label)

        self.set_selected(False)

    def _make_update_callback(self, index):
        return lambda event: self.update_arg(index)

    def _get_location_names(self):
        """Get list of location names from persistent locations"""
        if not self.move_registry:
            return ["No locations available"]
        
        try:
            # Try to access locations if already loaded
            if hasattr(self.move_registry, 'locations') and self.move_registry.locations:
                return [loc[0] for loc in self.move_registry.locations if loc[0]]
            
            # Otherwise load them
            locations = ProcedureFile().Open("persistant/locations.yml")
            return [loc[0] for loc in locations if loc[0]]
        except Exception as e:
            print(f"Error loading locations: {e}")
            return ["Error loading locations"]

    def update_checkbox_arg(self, index):
        """Update argument from checkbox state"""
        for checkbox, idx in self.checkboxes:
            if idx == index:
                self.args[index] = 1 if checkbox.get() else 0
                break

    def update_arg(self, index, value=None):
        """Update argument value"""
        if value is not None:
            self.args[index] = value
        else:
            try:
                raw_value = self.entries[index].get().strip()
                try:
                    value = int(raw_value)
                except ValueError:
                    try:
                        value = float(raw_value)
                    except ValueError:
                        value = raw_value
                self.args[index] = value
            except Exception:
                pass

    def move_up(self):
        self.move_callback(self.index, self.index - 1)

    def move_down(self):
        self.move_callback(self.index, self.index + 1)

    def set_selected(self, selected):
        self._selected = selected
        fg = "#444444" if selected else "transparent"
        self.configure(fg_color=fg)
        self.top_row.configure(fg_color=fg)
        if hasattr(self, "args_frame"):
            self.args_frame.configure(fg_color=fg)