import customtkinter as ctk
from PIL import Image
import sys
import os
import threading
import logging

from ...components.constants import *


# get current directory so we can import from outside guiFrames folder
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(path)
from objects.hotplate import Hotplate
from drivers.controlboard_driver import ControlBoard
from drivers.spincoater_driver import SpinCoater
from drivers.camera_driver import Camera
from drivers.spectrometer_driver import Spectrometer

class ConnectionFrame(ctk.CTkFrame):
    def __init__(self, master, dispatcher):  # Add spectrometer parameter
        super().__init__(master=master,fg_color = FOREGROUND_COLOR,height=400,corner_radius=0 )

        self.dispatcher = dispatcher
        self.control_board = dispatcher.control_board
        self.spin_coater = dispatcher.spin_coater
        self.hotplate = dispatcher.hotplate
        self.camera = dispatcher.camera
        self.spectrometer = dispatcher.spectrometer
        self.command_destination = "Control Board"
        
        # Register callback for camera connection state changes
        self.dispatcher.register_camera_connection_callback(self._on_camera_connection_changed)
        
        # Title
        self.title_label = ctk.CTkLabel(
            master=self,
            text="Connection Manager",
            justify="left",anchor="w",
            font=("Arial", 20, "bold"))
        self.title_label.grid(
            row=0, column=0, columnspan=5, 
            padx=5, pady=5, sticky="nw")
        
        # Control Board
        self.control_board_connection = NameLater(
            self, "controlboard.png",self._connect_control_board)
        self.control_board_connection.grid(
            row=1, column=0,
            padx=5,pady=5,
            sticky="nw")
        
        # Spin Coater
        self.spin_coater_connection = NameLater(
            self, "spin_coater.png",self._connect_spin_coater)
        self.spin_coater_connection.grid(
            row=1, column=1,
            padx=5,pady=5,sticky="nw")
        
        # Hotplate
        self.hotplate_connection = NameLater(
            self, "hotplate.png",self._connect_hotplate)
        self.hotplate_connection.grid(
            row=1, column=2,
            padx=5,pady=5,sticky="nw")
        
        # Spectrometer
        self.spectrometer_connection = NameLater(
            self, "spectrometer.png",self._connect_spectrometer)
        self.spectrometer_connection.grid(
            row=1, column=3,
            padx=5,pady=5,sticky="nw")
        
        # Camera
        self.camera_connection = NameLater(
            self, "camera.png",self._connect_camera)
        self.camera_connection.grid(
            row=1, column=4,
            padx=5,pady=5,sticky="nw")

        # command entry
        self.command_destination_label = ctk.CTkLabel(
            master=self,
            text=f"Destination:",
            width=80,
            anchor="w"
        )
        self.command_destination_label.grid(row=4, column=0, padx=5, pady=5, sticky="nw")
        
        self.command_entry_destination = ctk.CTkOptionMenu(
            master=self,
            values=["Control Board", "Spincoater", "Hotplate", "Spectrometer"],
            width=120,
            fg_color = PLAIN_TEXT_COLOR,
            button_color = PLAIN_TEXT_COLOR,
            button_hover_color = FOREGROUND_COLOR_TWO,
            corner_radius = 0,
            command=self._set_command_destination
        )
        self.command_entry_destination.grid(row=5, column=0, padx=5, pady=5, sticky="nw")

        self.command_entry = ctk.CTkEntry(
            master=self,
            width=300,
            height=50
        )
        self.command_entry.grid(row=4, column=1, rowspan=2, columnspan=3, padx=5, pady=5, sticky="nw")
        self.command_entry.bind("<Return>", self._send_entry)
        
        # Send Button
        self.send_entry_button = ctk.CTkButton(
            master=self,
            text="Send",
            width=50,
            height=50,
            fg_color = PLAIN_TEXT_COLOR,
            hover_color = FOREGROUND_COLOR_TWO,
            corner_radius = 0,
            command=self._send_entry)
        self.send_entry_button.grid(
            row=4, column=4, rowspan=2,
            padx=5, pady=5, sticky="nw")
        
        self._update()

        # Best-effort auto-connect on creation (non-blocking)
        try:
            threading.Thread(target=self._auto_connect_on_startup, daemon=True).start()
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to start auto-connect thread for ConnectionFrame")

    def _auto_connect_on_startup(self):
        """Attempt to connect to available devices on startup in background.

        This is best-effort and will not raise; it updates individual
        connection widgets via the existing set_connection_status calls.
        """
        logger = logging.getLogger("Main Logger")
        try:
            # Try control board first (most critical)
            try:
                self.control_board.connect()
            except Exception as e:
                logger.debug(f"Control board auto-connect attempt raised: {e}")
            self.control_board_connection.set_connection_status(self.control_board.is_connected())

            # Try the spin coater
            try:
                self.spin_coater.connect()
            except Exception as e:
                logger.debug(f"Spin coater auto-connect attempt raised: {e}")
            self.spin_coater_connection.set_connection_status(self.spin_coater.is_connected())

            # Try hotplate
            try:
                self.hotplate.connect()
            except Exception as e:
                logger.debug(f"Hotplate auto-connect attempt raised: {e}")
            self.hotplate_connection.set_connection_status(self.hotplate.is_connected())

            # Try spectrometer
            try:
                self.spectrometer.connect()
            except Exception as e:
                logger.debug(f"Spectrometer auto-connect attempt raised: {e}")
            self.spectrometer_connection.set_connection_status(self.spectrometer.is_connected())

            # Try camera via dispatcher helper
            try:
                self.dispatcher.connect_camera()
            except Exception as e:
                logger.debug(f"Camera auto-connect attempt raised: {e}")
            self.camera_connection.set_connection_status(self.camera.is_connected())

        except Exception:
            logger.exception("Error during auto-connect startup sequence")

    def _update(self):
        self.control_board_connection.set_connection_status(self.control_board.is_connected())
        self.spin_coater_connection.set_connection_status(self.spin_coater.is_connected())
        self.hotplate_connection.set_connection_status(self.hotplate.is_connected())
        self.spectrometer_connection.set_connection_status(self.spectrometer.is_connected())
        self.camera_connection.set_connection_status(self.camera.is_connected())

        self.after(1000, self._update)

    def _connect_control_board(self):
        # Run connection in background to avoid UI freeze and handle errors
        def _task():
            logger = logging.getLogger("Main Logger")
            try:
                self.control_board.connect()
                ok = self.control_board.is_connected()
                self.control_board_connection.set_connection_status(ok)
                if not ok:
                    logger.warning("Control board auto-connect reported not connected")
            except Exception as e:
                logger.exception(f"Error connecting control board: {e}")
                try:
                    self.control_board.disconnect()
                except Exception:
                    pass
                self.control_board_connection.set_connection_status(False)

        threading.Thread(target=_task, daemon=True).start()
    
    def _connect_spin_coater(self):
        def _task():
            logger = logging.getLogger("Main Logger")
            try:
                self.spin_coater.connect()
                self.spin_coater_connection.set_connection_status(self.spin_coater.is_connected())
            except Exception as e:
                logger.exception(f"Error connecting spin coater: {e}")
                try:
                    self.spin_coater.disconnect()
                except Exception:
                    pass
                self.spin_coater_connection.set_connection_status(False)

        threading.Thread(target=_task, daemon=True).start()
        
    def _connect_hotplate(self):
        def _task():
            logger = logging.getLogger("Main Logger")
            try:
                self.hotplate.connect()
                self.hotplate_connection.set_connection_status(self.hotplate.is_connected())
            except Exception as e:
                logger.exception(f"Error connecting hotplate: {e}")
                try:
                    self.hotplate.disconnect()
                except Exception:
                    pass
                self.hotplate_connection.set_connection_status(False)

        threading.Thread(target=_task, daemon=True).start()
        
    def _connect_spectrometer(self):
        def _task():
            logger = logging.getLogger("Main Logger")
            try:
                self.spectrometer.connect()
                self.spectrometer_connection.set_connection_status(self.spectrometer.is_connected())
            except Exception as e:
                logger.exception(f"Error connecting spectrometer: {e}")
                try:
                    self.spectrometer.disconnect()
                except Exception:
                    pass
                self.spectrometer_connection.set_connection_status(False)

        threading.Thread(target=_task, daemon=True).start()
        
    def _connect_camera(self):
        # Dispatcher provides a wrapper and callback notification - run in background
        def _task():
            logger = logging.getLogger("Main Logger")
            try:
                self.dispatcher.connect_camera()
            except Exception as e:
                logger.exception(f"Error connecting camera: {e}")
                try:
                    self.camera.disconnect()
                except Exception:
                    pass

        threading.Thread(target=_task, daemon=True).start()
        
    def _on_camera_connection_changed(self, is_connected: bool):
        """Callback when camera connection state changes (called from either button)"""
        self.camera_connection.set_connection_status(is_connected)
        
    def _set_command_destination(self, value: str):
        self.command_destination = value
        self.command_destination_label.configure(text=f"Destination:")

    def _send_entry(self, event=None):
        value = self.command_entry.get()
        
        if value == "":
            return
        logger = logging.getLogger("Main Logger")
        try:
            if self.command_destination == "Control Board":
                try:
                    self.control_board.send_message(value)
                except Exception as e:
                    logger.exception(f"Failed to send to control board: {e}")
                    try:
                        self.control_board.disconnect()
                    except Exception:
                        pass
                    self.control_board_connection.set_connection_status(False)
            elif self.command_destination == "Spincoater":
                try:
                    self.spin_coater.send_message(value)
                except Exception as e:
                    logger.exception(f"Failed to send to spin coater: {e}")
                    try:
                        self.spin_coater.disconnect()
                    except Exception:
                        pass
                    self.spin_coater_connection.set_connection_status(False)
            elif self.command_destination == "Spectrometer":
                try:
                    self.spectrometer.send_message(value)
                except Exception as e:
                    logger.exception(f"Failed to send to spectrometer: {e}")
                    try:
                        self.spectrometer.disconnect()
                    except Exception:
                        pass
                    self.spectrometer_connection.set_connection_status(False)
            elif self.command_destination == "Hotplate":
                try:
                    self.hotplate.send_message(value)
                except Exception as e:
                    logger.exception(f"Failed to send to hotplate: {e}")
                    try:
                        self.hotplate.disconnect()
                    except Exception:
                        pass
                    self.hotplate_connection.set_connection_status(False)
        except Exception:
            logger.exception("Unexpected error in _send_entry")
    
    def destroy(self):
        """Clean up callbacks when frame is destroyed"""
        self.dispatcher.unregister_camera_connection_callback(self._on_camera_connection_changed)
        super().destroy()
            
class NameLater(ctk.CTkFrame):
    def __init__(self, master, image_path, command, default_port: int = 0):
        super().__init__(master=master)
        # Image
        image = ctk.CTkImage(
            light_image=Image.open(f"guiImages/{image_path}"),
            size=(100, 100))
        self.image_label = ctk.CTkLabel(
            master=self, text="", image=image,
            width=100, height=100)
        self.image_label.grid(
            row=0, column=0, columnspan=2,
            padx=5, pady=5, 
            sticky="nw")
        # Status Label
        self.status_label = ctk.CTkLabel(
            master=self, text="Status: Disconected",
            width=100, height=20,
            font=("Arial", 10))
        self.status_label.grid(
            row=1, column=0, columnspan=2,
            padx=5, pady=5, 
            sticky="nw")
        # Connect button
        self.connect_button = ctk.CTkButton(
            master=self, 
            text="Connect",
            fg_color = PLAIN_TEXT_COLOR,
            hover_color = FOREGROUND_COLOR_TWO,
            corner_radius = 0,
            width=100, 
            height=20,
            command=command)
        self.connect_button.grid(
            row=2, column=0, 
            padx=5, pady=5, 
            sticky="nw")
      

    def set_connection_status(self, connected: bool):
        if connected:
            self.status_label.configure(text="Status: Connected")
            self.connect_button.configure(state="disabled")
        else:
            self.status_label.configure(text="Status: Disconected")
            # check prevents it from glitching out and updating constantly
            if self.connect_button.cget("state") != "normal":
                self.connect_button.configure(state="normal")
    
if __name__ == "__main__":
    app = ctk.CTk()
    ctk.set_appearance_mode("dark")
    app.geometry("1200x1000")
    control_board_connection = NameLater(
        app, "controlboard.png",print("hi"))
    control_board_connection.grid(
        row=1, column=0,
        padx=5,pady=5,
        sticky="nw")
    app.mainloop()