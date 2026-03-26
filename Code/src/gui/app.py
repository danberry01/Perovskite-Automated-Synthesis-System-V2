import customtkinter as ctk
import os
from .components.constants import *
from .frames import *

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class App(ctk.CTk):
    """Application for Perovskite Automated Synthesis System"""
    def __init__(self, move_registry, dispatcher):
        super().__init__(fg_color = FOREGROUND_COLOR)

        self.move_registry = move_registry
        self.dispatcher = dispatcher

        # # If run from main, takes the file path 
        # self.current_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # self.cat_icon_path = os.path.join(self.current_directory, "gui", "icons", "cat.ico")

        # Define the window
        self.title("Perovskite Automated Synthesis System V2")
        # self.iconbitmap(self.cat_icon_path)
        self.geometry("1600x800")

        self.grid_rowconfigure(0, weight = 1)
        self.grid_rowconfigure(1, weight = 0)

        self.grid_columnconfigure(0, weight = 0)
        self.grid_columnconfigure(1, weight = 1)

        self.tab_manager_frame = TabManagerFrame(master = self, controller = self)
        self.tab_manager_frame.grid(row = 0, column = 0, rowspan = 2, padx = 0, pady = 0, sticky = "nsew")
        
        self.tab_view_frame = TabViewFrame(master = self, controller = self, dispatcher = self.dispatcher, move_registry = self.move_registry)
        self.tab_view_frame.grid(row = 0, column = 1, padx = 0, pady = 0, sticky = "nsew")

        self.info_frame = InfoFrame(master = self, controller = self)
        self.info_frame.grid(row = 1, column = 1, padx = 0, pady = 0, sticky = "nsew")

    def switch_tab(self, tab_name):
        self.tab_manager_frame.current_tab = tab_name
        self.tab_view_frame.goto_tab(tab_name)     


        


if __name__ == "__main__":
    app = App()
    app.mainloop()
        



