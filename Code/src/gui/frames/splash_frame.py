import customtkinter as ctk
import threading
import logging


class SplashFrame(ctk.CTkFrame):
    """Startup splash that asks the user whether to home the gantry.

    This frame attempts a best-effort auto-connect to the control board
    in the background and displays a simple status. If the user selects
    Yes the UI switches to the procedure viewer and the gantry homing is
    started in a background thread. If No, the UI switches to the
    file manager (home) tab.
    """

    def __init__(self, master, dispatcher, move_registry, controller, **kwargs):
        super().__init__(master=master, fg_color="#222222", **kwargs)
        self.dispatcher = dispatcher
        self.move_registry = move_registry
        self.controller = controller
        self.logger = logging.getLogger("Main Logger")

        # Layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        title = ctk.CTkLabel(self, text="Welcome to Perovskite ASS V2", font=("Arial", 22, "bold"))
        title.pack(pady=(40, 8))

        prompt = ctk.CTkLabel(self, text="Home the gantry now?", font=("Arial", 16))
        prompt.pack(pady=(0, 10))

        self.status_label = ctk.CTkLabel(self, text="Attempting to auto-connect to hardware...", text_color="#CCCCCC")
        self.status_label.pack(pady=(0, 18))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        yes_btn = ctk.CTkButton(btn_frame, text="Yes", width=120, command=self._on_yes)
        yes_btn.grid(row=0, column=0, padx=8)
        no_btn = ctk.CTkButton(btn_frame, text="No", width=120, command=self._on_no)
        no_btn.grid(row=0, column=1, padx=8)

        # Start background auto-connect attempt
        threading.Thread(target=self._attempt_auto_connect, daemon=True).start()

    def _attempt_auto_connect(self):
        try:
            cb = getattr(self.dispatcher, 'control_board', None)
            if cb is None:
                self._set_status("No control board driver available")
                return

            if cb.is_connected():
                self._set_status("Control board connected")
                return

            self._set_status("Auto-connecting control board...")
            try:
                cb.connect()
            except Exception as e:
                self.logger.exception(f"Auto-connect attempt raised: {e}")

            if cb.is_connected():
                self._set_status("Control board connected")
            else:
                self._set_status("Control board not connected")
        except Exception as e:
            self.logger.exception(f"Auto-connect failed: {e}")
            self._set_status("Auto-connect failed")

    def _set_status(self, text: str):
        try:
            self.status_label.configure(text=text)
        except Exception:
            pass

    def _on_yes(self):
        try:
            if hasattr(self.controller, 'switch_tab'):
                self.controller.switch_tab('procedure_viewer')
            # Start homing in background so GUI remains responsive
            threading.Thread(target=self._home_gantry, daemon=True).start()
        finally:
            try:
                self.place_forget()
                self.destroy()
            except Exception:
                pass

    def _on_no(self):
        try:
            if hasattr(self.controller, 'switch_tab'):
                self.controller.switch_tab('file_manager')
        finally:
            try:
                self.place_forget()
                self.destroy()
            except Exception:
                pass

    def _home_gantry(self):
        try:
            th = getattr(self.move_registry, 'toolhead', None)
            if th:
                th.home()
            else:
                self.logger.warning('Toolhead not available for homing')
        except Exception as e:
            self.logger.exception(f'Homing from splash failed: {e}')
