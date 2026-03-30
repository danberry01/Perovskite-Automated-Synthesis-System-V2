import customtkinter as ctk


class StepItem(ctk.CTkFrame):
    def __init__(self, master, text, index, args, move_callback, select_callback):
        super().__init__(master, corner_radius=5, fg_color="transparent")

        self.index = index
        self.move_callback = move_callback
        self.select_callback = select_callback

        self.args = list(args)
        self.entries = []

        self._selected = False

        # Main row keeps the original-looking step name visible
        self.top_row = ctk.CTkFrame(self, fg_color="transparent")
        self.top_row.pack(fill="x", padx=5, pady=(4, 2))

        self.left_button = ctk.CTkButton(
            self.top_row,
            text="↑",
            width=30,
            height=28,
            corner_radius=4,
            command=self.move_up
        )
        self.left_button.pack(side="left", padx=(0, 4))

        self.label = ctk.CTkLabel(
            self.top_row,
            text=text,
            anchor="w"
        )
        self.label.pack(side="left", fill="x", expand=True)
        self.label.bind("<Button-1>", lambda e: self.select_callback(self.index))
        self.top_row.bind("<Button-1>", lambda e: self.select_callback(self.index))

        self.right_button = ctk.CTkButton(
            self.top_row,
            text="↓",
            width=30,
            height=28,
            corner_radius=4,
            command=self.move_down
        )
        self.right_button.pack(side="right", padx=(4, 0))

        # Argument row stays below the name, so nothing disappears
        self.args_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.args_frame.pack(fill="x", padx=5, pady=(0, 5))

        self.arg_labels = []
        for i, val in enumerate(self.args):
            container = ctk.CTkFrame(self.args_frame, fg_color="transparent")
            container.pack(side="left", padx=(0, 8), pady=2)

            arg_label = ctk.CTkLabel(container, text=f"{i}:", width=16)
            arg_label.pack(side="left")

            entry = ctk.CTkEntry(container, width=72)
            entry.insert(0, str(val))
            entry.pack(side="left")

            entry.bind("<FocusOut>", self._make_update_callback(i))

            self.entries.append(entry)
            self.arg_labels.append(arg_label)

        self.set_selected(False)

    def _make_update_callback(self, index):
        return lambda event: self.update_arg(index)

    def update_arg(self, index):
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
        if selected:
            self.configure(fg_color="#444444")
            self.top_row.configure(fg_color="#444444")
            self.args_frame.configure(fg_color="#444444")
        else:
            self.configure(fg_color="transparent")
            self.top_row.configure(fg_color="transparent")
            self.args_frame.configure(fg_color="transparent")