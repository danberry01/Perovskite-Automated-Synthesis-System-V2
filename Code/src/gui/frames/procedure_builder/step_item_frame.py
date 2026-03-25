import customtkinter as ctk
from ...components.constants import *

class StepItem(ctk.CTkFrame):
    def __init__(self, master, text, index, move_callback, select_callback, **kwargs):
        super().__init__(master, fg_color=FOREGROUND_COLOR, **kwargs)

        self.index = index
        self.move_callback = move_callback
        self.select_callback = select_callback

        self.default_bg = BACKGROUND_COLOR
        self.selected_bg = FOREGROUND_COLOR
        self.configure(fg_color=self.default_bg)  # default color


        self.grid_columnconfigure(1, weight=1)

        # Up button
        self.up_button = ctk.CTkButton(
            self,
            text="↑",
            text_color = BACKGROUND_COLOR, 
            fg_color = PLAIN_TEXT_COLOR,
            width=30,
            command=self.move_up
        )
        self.up_button.grid(row=0, column=0, padx=5, pady=5)

        # Label
        self.label = ctk.CTkLabel(self, text=text, font = ("roboto", 20), compound = "center")
        self.label.grid(row=0, column=1, sticky="ew", padx=5)

        self.bind("<Button-1>", self.on_click)
        self.label.bind("<Button-1>", self.on_click)

        # Down button
        self.down_button = ctk.CTkButton(
            self,
            text="↓",
            text_color = BACKGROUND_COLOR, 
            fg_color = PLAIN_TEXT_COLOR,
            width=30,
            command=self.move_down
        )
        self.down_button.grid(row=0, column=2, padx=5, pady=5)

    def move_up(self):
        self.move_callback(self.index, self.index - 1)

    def move_down(self):
        self.move_callback(self.index, self.index + 1)

    def set_text(self, text):
        self.label.configure(text=text)

    def on_click(self, event):
        self.select_callback(self.index)

    def set_selected(self, selected: bool):
        """Change background color based on selection"""
        if selected:
            self.configure(fg_color=self.selected_bg)
        else:
            self.configure(fg_color=self.default_bg)

