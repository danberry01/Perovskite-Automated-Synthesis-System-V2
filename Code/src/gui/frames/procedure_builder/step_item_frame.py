import customtkinter as ctk
import os
import sys
from inspect import signature

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
        self.function_name = text  # Store function name for parameter mapping
        
        # Keep a reference to the parent's args list so updates propagate
        # back to ProcedureDrafterFrame.steps
        self.args = args
        self.control_widgets = {}  # Map index -> control widget
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
            text_color="white"
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

        # --- Argument row with context-aware controls ---
        if self.args:
            self.args_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.args_frame.pack(fill="x", padx=5, pady=(0, 5))

            # Get parameter names from function signature if available
            param_names = self._get_parameter_names()

            for i, val in enumerate(self.args):
                container = ctk.CTkFrame(self.args_frame, fg_color="transparent")
                container.pack(side="left", padx=(0, 8), pady=2)

                # Create parameter label with descriptive name
                param_label = param_names[i] if i < len(param_names) else f"{i}"
                arg_label = ctk.CTkLabel(container, text=f"{param_label}:", width=80, text_color="white")
                arg_label.pack(side="left")

                # Create appropriate control based on function and parameter
                control = self._create_control_for_param(container, i, val, param_label)
                self.control_widgets[i] = control

        self.set_selected(False)

    def _get_parameter_names(self):
        """Get parameter names from function signature"""
        if not self.move_registry or self.function_name not in self.move_registry.move_dict:
            return []
        
        try:
            func = self.move_registry.move_dict[self.function_name]
            sig = signature(func)
            params = list(sig.parameters.keys())
            # If an unbound function includes 'self' as first parameter, drop it
            if params and params[0] == 'self':
                params = params[1:]
            return params
        except Exception:
            return []

    def _create_control_for_param(self, container, param_index, value, param_name):
        """Create appropriate UI control based on parameter type and function"""
        
        # Special case: move_to_location destination parameter (index 0)
        if self.function_name == "move_to_location" and param_index == 0:
            location_names = self._get_location_names()
            dropdown = ctk.CTkOptionMenu(
                container, 
                width=150,
                values=location_names,
                command=lambda selected: self._update_arg_from_widget(param_index, selected)
            )
            if str(value) in location_names:
                dropdown.set(str(value))
            else:
                dropdown.set(location_names[0] if location_names else "")
            dropdown.pack(side="left")
            hint = self._get_param_hint(param_name, param_index)
            if hint:
                hint_label = ctk.CTkLabel(container, text=hint, text_color="#AAAAAA")
                hint_label.pack(side="left", padx=(4, 0))
            return dropdown
        
        # Special case: move_toolhead relative parameter (index 3)
        elif self.function_name == "move_toolhead" and param_index == 3:
            checkbox = ctk.CTkCheckBox(
                container,
                text="",
                width=20,
                command=lambda: self._update_checkbox_arg(param_index, checkbox)
            )
            checkbox.pack(side="left")
            # Set initial state
            try:
                if int(value) >= 1:
                    checkbox.select()
            except ValueError:
                pass
            hint = self._get_param_hint(param_name, param_index)
            if hint:
                hint_label = ctk.CTkLabel(container, text=hint, text_color="#AAAAAA")
                hint_label.pack(side="left", padx=(4, 0))
            return checkbox
        
        # Special case: measure_spectrum measurement_type parameter (index 0)
        elif self.function_name == "measure_spectrum" and param_index == 0:
            measurement_types = ["Background", "Reference", "Sample"]
            dropdown = ctk.CTkOptionMenu(
                container,
                width=120,
                values=measurement_types,
                command=lambda selected: self._update_arg_from_widget(param_index, selected)
            )
            if str(value) in measurement_types:
                dropdown.set(str(value))
            else:
                dropdown.set(measurement_types[0] if measurement_types else "")
            dropdown.pack(side="left")
            hint = self._get_param_hint(param_name, param_index)
            if hint:
                hint_label = ctk.CTkLabel(container, text=hint, text_color="#AAAAAA")
                hint_label.pack(side="left", padx=(4, 0))
            return dropdown
        
        # Default: text entry with smart type conversion
        else:
            entry = ctk.CTkEntry(container, width=80, placeholder_text=str(value))
            entry.insert(0, str(value))
            entry.pack(side="left")
            entry.bind("<FocusOut>", lambda e: self._update_arg_from_widget(param_index, entry.get()))
            hint = self._get_param_hint(param_name, param_index)
            if hint:
                hint_label = ctk.CTkLabel(container, text=hint, text_color="#AAAAAA")
                hint_label.pack(side="left", padx=(4, 0))
            return entry

    def commit_args_from_widgets(self):
        """Force-read current widget values and update `self.args` accordingly."""
        for idx, widget in list(self.control_widgets.items()):
            try:
                # OptionMenu/Entry expose `.get()`; CheckBox handled via helper
                if hasattr(widget, 'get') and callable(widget.get):
                    # CTkCheckBox also has get() but we reuse the checkbox handler
                    if type(widget).__name__ == 'CTkCheckBox':
                        self._update_checkbox_arg(idx, widget)
                    else:
                        val = widget.get()
                        self._update_arg_from_widget(idx, val)
                else:
                    # Fallback: leave existing value
                    pass
            except Exception:
                import logging
                logging.getLogger('Main Logger').exception('Failed to commit widget value')
        return self.args

    def _get_param_hint(self, param_name, param_index):
        """Return a short hint string for the parameter if available."""
        try:
            if not self.move_registry or self.function_name not in self.move_registry.move_dict:
                return ""
            func = self.move_registry.move_dict[self.function_name]
            sig = signature(func)
            params = list(sig.parameters.values())
            if params and params[0].name == 'self':
                params = params[1:]
            if param_index < len(params):
                p = params[param_index]
                if p.default is not p.empty:
                    return f"default: {p.default}"
            # Heuristics for common names
            name = (param_name or "").lower()
            if name in ('x', 'y', 'z'):
                return "units: mm"
            if name == 'relative':
                return "0 or 1 (absolute=0, relative=1)"
            if 'time' in name or 'seconds' in name:
                return "seconds"
            return ""
        except Exception:
            return ""

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
            return ["Error loading locations"]

    def _update_checkbox_arg(self, index, checkbox):
        """Update argument from checkbox state"""
        self.args[index] = 1 if checkbox.get() else 0

    def _update_arg_from_widget(self, index, value):
        """Update argument from a widget value, with smart type conversion.

        This writes directly into `self.args` (which references the parent
        step's args list) so the ProcedureDrafterFrame will see the change.
        """
        # If the currently stored value has a numeric type, try to cast
        try:
            current = None
            if index < len(self.args):
                current = self.args[index]

            # If the incoming value is already the same type, just assign
            if isinstance(current, int):
                try:
                    self.args[index] = int(value)
                    return
                except Exception:
                    pass
            if isinstance(current, float):
                try:
                    self.args[index] = float(value)
                    return
                except Exception:
                    pass

            # Otherwise attempt best-effort numeric conversion
            try:
                if isinstance(value, str) and value.isdigit():
                    self.args[index] = int(value)
                    return
                # try float
                self.args[index] = float(value)
                return
            except Exception:
                # fallback to string
                pass

            # final fallback: store as-is (string or other)
            self.args[index] = value
        except Exception:
            # avoid crashing UI; log minimally to console
            import logging
            logging.getLogger("Main Logger").exception("Failed to update argument from widget")

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