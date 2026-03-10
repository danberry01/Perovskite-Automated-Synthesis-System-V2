import customtkinter as ctk
from PIL import Image
from ..components.theme import *
from ..components.helper_functions import is_overlapping

class TabViewFrame(ctk.CTkFrame):
    """Frame for Displaying different tab options"""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            width = 70,
            height = 800,
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR
        )
        
        self.rowconfigure(1, weight = 1)
        
        self.unselected_file_image = self.path_to_ctk_image("gui/icons/unselected_file.png")
        self.selected_file_image = self.path_to_ctk_image("gui/icons/selected_file.png")

        self.file_button = ctk.CTkButton(
            master = self,
            width = 60, 
            height = 60, 
            corner_radius = 0,
            fg_color = PRIMARY_BUTTON_COLOR,
            hover_color = HOVER_BUTTON_COLOR,
            text = "1",
            font = ("Roboto", 10)
        )
        self.file_button.grid(row = 0, column = 0, padx = 5, pady = 5, sticky = "new")

        self.bottom_button = ctk.CTkButton(
            master = self,
            width = 60, 
            height = 60, 
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR,
            hover_color = FOREGROUND_COLOR,
            image = self.unselected_file_image,
            text = ""
        )
        self.bottom_button.grid(row = 2, column = 0, padx = 5, pady = 5, sticky = "sew")
        self.frame_image_bindings(self.bottom_button, self.unselected_file_image, self.selected_file_image)

        self.master.bind("<Configure>",lambda event: self.hide_overlapping_frames(disp_frame = self.file_button, hide_frame = self.bottom_button))

    def hide_overlapping_frames(self, disp_frame = None, hide_frame = None, event=None):

        self.update_idletasks()

        required_height = (
            disp_frame.winfo_reqheight() +
            hide_frame.winfo_reqheight() +
            20
        )

        if self.winfo_height() < required_height:
            hide_frame.grid_remove()
        else:
            if not hide_frame.winfo_ismapped():
                hide_frame.grid()
    
    def path_to_ctk_image(self, image_path):
        if image_path is None:
            raise ValueError("image_path must be provided")

        return ctk.CTkImage(
            light_image=Image.open(image_path),
            dark_image=Image.open(image_path),
            size=(40, 40)
        )
    
    def frame_image_bindings(self, widget, image_normal, image_hover):
        widget.bind("<Enter>", lambda e: widget.configure(image=image_hover))
        widget.bind("<Leave>", lambda e: widget.configure(image=image_normal))
