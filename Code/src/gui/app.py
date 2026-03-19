import customtkinter as ctk
import os
from .components.constants import *
from .frames import *

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class App(ctk.CTk):
    """Application for Perovskite Automated Synthesis System"""
    def __init__(self):
        super().__init__(fg_color = FOREGROUND_COLOR)

        # # If run from main, takes the file path 
        # self.current_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # self.cat_icon_path = os.path.join(self.current_directory, "gui", "icons", "cat.ico")

        # Define the window
        self.title("Perovskite Automated Synthesis System V2")
        # self.iconbitmap(self.cat_icon_path)
        self.geometry("1000x800")

        self.grid_rowconfigure(0, weight = 1)
        self.grid_rowconfigure(1, weight = 0)

        self.grid_columnconfigure(0, weight = 0)
        self.grid_columnconfigure(1, weight = 1)

        
        # Define frames
        frame_configs = [
            # {"class": CameraFrame,              "frame": "camera_frame",            "row": 0, "col": 0, "padx": 10, "pady": 10},
            # {"class": ConnectionFrame,          "frame": "connection_frame",        "row": 0, "col": 1, "padx": 5,  "pady": 5},
            # {"class": ConsoleFrame,             "frame": "console_frame",           "row": 1, "col": 0, "padx": 20, "pady": 2},
            {"class": InfoFrame,                "frame": "info_frame",              "row": 1, "col": 1, "padx": 0,  "pady": 0},
            # {"class": LocationsFrame,           "frame": "locations_frame",         "row": 1, "col": 1, "padx": 5,  "pady": 5},
            # {"class": ProcedureBuilderFrame,    "frame": "procedure_builder_frame", "row": 1, "col": 1, "padx": 5,  "pady": 5},
            # {"class": ProcedureLogFrame,        "frame": "procedure_log_frame",     "row": 1, "col": 1, "padx": 5,  "pady": 5},
            # {"class": SpectrometerFrame,        "frame": "spectrometer_frame",      "row": 1, "col": 1, "padx": 5,  "pady": 5},
            {"class": TabManagerFrame,          "frame": "tab_manager_frame",           "row": 0, "col": 0, "rowspan": 2,"padx": 0,  "pady": 0},
            {"class": TabViewFrame,             "frame": "tab_view_frame",              "row": 0, "col": 1, "padx": 0,  "pady": 0}

        ]

        self.frames = {}

        for config in frame_configs:
            # Pull current class and frame
            current_class = config["class"]
            current_frame_name = config["frame"] 
            
            # Define frame
            current_frame_instance = current_class(master = self, controller=self)

            self.frames[current_frame_name] = current_frame_instance

            setattr(self, current_frame_name, current_frame_instance)

            # frame.grid(row,col,padx,pady,sticky)
            current_frame_instance.grid(
                row    = config.get("row", 0), # default row 0
                column = config.get("col", 0), # Default col 0
                rowspan    = config.get("rowspan", None), # default row 0
                columnspan = config.get("colspan", None), # Default col 0
                padx   = config.get("padx", 5), # Default pad 5
                pady   = config.get("pady", 5), # Default pad 5
                sticky = config.get("sticky", "nsew") # Default to full stretch
            )

    def switch_tab(self, tab_name):
        self.tab_manager_frame.current_tab = tab_name
        self.tab_view_frame.goto_tab(tab_name)     


        


if __name__ == "__main__":
    app = App()
    app.mainloop()
        



