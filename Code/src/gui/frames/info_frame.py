import customtkinter as ctk
from ..components.constants import *
import logging
from time import sleep
import os
import shutil
import socket
import smtplib
import subprocess
import threading
from email.message import EmailMessage
from datetime import datetime
from drivers.procedure_file_driver import ProcedureFile

# Place the ConsoleFrame inside the InfoFrame so the console is part of the
# bottom pane and remains visible when the procedure viewer is not active.
from .procedure_viewer.console_frame import ConsoleFrame


class InfoFrame(ctk.CTkFrame):
    """Frame to display miscellaneous information (contains console + status)."""
    _NO_EMAIL_OPTION = "(no emails. Add to emails.yml)"

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
        self._from_addr = self._build_default_from_address()
        self._email_send_thread = None
        self._selected_email = None
        try:
            self._ensure_emails_file()
            self.emails = self._load_emails() or []
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to initialize emails.yml")
            self.emails = []

        # Option menu for selecting recipient
        option_values = self.emails if len(self.emails) > 0 else [self._NO_EMAIL_OPTION]
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
        if self.emails:
            self._selected_email = self.emails[0]
            self.email_dropdown.set(self._selected_email)
        else:
            self.email_dropdown.set(self._NO_EMAIL_OPTION)

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
            os.makedirs(os.path.dirname(self._emails_file), exist_ok=True)
            pf = ProcedureFile()
            data = pf.Open(self._emails_file)
            if not data:
                default = {
                    'smtp': {
                        'transport': 'auto',
                        'host': 'localhost',
                        'port': 25,
                        'username': '',
                        'password': '',
                        'use_tls': False,
                        'use_ssl': False,
                        'timeout': 10,
                        'sendmail_path': '',
                        'mail_path': ''
                    },
                    'from': self._build_default_from_address(),
                    'recipients': ['dcounte1@binghamton.edu']
                }
                pf.Save(self._emails_file, default)
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to create emails.yml")

    def _load_emails(self):
        try:
            pf = ProcedureFile()
            data = pf.Open(self._emails_file)
            if not isinstance(data, dict):
                return []
            self._smtp_config = data.get('smtp', {}) or {}
            self._from_addr = str(data.get('from') or self._smtp_config.get('username') or self._build_default_from_address()).strip()

            recipients = data.get('recipients', []) or []
            if isinstance(recipients, str):
                recipients = [recipients]
            return [str(recipient).strip() for recipient in recipients if str(recipient).strip()]
        except Exception:
            logging.getLogger("Main Logger").exception("Failed to load emails.yml")
            return []

    def _on_email_selected(self, value):
        self._selected_email = value

    def send_console_email(self):
        if self._email_send_thread and self._email_send_thread.is_alive():
            self._write_email_status("WARNING", "Email delivery already in progress.")
            return

        try:
            recipient = getattr(self, '_selected_email', None)
            try:
                if not recipient and hasattr(self.email_dropdown, 'get'):
                    recipient = self.email_dropdown.get()
            except Exception:
                pass
            if not recipient or recipient == self._NO_EMAIL_OPTION:
                self._write_email_status("ERROR", "No recipient selected for email.")
                return

            console_text = self._get_console_log_text()
            self._set_email_button_state(enabled=False, text="Sending...")
            self._email_send_thread = threading.Thread(
                target=self._send_console_email_worker,
                args=(recipient, console_text),
                daemon=True
            )
            self._email_send_thread.start()
        except Exception as e:
            logging.getLogger("Main Logger").exception("Failed to send console email: %s", e)
            self._set_email_button_state(enabled=True, text="Email Console")
            self._write_email_status("ERROR", f"Failed to queue email send: {e}")

    def _build_default_from_address(self) -> str:
        hostname = socket.gethostname().strip() or 'localhost'
        return f"pass@{hostname}"

    def _write_email_status(self, level: str, message: str):
        try:
            self.console_frame.write_to_console(f"{level}\t{datetime.now().isoformat()}: {message}")
        except Exception:
            pass

    def _get_console_log_text(self) -> str:
        try:
            console_text = self.console_frame.get_log_text()
        except Exception:
            console_text = ""

        if console_text.strip():
            return console_text

        try:
            return self.console_frame.console.get("1.0", "end").strip()
        except Exception:
            return ""

    def _set_email_button_state(self, enabled: bool, text: str):
        try:
            self.email_button.configure(state="normal" if enabled else "disabled", text=text)
        except Exception:
            pass

    def _send_console_email_worker(self, recipient: str, console_text: str):
        try:
            message = self._build_console_email_message(recipient, console_text)
            self._deliver_email_message(message)
            self.after(0, lambda: self._write_email_status("INFO", f"Sent console log to {recipient}"))
        except Exception as e:
            logging.getLogger("Main Logger").error("Failed to send console email: %s", e)
            self.after(0, lambda: self._write_email_status("ERROR", f"Failed to send email: {e}"))
        finally:
            self.after(0, lambda: self._set_email_button_state(enabled=True, text="Email Console"))

    def _build_console_email_message(self, recipient: str, console_text: str) -> EmailMessage:
        timestamp = datetime.now()
        hostname = socket.gethostname().strip() or 'localhost'
        subject = f"PASS Console Log [{hostname}] [{timestamp.strftime('%Y-%m-%d %H:%M:%S')}]"
        body = console_text.strip() or "Console log was empty at send time."

        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = getattr(self, '_from_addr', self._build_default_from_address())
        message['To'] = recipient
        message.set_content(body)
        message.add_attachment(
            body.encode('utf-8'),
            maintype='text',
            subtype='plain',
            filename=f"pass-console-{timestamp.strftime('%Y%m%d-%H%M%S')}.log"
        )
        return message

    def _deliver_email_message(self, message: EmailMessage):
        smtp = getattr(self, '_smtp_config', {}) or {}
        transport = str(smtp.get('transport', 'auto')).strip().lower() or 'auto'
        if transport not in ('auto', 'smtp', 'sendmail', 'mail'):
            transport = 'auto'

        errors = []
        if transport in ('auto', 'smtp'):
            try:
                self._send_via_smtp(message, smtp)
                return
            except Exception as exc:
                errors.append(f"SMTP delivery failed: {exc}")
                if transport == 'smtp':
                    raise

        if transport in ('auto', 'sendmail'):
            try:
                self._send_via_sendmail(message, smtp)
                return
            except Exception as exc:
                errors.append(f"sendmail delivery failed: {exc}")
                if transport == 'sendmail':
                    raise

        if transport in ('auto', 'mail'):
            try:
                self._send_via_mail_command(message, smtp)
                return
            except Exception as exc:
                errors.append(f"mail delivery failed: {exc}")
                if transport == 'mail':
                    raise

        if errors:
            raise RuntimeError("; ".join(errors))

    def _send_via_smtp(self, message: EmailMessage, smtp_config: dict):
        host = str(smtp_config.get('host') or 'localhost').strip()
        port = self._coerce_int(smtp_config.get('port'), 25)
        timeout = self._coerce_float(smtp_config.get('timeout'), 10.0)
        username = str(smtp_config.get('username') or '').strip()
        password = str(smtp_config.get('password') or '')
        use_tls = self._coerce_bool(smtp_config.get('use_tls'), False)
        use_ssl = self._coerce_bool(smtp_config.get('use_ssl'), False)
        local_hostname = str(smtp_config.get('local_hostname') or '').strip() or None

        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(host, port, timeout=timeout, local_hostname=local_hostname) as server:
            server.ehlo()
            if use_tls and not use_ssl:
                server.starttls()
                server.ehlo()
            if username:
                server.login(username, password)
            server.send_message(message)

    def _send_via_sendmail(self, message: EmailMessage, smtp_config: dict):
        sendmail_path = self._resolve_sendmail_path(smtp_config)
        if sendmail_path is None:
            raise FileNotFoundError("No sendmail-compatible binary found. Configure SMTP or install sendmail, msmtp, or postfix.")

        timeout = self._coerce_float(smtp_config.get('timeout'), 10.0)
        result = subprocess.run(
            [sendmail_path, '-t', '-oi'],
            input=message.as_bytes(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace').strip()
            raise RuntimeError(stderr or f"sendmail exited with code {result.returncode}")

    def _send_via_mail_command(self, message: EmailMessage, smtp_config: dict):
        mail_path = self._resolve_mail_path(smtp_config)
        if mail_path is None:
            raise FileNotFoundError("No mail or mailx binary found. Configure SMTP or install mailutils/bsd-mailx.")

        timeout = self._coerce_float(smtp_config.get('timeout'), 10.0)
        recipient = str(message.get('To') or '').strip()
        subject = str(message.get('Subject') or '').strip()
        body = self._extract_text_body(message)
        result = subprocess.run(
            [mail_path, '-s', subject, recipient],
            input=body.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace').strip()
            raise RuntimeError(stderr or f"{os.path.basename(mail_path)} exited with code {result.returncode}")

    def _resolve_sendmail_path(self, smtp_config: dict):
        configured_path = str(smtp_config.get('sendmail_path') or '').strip()
        candidates = [configured_path] if configured_path else []
        candidates.extend([
            shutil.which('sendmail'),
            shutil.which('msmtp'),
            '/usr/sbin/sendmail',
            '/usr/bin/sendmail',
            '/usr/bin/msmtp'
        ])

        for path in candidates:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def _resolve_mail_path(self, smtp_config: dict):
        configured_path = str(smtp_config.get('mail_path') or '').strip()
        candidates = [configured_path] if configured_path else []
        candidates.extend([
            shutil.which('mail'),
            shutil.which('mailx'),
            '/usr/bin/mail',
            '/usr/bin/mailx'
        ])

        for path in candidates:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def _extract_text_body(self, message: EmailMessage) -> str:
        body = message.get_body(preferencelist=('plain',))
        if body is not None:
            try:
                return body.get_content()
            except Exception:
                pass
        try:
            return message.get_content()
        except Exception:
            return message.as_string()

    def _coerce_bool(self, value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ('1', 'true', 'yes', 'on'):
                return True
            if normalized in ('0', 'false', 'no', 'off'):
                return False
        return default

    def _coerce_int(self, value, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _coerce_float(self, value, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default