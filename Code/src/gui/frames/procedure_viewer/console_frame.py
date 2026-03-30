import customtkinter as ctk
import logging
from queue import Queue

from ...components.constants import *


class ConsoleFrame(ctk.CTkFrame):
    """ GUI Frame to display the console log """
    
    def __init__(self, master):
        super().__init__(master=master,fg_color = FOREGROUND_COLOR, border_width=2, corner_radius=0 )
        
        # Update loop tracking  
        self._update_after_id = None
        self._is_paused = False
        
        self.logger = logging.getLogger("Main Logger")
        self.log_queue = Queue()
        self.console_handler = ConsoleLogHandler(self)
        self.console_handler.setFormatter(logging.Formatter('%(levelname)s\t%(asctime)s: %(message)s'))
        self.logger.addHandler(self.console_handler)

        self.columnconfigure(0, weight = 1)
        self.columnconfigure(1, weight = 1)
        self.rowconfigure(0, weight = 0)
        self.rowconfigure(1, weight = 1)

        # title label
        self.title_label = ctk.CTkLabel(
            master=self,
            text="Console",
            justify="left",
            anchor="w",
            font=("Arial", 20, "bold"))
        self.title_label.grid(
            row=0, column=0, 
            padx=20, pady=10, 
            sticky="nw")
        
        # logging level selector
        self.log_level = ctk.CTkOptionMenu(
            master=self,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            width=100,
            fg_color = PLAIN_TEXT_COLOR,
            button_color = PLAIN_TEXT_COLOR,
            button_hover_color = FOREGROUND_COLOR_TWO,
            corner_radius = 0,
            command=self.update_logging_level)
        self.log_level.grid(row=0, column=1, padx=20, pady=10, sticky="ne")
        
        # console
        self.console = ctk.CTkTextbox(
            master=self,
            corner_radius=0,
            fg_color = PLAIN_TEXT_COLOR,
            state="disabled")
        self.console.grid(row=1, column=0, columnspan = 2, padx=20, pady=10, sticky="nsew")
        
        self.console.tag_config("DEBUG", foreground="#8df564")
        self.console.tag_config("WARNING", foreground="#e4f089")
        self.console.tag_config("ERROR", foreground="red")
        
        self._update()
    
    def destroy(self):
        """ Override the destroy method to perform cleanup tasks """
        self.logger.removeHandler(self.console_handler)
        super().destroy()
        
    def _update(self):
        # Don't process messages if paused, but keep scheduling the loop
        if not self._is_paused:
            while not self.log_queue.empty():
                msg = self.log_queue.get()
                self.write_to_console(msg)
                self.log_queue.task_done()
                self.console.see("end")
        
        self._update_after_id = self.after(50, self._update)
    
    def pause_update(self):
        """Pause console updates to reduce CPU usage"""
        self._is_paused = True
    
    def resume_update(self):
        """Resume console updates"""
        self._is_paused = False

    def write_to_console(self, text: str):
        """ Write a message to the console

        ### Args:
            text (str): message to be logged in console
        """
        
        prefix = text.split(" ")[0]
        
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n", prefix)
        self.console.configure(state="disabled")


    def update_logging_level(self, level: str):
        """ Update the logging level

        ### Args:
            level (str): logging level to set
        """
        self.logger.setLevel(level)
        self.logger.debug(f"Logging level set to {level}")

    
class ConsoleLogHandler(logging.StreamHandler):
    """ Custom log handler to write log messages to the console frame """
    def __init__(self, console):
        super().__init__()
        self.console = console

    def emit(self, record):
        self.console.log_queue.put(self.format(record))
    