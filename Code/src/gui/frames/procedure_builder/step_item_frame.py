import customtkinter as ctk


class StepItem(ctk.CTkFrame):
    def __init__(self, master, text, index, args, move_callback, select_callback):
        super().__init__(master, corner_radius=5)

        self.index = index
        self.move_callback = move_callback
        self.select_callback = select_callback

        self.args = args
        self.entries = []

        # --- STEP LABEL ---
        self.label = ctk.CTkLabel(self, text=text, anchor="w")
        self.label.pack(fill="x", padx=5, pady=2)

        self.label.bind("<Button-1>", lambda e: self.select_callback(self.index))

        # --- ARGUMENT INPUTS ---
        self.args_frame = ctk.CTkFrame(self)
        self.args_frame.pack(fill="x", padx=5, pady=2)

        for i, val in enumerate(self.args):
            container = ctk.CTkFrame(self.args_frame, fg_color="transparent")
            container.pack(side="left", padx=2)

            # OPTIONAL: argument label (index-based for now, safe)
            arg_label = ctk.CTkLabel(container, text=f"{i}:", width=10)
            arg_label.pack(side="left")

            entry = ctk.CTkEntry(container, width=60)
            entry.insert(0, str(val))
            entry.pack(side="left")

            # 🔥 safer binding (avoids late-binding issues)
            entry.bind("<FocusOut>", self._make_update_callback(i))

            self.entries.append(entry)

    # -------------------------
    # SAFE CALLBACK GENERATOR
    # -------------------------
    def _make_update_callback(self, index):
        return lambda event: self.update_arg(index)

    # -------------------------
    # ARG UPDATE LOGIC
    # -------------------------
    def update_arg(self, index):
        try:
            raw_value = self.entries[index].get().strip()

            # Try int
            try:
                value = int(raw_value)
            except ValueError:
                # Try float
                try:
                    value = float(raw_value)
                except ValueError:
                    # Keep as string
                    value = raw_value

            self.args[index] = value

        except Exception:
            pass

    # -------------------------
    # SELECTION VISUAL
    # -------------------------
    def set_selected(self, selected):
        if selected:
            self.configure(fg_color="#444444")
        else:
            self.configure(fg_color="transparent")