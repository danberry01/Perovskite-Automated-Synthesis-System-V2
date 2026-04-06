import customtkinter as ctk
from ..components.constants import *
import logging
from time import sleep
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from drivers.procedure_file_driver import ProcedureFile

# Place the ConsoleFrame inside the InfoFrame so the console is part of the
# bottom pane and remains visible when the procedure viewer is not active.
from .procedure_viewer.console_frame import ConsoleFrame


class InfoFrame(ctk.CTkFrame):
    """Frame to display miscellaneous information (contains console + status)."""
    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=FOREGROUND_COLOR_TWO)

        self.controller = controller
        # MoveRegistry and procedure_handler (may be None during early init)
        self.move_registry = getattr(controller, 'move_registry', None)
        self.procedure_handler = getattr(controller, 'procedure_handler', None)

        # Layout: top row = status (coords + progress + step info), bottom = console
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        # Status frame in the top-right of this InfoFrame
        self.status_frame = ctk.CTkFrame(master=self, fg_color=FOREGROUND_COLOR_TWO)
        self.status_frame.grid(row=0, column=1, sticky="ne", padx=10, pady=6)

        # Position labels (X Y Z) grouped to the right
        self.pos_label = ctk.CTkLabel(self.status_frame, text="X: --  Y: --  Z: --", anchor="e",
                                      font=("Arial", 14))
        self.pos_label.grid(row=0, column=0, sticky="ne")

        # Procedure step info
        self.step_info_label = ctk.CTkLabel(self.status_frame, text="No Procedure Loaded - Use Import to load one",
                                            anchor="e", font=("Arial", 12))
        self.step_info_label.grid(row=1, column=0, sticky="ne", pady=(4, 0))

        # Progress bar (0.0 - 1.0)
        self.progress = ctk.CTkProgressBar(master=self.status_frame, width=240)
        self.progress.set(0.0)
        self.progress.grid(row=2, column=0, sticky="ne", pady=(6, 0))

        # Hotplate temperature label
        self.hotplate_label = ctk.CTkLabel(self.status_frame, text="Hotplate: --/--", anchor="e", font=("Arial", 12))
        self.hotplate_label.grid(row=3, column=0, sticky="ne")

        # Spincoater status label
        self.spincoater_label = ctk.CTkLabel(self.status_frame, text="Spincoater: Disconnected | RPM: --", anchor="e", font=("Arial", 12))
        self.spincoater_label.grid(row=4, column=0, sticky="ne")

        # Email dropdown + send button (below hotplate/spincoater info)
        # emails.yml is stored under Code/src/persistant/emails.yml
        self._emails_file = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'persistant', 'emails.yml'))
        self._smtp_config = {}
        self._from_addr = 'pass@localhost'
        try:
            self._ensure_emails_file()
            self.emails = self._load_emails() or []
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to initialize emails.yml")
            self.emails = []

        # Option menu for selecting recipient
        option_values = self.emails if len(self.emails) > 0 else ["(no emails. Add to emails.yml)"]
        self.email_dropdown = ctk.CTkOptionMenu(
            master=self.status_frame,
            values=option_values,
            width=200,
            fg_color=PLAIN_TEXT_COLOR,
            button_color=PLAIN_TEXT_COLOR,
            button_hover_color=FOREGROUND_COLOR_TWO,
            corner_radius=0,
            command=self._on_email_selected
        )
        self.email_dropdown.grid(row=5, column=0, sticky="ne", padx=5, pady=(6, 0))

        # Button to send the entire console log to the selected email
        self.email_button = ctk.CTkButton(master=self.status_frame, text="Email Console", command=self.send_console_email)
        self.email_button.grid(row=6, column=0, sticky="ne", padx=5, pady=(6, 6))

        # Console placed in the bottom area
        self.console_frame = ConsoleFrame(master=self)
        self.console_frame.grid(row=0, column=0, sticky="nsew")

        # Start periodic update loop
        try:
            self._after_id = None
            self._update_loop()
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to start InfoFrame update loop")

    def _format_pos(self, v):
        try:
            if v is None:
                return "--"
            return f"{float(v):.2f}"
        except Exception:
            return str(v)

    def _update_loop(self):
        """Periodic UI update: refresh positions, progress, and step info."""
        try:
            # Update positions from control board if available
            x = y = z = None
            try:
                if self.move_registry and hasattr(self.move_registry, 'control_board') and self.move_registry.control_board:
                        # Do not actively request a position here; keep UI reads
                        # lightweight and rely on the control board's move-wait
                        # logic to request updates while moves are in progress.
                        x = self.move_registry.toolhead.get_position('X')
                        y = self.move_registry.toolhead.get_position('Y')
                        z = self.move_registry.toolhead.get_position('Z')
            except Exception:
                pass

            pos_text = f"X: {self._format_pos(x)}  Y: {self._format_pos(y)}  Z: {self._format_pos(z)}"
            try:
                self.pos_label.configure(text=pos_text)
            except Exception:
                pass

            # Update procedure progress and current step info
            try:
                ph = getattr(self.controller, 'procedure_handler', None)
                if ph and ph.procedure:
                    progress = ph.get_progress()
                    self.progress.set(progress)

                    cur = ph.get_current_step_index()
                    total = len(ph.procedure)
                    if cur < total and total > 0:
                        step = ph.procedure[cur]
                        func_name = step[0]
                        args = step[1:]
                        step_text = f"Step {cur+1}/{total}: {func_name}({', '.join(map(str,args))})"
                    else:
                        step_text = "Procedure idle"
                else:
                    self.progress.set(0.0)
                    step_text = "No Procedure Loaded - Use Import to load one"

                try:
                    self.step_info_label.configure(text=step_text)
                except Exception:
                    pass
            except Exception:
                logging.getLogger("Main Logger").exception("Error updating procedure info")

            # Update hotplate and spincoater statuses
            try:
                hp = getattr(self.move_registry, 'hotplate', None)
                if hp is not None:
                    current_temperature = getattr(hp, 'current_temperature_c', '--')
                    target_temperature = getattr(hp, 'target_temperature_c', '--')
                    try:
                        hp_status = "Connected" if (hasattr(hp, 'is_connected') and hp.is_connected()) else "Disconnected"
                    except Exception:
                        hp_status = "Connected" if getattr(hp, 'serial', None) else "Disconnected"
                    try:
                        self.hotplate_label.configure(text=f"Hotplate: {current_temperature}/{target_temperature} °C ({hp_status})")
                    except Exception:
                        pass
                else:
                    try:
                        self.hotplate_label.configure(text="Hotplate: --/--")
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                sc = getattr(self.move_registry, 'spin_coater', None)
                if sc is not None:
                    try:
                        sc_status = "Connected" if sc.is_connected() else "Disconnected"
                    except Exception:
                        sc_status = "Connected" if getattr(sc, 'serial', None) else "Disconnected"
                    is_running = getattr(sc, 'is_running', False)
                    rpm = getattr(sc, 'last_rpm', None)
                    rpm_text = str(rpm) if rpm is not None else "N/A"
                    running_text = "Running" if is_running else "Idle"
                    try:
                        self.spincoater_label.configure(text=f"Spincoater: {sc_status} | {running_text} | RPM: {rpm_text}")
                    except Exception:
                        pass
                else:
                    try:
                        self.spincoater_label.configure(text="Spincoater: Disconnected | RPM: --")
                    except Exception:
                        pass
            except Exception:
                pass

        finally:
            # Schedule next update
            try:
                # Reduce polling frequency to avoid flooding the console with
                # frequent M114 requests; 1000ms is sufficient for UI updates.
                self._after_id = self.after(1000, self._update_loop)
            except Exception:
                pass

    def _ensure_emails_file(self):
        try:
            # Use the same ProcedureFile helper used for locations.yml so
            # parsing/formatting is consistent across the app.
            pf = ProcedureFile()
            data = pf.Open('persistant/emails.yml') or pf.Open('persistant/emails')
            if not data:
                default = {
                    'smtp': {
                        'host': 'localhost',
                        'port': 25,
                        'username': '',
                        'password': '',
                        'use_tls': False
                    },
                    'from': 'pass@localhost',
                    'recipients': ['user@example.com']
                }
                pf.Save('persistant/emails', default)
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to create emails.yml")

    def _load_emails(self):
        try:
            pf = ProcedureFile()
            data = pf.Open('persistant/emails.yml') or pf.Open('persistant/emails')
            if not data:
                return []
            self._smtp_config = data.get('smtp', {}) or {}
            self._from_addr = data.get('from', self._smtp_config.get('username') or 'pass@localhost')
            return data.get('recipients', []) or []
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to load emails.yml")
            return []

    def _on_email_selected(self, value):
        self._selected_email = value

    def send_console_email(self):
        try:
            recipient = getattr(self, '_selected_email', None)
            try:
                if not recipient and hasattr(self.email_dropdown, 'get'):
                    recipient = self.email_dropdown.get()
            except Exception:
                pass
            if not recipient or recipient == "(no emails)":
                self.console_frame.write_to_console(f"ERROR\t{datetime.now().isoformat()}: No recipient selected for email.")
                return
            try:
                console_text = self.console_frame.console.get("1.0", "end")
            except Exception:
                console_text = ""
            subject = f"PASS Console Log [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = getattr(self, '_from_addr', 'pass@localhost')
            msg['To'] = recipient
            msg.set_content(console_text)
            smtp = getattr(self, '_smtp_config', {}) or {}
            host = smtp.get('host', 'localhost')
            port = smtp.get('port', 25)
            username = smtp.get('username')
            password = smtp.get('password')
            use_tls = smtp.get('use_tls', False)
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
            server.quit()
            self.console_frame.write_to_console(f"INFO\t{datetime.now().isoformat()}: Sent console log to {recipient}")
        except Exception as e:
            logging.getLogger("Main Logger").exception("Failed to send console email: %s", e)
            try:
                self.console_frame.write_to_console(f"ERROR\t{datetime.now().isoformat()}: Failed to send email: {e}")
            except Exception:
                pass