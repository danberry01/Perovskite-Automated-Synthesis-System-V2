import customtkinter as ctk
import os
import logging
from time import sleep
from .components.constants import *
from .frames import *

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class App(ctk.CTk):
    """Application for Perovskite Automated Synthesis System"""
    def __init__(self, move_registry, dispatcher, procedure_handler):
        super().__init__(fg_color = FOREGROUND_COLOR)

        self.move_registry = move_registry
        self.dispatcher = dispatcher
        self.procedure_handler = procedure_handler

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

        self.tab_manager_frame = TabManagerFrame(
            master = self,
            controller = self
        )
        self.tab_manager_frame.grid(row = 0, column = 0, rowspan = 2, padx = 0, pady = 0, sticky = "nsew")
        
        self.tab_view_frame = TabViewFrame(
            master = self, 
            controller = self, 
            dispatcher = self.dispatcher, 
            move_registry = self.move_registry, 
            procedure_handler = self.procedure_handler
        )
        self.tab_view_frame.grid(row = 0, column = 1, padx = 0, pady = 0, sticky = "nsew")

        self.info_frame = InfoFrame(
            master = self,
            controller = self
        )
        self.info_frame.grid(row = 1, column = 1, padx = 0, pady = 0, sticky = "nsew")

        # Ensure application performs driver cleanup on window close
        try:
            self.protocol("WM_DELETE_WINDOW", self._on_closing)
        except Exception:
            # protocol may not be available in some environments; ignore if so
            pass

    def _on_closing(self):
        """Run cleanup in a background thread so the GUI can close immediately.

        Heavy or potentially blocking hardware operations (serial writes,
        disconnects) are executed in a daemon thread to avoid freezing the
        main thread when the user clicks the window close (X) button.
        """
        logger = logging.getLogger("Main Logger")
        logger.info("Application closing — scheduling cleanup")

        def _cleanup():
            logger.info("Background cleanup started")
            # Stop any running procedure and issue emergency stop
            try:
                if self.procedure_handler:
                    self.procedure_handler.kill()
            except Exception:
                logger.exception("Error while killing procedure handler during shutdown")

            # Ensure hardware is commanded to a safe state
            try:
                if self.move_registry:
                    self.move_registry.kill()
            except Exception:
                logger.exception("Error while invoking move_registry.kill() during shutdown")

            # Give hardware a short moment to process stop commands
            sleep(0.2)

            # Disconnect hardware drivers where possible
            try:
                drivers = [
                    'control_board', 'spin_coater', 'camera', 'spectrometer', 'hotplate', 'vial_carousel'
                ]
                for name in drivers:
                    try:
                        drv = getattr(self.dispatcher, name, None)
                        if drv is None:
                            continue
                        if hasattr(drv, 'disconnect') and callable(drv.disconnect):
                            try:
                                drv.disconnect()
                            except Exception:
                                logger.exception(f"Error disconnecting {name}")
                    except Exception:
                        logger.exception(f"Error during shutdown driver cleanup for {name}")
            except Exception:
                logger.exception("Error during driver cleanup")

            logger.info("Background cleanup finished")

        # Run cleanup in background and close GUI immediately
        try:
            import threading as _threading
            t = _threading.Thread(target=_cleanup, daemon=True)
            t.start()
        except Exception:
            logger.exception("Failed to start background cleanup thread")

        try:
            self.destroy()
        except Exception:
            pass

    def switch_tab(self, tab_name):
        self.tab_manager_frame.current_tab = tab_name
        self.tab_view_frame.goto_tab(tab_name)     


        


if __name__ == "__main__":
    app = App()
    app.mainloop()
        



