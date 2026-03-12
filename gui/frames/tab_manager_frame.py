import customtkinter as ctk
from PIL import Image

from ..components.constants import *
from ..components.helper_functions import is_overlapping
from .tab_view_frame import TabViewFrame

class TabManagerFrame(ctk.CTkFrame):
    """Frame for Displaying different tab options"""
    def __init__(self, master, controller, **kwargs):
        super().__init__(
            master,
            width = 70,
            height = 800,
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR
        )

        self.controller = controller   

        self.current_tab = "file_manager"

        self.rowconfigure(3, weight = 1)
        self.columnconfigure(0, weight = 0)
        # Define all Tab Icons
        self.unselected_file_image = self.path_to_ctk_image("gui/icons/unselected_file.png")
        self.selected_file_image = self.path_to_ctk_image("gui/icons/selected_file.png")

        self.unselected_builder_image = self.path_to_ctk_image("gui/icons/unselected_builder.png")
        self.selected_builder_image = self.path_to_ctk_image("gui/icons/selected_builder.png")

        self.unselected_procedure_image = self.path_to_ctk_image("gui/icons/unselected_procedure.png")
        self.selected_procedure_image = self.path_to_ctk_image("gui/icons/selected_procedure.png")

        self.unselected_settings_image = self.path_to_ctk_image("gui/icons/unselected_settings.png")
        self.selected_settings_image = self.path_to_ctk_image("gui/icons/selected_settings.png")

        # File tab button
        self.file_tab_button = ctk.CTkButton(
            master = self,
            width = 75, 
            height = 75, 
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR,
            hover_color = FOREGROUND_COLOR,
            image = self.unselected_file_image,
            text = "",
            command = lambda: self.controller.switch_tab("file_manager") 
        )

        self.file_tab_button.grid(row = 0, column = 0, padx = 5, pady = 5, sticky = "new") # Establishes grid placement
        self.frame_image_bindings(self.file_tab_button, self.unselected_file_image, self.selected_file_image) #Binds the hover actions to file icon replacement


        # Builder tab button
        self.builder_tab_button = ctk.CTkButton(
            master = self,
            width = 75, 
            height = 75, 
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR,
            hover_color = FOREGROUND_COLOR,
            image = self.unselected_builder_image,
            text = "",
            command = lambda: self.controller.switch_tab("procedure_builder") 
        )
        self.builder_tab_button.grid(row = 1, column = 0, padx = 5, pady = 5, sticky = "new") # Establishes grid placement
        self.frame_image_bindings(self.builder_tab_button, self.unselected_builder_image, self.selected_builder_image) #Binds the hover actions to file icon replacement


        # Builder tab button
        self.procedure_tab_button = ctk.CTkButton(
            master = self,
            width = 75, 
            height = 75, 
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR,
            hover_color = FOREGROUND_COLOR,
            image = self.unselected_procedure_image,
            text = "",
            command = lambda: self.controller.switch_tab("procedure_viewer") 
        )
        self.procedure_tab_button.grid(row = 2, column = 0, padx = 5, pady = 5, sticky = "new") # Establishes grid placement
        self.frame_image_bindings(self.procedure_tab_button, self.unselected_procedure_image, self.selected_procedure_image) #Binds the hover actions to file icon replacement


        self.settings_tab_button = ctk.CTkButton(
            master = self,
            width = 75, 
            height = 75, 
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR,
            hover_color = FOREGROUND_COLOR,
            image = self.unselected_settings_image,
            text = "",
            command = lambda: self.controller.switch_tab("settings") 
        )
        self.settings_tab_button.grid(row = 4, column = 0, padx = 5, pady = 5, sticky = "sew")
        self.frame_image_bindings(self.settings_tab_button, self.unselected_settings_image, self.selected_settings_image) #Binds the hover actions to file icon replacement

        # Binds buttons on bottom to dissapear when tab selection buttons collide
        self.master.bind("<Configure>",lambda e: self.hide_overlapping_frames(disp_frame = self.procedure_tab_button, hide_frame = self.settings_tab_button))

    def hide_overlapping_frames(self, disp_frame = None, hide_frame = None, event=None):

        self.update_idletasks()

        required_height = (
            disp_frame.winfo_reqheight() +
            hide_frame.winfo_reqheight() +
            210 # This number determines how far from the top the frame "collision" is detected. Higher number = sooner collision
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
            size=(55, 55)
        )
    
    def frame_image_bindings(self, widget, image_normal, image_hover):
        widget.bind("<Enter>", lambda e: widget.configure(image=image_hover))
        widget.bind("<Leave>", lambda e: widget.configure(image=image_normal))

    def set_next_tab(self, tab):
        if self.current_tab == tab:
            print("Tab Already Set!")
            return
        if not(tab in TABS):
            raise TypeError("tab does not exist")

        self.current_tab = tab
        print("next tab set: "+ self.current_tab )

