import customtkinter as ctk
import threading
import logging
from typing import Dict, List, Tuple
import json
import os
import cv2
from PIL import Image

from ...components.constants import *
from drivers.controlboard_driver import ControlBoard


class ArucoCalibrationMainPanel(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color=FOREGROUND_COLOR)
        self.controller = controller

        camera_label = ctk.CTkLabel(self, text="Camera Feed", font=("Arial", 12, "bold"))
        camera_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.camera_display = ctk.CTkLabel(
            self,
            width=600,
            height=400,
            bg_color="#000000",
            text="",
            corner_radius=0
        )
        self.camera_display.grid(row=1, column=0, padx=5, pady=5)

        status_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR_TWO)
        status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        status_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(status_frame, text="Status:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=3)
        self.status_label = ctk.CTkLabel(status_frame, text="Ready", font=("Arial", 10))
        self.status_label.grid(row=0, column=1, padx=5, pady=3, sticky="w")

        position_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR_TWO)
        position_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        position_frame.columnconfigure(0, weight=1)

        self.position_label = ctk.CTkLabel(
            position_frame,
            text="Gantry Position: X=0.00mm Y=0.00mm Z=0.00mm",
            font=("Arial", 9),
            justify="left"
        )
        self.position_label.grid(row=0, column=0, padx=5, pady=3, sticky="ew")

        # Expose controller handles so ArucoCalibrationFrame can use them
        self.controller.camera_display = self.camera_display
        self.controller.status_label = self.status_label
        self.controller.position_label = self.position_label


class ArucoCalibrationSidePanel(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color=FOREGROUND_COLOR)
        self.controller = controller

        controls_label = ctk.CTkLabel(self, text="Calibration Controls", font=("Arial", 12, "bold"))
        controls_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        button_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR)
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        self.scan_button = ctk.CTkButton(
            button_frame,
            text="Start Calibration Scan",
            command=self.controller._start_calibration_scan,
            fg_color="#2E7D32",
            hover_color="#1B5E20"
        )
        self.scan_button.grid(row=0, column=0, sticky="ew", padx=2, pady=5)

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.controller._cancel_calibration,
            fg_color="#C62828",
            hover_color="#880E4F",
            state="disabled"
        )
        self.cancel_button.grid(row=0, column=1, sticky="ew", padx=2, pady=5)

        self.home_button = ctk.CTkButton(
            button_frame,
            text="Home Gantry",
            command=self.controller._home_gantry,
            fg_color="#1565C0",
            hover_color="#0D47A1"
        )
        self.home_button.grid(row=1, column=0, sticky="ew", padx=2, pady=5)

        self.refresh_position_button = ctk.CTkButton(
            button_frame,
            text="Refresh Position",
            command=self.controller._refresh_position,
            fg_color="#616161",
            hover_color="#424242"
        )
        self.refresh_position_button.grid(row=1, column=1, sticky="ew", padx=2, pady=5)

        markers_label = ctk.CTkLabel(self, text="Detected Markers", font=("Arial", 12, "bold"))
        markers_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(10, 5))

        self.markers_display = ctk.CTkTextbox(
            self,
            width=280,
            height=150,
            font=("Courier", 9),
            state="disabled",
            text_color=PLAIN_TEXT_COLOR
        )
        self.markers_display.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)

        positions_label = ctk.CTkLabel(self, text="Calibrated Positions", font=("Arial", 12, "bold"))
        positions_label.grid(row=4, column=0, sticky="ew", padx=5, pady=(10, 5))

        self.positions_listbox = ctk.CTkTextbox(
            self,
            width=280,
            height=150,
            font=("Courier", 9),
            state="disabled",
            text_color=PLAIN_TEXT_COLOR
        )
        self.positions_listbox.grid(row=5, column=0, sticky="nsew", padx=5, pady=5)

        management_frame = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR)
        management_frame.grid(row=6, column=0, sticky="ew", padx=5, pady=5)
        management_frame.columnconfigure(0, weight=1)
        management_frame.columnconfigure(1, weight=1)

        self.save_button = ctk.CTkButton(
            management_frame,
            text="Save Selected",
            command=self.controller._save_selected_position,
            fg_color="#00897B",
            hover_color="#004D40",
            state="disabled"
        )
        self.save_button.grid(row=0, column=0, sticky="ew", padx=2, pady=5)

        self.delete_button = ctk.CTkButton(
            management_frame,
            text="Delete Selected",
            command=self.controller._delete_selected_position,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            state="disabled"
        )
        self.delete_button.grid(row=0, column=1, sticky="ew", padx=2, pady=5)

        self.clear_all_button = ctk.CTkButton(
            management_frame,
            text="Clear All",
            command=self.controller._clear_all_calibrations,
            fg_color="#F57F17",
            hover_color="#E65100"
        )
        self.clear_all_button.grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=5)

        self.controller.scan_button = self.scan_button
        self.controller.cancel_button = self.cancel_button
        self.controller.home_button = self.home_button
        self.controller.refresh_position_button = self.refresh_position_button
        self.controller.markers_display = self.markers_display
        self.controller.positions_listbox = self.positions_listbox
        self.controller.save_button = self.save_button
        self.controller.delete_button = self.delete_button
        self.controller.clear_all_button = self.clear_all_button


class ArucoCalibrationFrame(ctk.CTkFrame):
    """Frame for calibrating ArUco marker positions in absolute coordinate system"""
    
    def __init__(self, master, dispatcher, **kwargs):
        super().__init__(master, fg_color=FOREGROUND_COLOR, corner_radius=0)
        
        self.logger = logging.getLogger("Main Logger")
        self.dispatcher = dispatcher
        self.control_board: ControlBoard = dispatcher.control_board
        
        # Use shared ArUco detector and video capture from dispatcher
        self.aruco_detector = dispatcher.aruco_detector
        self.myVideoCapture = dispatcher.video_capture
        self.width = dispatcher.camera_width
        self.height = dispatcher.camera_height
        
        # Calibration data storage
        self.calibration_data: Dict[int, Dict] = {}  # saved/permanent calibrations
        self.pending_calibrations: Dict[int, Dict] = {}  # newly scanned calibrations not yet saved
        self.calibration_file = "calibration_data/aruco_calibrations.json"
        self._load_calibration_data()
        
        # State tracking
        self._is_paused = False
        self._calibration_in_progress = False
        self._cancel_requested = False
        self._verification_results: List[Tuple[float, float, float]] = []
        self._video_feed_after_id = None
        
        # Setup UI
        self._setup_ui()
        self._load_calibration_data()
    
    def _setup_ui(self):
        """Setup the user interface using split main/side panel classes"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="ArUco Marker Position Calibration",
            font=("Arial", 18, "bold")
        )
        header.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        main_container = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR)
        main_container.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        main_container.columnconfigure(0, weight=2)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        self.main_panel = ArucoCalibrationMainPanel(main_container, controller=self)
        self.main_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.side_panel = ArucoCalibrationSidePanel(main_container, controller=self)
        self.side_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Mirror control references to allow existing logic to run unchanged
        self.scan_button = self.side_panel.scan_button
        self.cancel_button = self.side_panel.cancel_button
        self.home_button = self.side_panel.home_button
        self.refresh_position_button = self.side_panel.refresh_position_button
        self.markers_display = self.side_panel.markers_display
        self.positions_listbox = self.side_panel.positions_listbox
        self.save_button = self.side_panel.save_button
        self.delete_button = self.side_panel.delete_button
        self.clear_all_button = self.side_panel.clear_all_button
        self.status_label = self.main_panel.status_label
        self.camera_display = self.main_panel.camera_display
        self.position_label = self.main_panel.position_label
    
    def _update_camera_display(self):
        """Update the camera display with the latest frame from shared video capture"""
        if self._is_paused:
            self._video_feed_after_id = self.camera_display.after(20, self._update_camera_display)
            return
        
        # Read frame from shared video capture
        ret, frame = self.myVideoCapture.read()
        if not ret:
            self._video_feed_after_id = self.camera_display.after(10, self._update_camera_display)
            return
        
        # Process frame with shared ArUco detector
        result = self.aruco_detector.detect_markers(frame)
        frame = result['frame']
        
        # Log detection results
        if result['count'] > 0:
            self.logger.debug(f"Detected {result['count']} markers")
        
        # Convert for Tkinter display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        captured_image = Image.fromarray(frame_rgb)
        
        ctk_image = ctk.CTkImage(
            light_image=captured_image,
            dark_image=captured_image,
            size=(self.width, self.height)
        )
        
        # Update display
        self.camera_display.configure(image=ctk_image)
        self.camera_display.image = ctk_image
        
        # Schedule next update
        self._video_feed_after_id = self.camera_display.after(20, self._update_camera_display)
    
    def _start_camera_display(self):
        """Start the camera display update loop"""
        self._is_paused = False
        if self._video_feed_after_id is None:
            self._update_camera_display()
    
    def _stop_camera_display(self):
        """Stop the camera display update loop"""
        self._is_paused = True
        if self._video_feed_after_id is not None:
            self.camera_display.after_cancel(self._video_feed_after_id)
            self._video_feed_after_id = None
    
    def pause_updates(self):
        """Pause camera display when frame is hidden"""
        self._stop_camera_display()
    
    def resume_updates(self):
        """Resume camera display when frame becomes visible"""
        self._start_camera_display()
    
    def _start_calibration_scan(self):
        """Start the calibration scanning process in a background thread"""
        if self._calibration_in_progress:
            self.logger.warning("Calibration already in progress")
            return
        
        self.scan_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self._calibration_in_progress = True
        self._cancel_requested = False
        
        # Start displaying camera feed
        self._start_camera_display()
        
        # Run calibration in background thread
        calibration_thread = threading.Thread(target=self._calibration_worker, daemon=True)
        calibration_thread.start()
    
    def _calibration_worker(self):
        """Background worker for calibration process"""
        import time

        try:
            cap = self.myVideoCapture

            while not self._cancel_requested:
                self._update_status("Scanning for markers...")

                start_time = time.time()
                detected_markers = {}

                while time.time() - start_time < 2.0 and not self._cancel_requested:
                    ret, frame = cap.read()
                    if not ret:
                        continue

                    result = self.aruco_detector.detect_markers(frame)
                    if result['count'] > 0:
                        for marker in result['markers']:
                            marker_id = marker['id']
                            if marker_id not in detected_markers:
                                detected_markers[marker_id] = []
                            detected_markers[marker_id].append(marker['position'])

                if self._cancel_requested:
                    break

                if not detected_markers:
                    self._update_status("No markers detected. Retry in 1 sec or Cancel.")
                    time.sleep(1.0)
                    continue

                # Average the detections for each marker
                marker_positions = {}
                for marker_id, positions in detected_markers.items():
                    if positions:
                        marker_positions[marker_id] = {
                            'x': sum(p['x'] for p in positions) / len(positions),
                            'y': sum(p['y'] for p in positions) / len(positions),
                            'z': sum(p['z'] for p in positions) / len(positions)
                        }

                # Get current gantry position
                gantry_pos = self.control_board.positions.copy()

                # Calculate absolute positions (relative marker pos + gantry pos)
                absolute_positions = {}
                for marker_id, rel_pos in marker_positions.items():
                    absolute_positions[marker_id] = {
                        'x': gantry_pos['X'] + rel_pos['x'] * 1000,
                        'y': gantry_pos['Y'] + rel_pos['y'] * 1000,
                        'z': gantry_pos['Z'] + rel_pos['z'] * 1000
                    }

                self._update_status("Verifying calibration...")

                verified_results = {}

                for marker_id, abs_pos in absolute_positions.items():
                    if self._cancel_requested:
                        break

                    self._verification_results = []
                    for attempt in range(3):
                        if self._cancel_requested:
                            break

                        self._update_status(f"Verification {attempt + 1}/3 for Marker {marker_id}...")
                        self.logger.debug(f"Homing gantry for verification attempt {attempt + 1}")
                        self.control_board.send_message("G28")
                        self.control_board.finish_moves()
                        time.sleep(0.5)

                        self.logger.debug(f"Moving to calibrated position: X={abs_pos['x']:.2f} Y={abs_pos['y']:.2f} Z={abs_pos['z']:.2f}")
                        self.control_board.move_axis('X', abs_pos['x'], feedrate_mm_per_minute=2000)
                        self.control_board.move_axis('Y', abs_pos['y'], feedrate_mm_per_minute=2000)
                        self.control_board.move_axis('Z', abs_pos['z'], feedrate_mm_per_minute=600)

                        time.sleep(0.5)

                        scan_start = time.time()
                        while time.time() - scan_start < 1.0 and not self._cancel_requested:
                            ret, frame = cap.read()
                            if not ret:
                                continue

                            result = self.aruco_detector.detect_markers(frame)
                            for marker in result['markers']:
                                if marker['id'] == marker_id:
                                    self._verification_results.append(marker['position'])

                    if self._cancel_requested:
                        break

                    if len(self._verification_results) < 2:
                        self._update_status(f"Failed to verify Marker {marker_id}. Will retry full scan.")
                        self.logger.warning(f"Verification failed for Marker {marker_id}: {len(self._verification_results)} hits")
                        continue

                    avg_result = {
                        'x': sum(p['x'] for p in self._verification_results) / len(self._verification_results),
                        'y': sum(p['y'] for p in self._verification_results) / len(self._verification_results),
                        'z': sum(p['z'] for p in self._verification_results) / len(self._verification_results)
                    }

                    verified_results[marker_id] = {
                        'relative_positions': [marker_positions[marker_id]],
                        'absolute_position': abs_pos,
                        'verification_count': len(self._verification_results),
                        'gantry_reference': gantry_pos,
                        'verification_average': avg_result
                    }

                    self.logger.info(f"Marker {marker_id} calibration verified: {abs_pos}")

                if self._cancel_requested:
                    break

                if not verified_results:
                    self._update_status("No verified markers, retrying scan.")
                    time.sleep(1.0)
                    continue

                # Save to pending calibrations and update UI
                self.pending_calibrations.update(verified_results)
                self._update_status(f"Calibration complete: {len(verified_results)} marker(s) pending save.")
                self._update_ui()
                return

            if self._cancel_requested:
                self._update_status("Calibration cancelled by user")

        except Exception as e:
            self.logger.error(f"Calibration error: {e}")
            self._update_status(f"Error: {e}")
        finally:
            self._reset_calibration()
    
    def _home_gantry(self):
        """Home the gantry to origin"""
        self._update_status("Homing gantry...")
        self.logger.debug("Homing gantry")
        self.control_board.send_message("G28")
        self.control_board.finish_moves()
        self._update_status("Gantry homed")
        self._refresh_position()
    
    def _refresh_position(self):
        """Refresh the displayed gantry position"""
        pos = self.control_board.positions
        pos_text = f"Gantry Position: X={pos['X']:.2f}mm Y={pos['Y']:.2f}mm Z={pos['Z']:.2f}mm"
        self.position_label.configure(text=pos_text)
    
    def _cancel_calibration(self):
        """Cancel ongoing calibration"""
        self._cancel_requested = True
        self._update_status("Calibration cancellation requested")
    
    def _reset_calibration(self):
        """Reset calibration UI state"""
        self._calibration_in_progress = False
        self.scan_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        # Stop displaying camera feed
        self._stop_camera_display()
    
    def _save_selected_position(self):
        """Save pending calibrated positions to permanent calibration file"""
        if not self.pending_calibrations:
            self._update_status("No pending calibrations to save")
            return

        for marker_id, data in self.pending_calibrations.items():
            self.calibration_data[marker_id] = data

        self.pending_calibrations.clear()
        self._save_calibration_data()
        self._update_ui()
        self._update_status("Pending calibrations saved permanently")
    
    def _delete_selected_position(self):
        """Delete a selected calibration"""
        try:
            selected = self.positions_listbox.selection_get()
        except Exception:
            selected = None

        if not selected:
            self._update_status("No selection available for deletion")
            return

        try:
            marker_id = int(selected.split("ID:")[1].split()[0])
        except Exception:
            self.logger.warning("Could not parse marker ID from selection")
            self._update_status("Failed to parse selected marker ID")
            return

        if marker_id in self.pending_calibrations:
            del self.pending_calibrations[marker_id]
            self._update_ui()
            self._update_status(f"Deleted pending calibration for Marker {marker_id}")
            return

        if marker_id in self.calibration_data:
            del self.calibration_data[marker_id]
            self._save_calibration_data()
            self._update_ui()
            self._update_status(f"Deleted saved calibration for Marker {marker_id}")
            return

        self._update_status(f"Marker ID {marker_id} not found in pending or saved calibrations")
    
    def _clear_all_calibrations(self):
        """Clear all calibrated positions"""
        self.calibration_data.clear()
        self.pending_calibrations.clear()
        self._save_calibration_data()
        self._update_ui()
        self._update_status("All calibrations cleared")
    
    def _update_status(self, status: str):
        """Update the status label"""
        self.status_label.configure(text=status)
        self.logger.debug(f"[Calibration] {status}")
    
    def _update_ui(self):
        """Update the UI displays"""
        # Update detected markers display (pending calibrations)
        self.markers_display.configure(state="normal")
        self.markers_display.delete("1.0", "end")

        if self.pending_calibrations:
            self.markers_display.insert("end", "Pending (Newly Calibrated) Markers:\n")
            for marker_id, data in self.pending_calibrations.items():
                abs_pos = data['absolute_position']
                self.markers_display.insert("end", f"Marker ID {marker_id}: X={abs_pos['x']:.2f}, Y={abs_pos['y']:.2f}, Z={abs_pos['z']:.2f}\n")
        else:
            self.markers_display.insert("end", "No newly calibrated markers. Start a scan to detect markers.\n")

        self.markers_display.configure(state="disabled")

        # Update calibrated positions list (saved + pending)
        self.positions_listbox.configure(state="normal")
        self.positions_listbox.delete("1.0", "end")

        if self.calibration_data:
            self.positions_listbox.insert("end", "Saved (Permanent) Calibrations:\n")
            for marker_id, data in self.calibration_data.items():
                abs_pos = data['absolute_position']
                self.positions_listbox.insert("end", f"Marker ID: {marker_id}\n  X: {abs_pos['x']:.2f}mm\n  Y: {abs_pos['y']:.2f}mm\n  Z: {abs_pos['z']:.2f}mm\n\n")

        if self.pending_calibrations:
            self.positions_listbox.insert("end", "Pending (Unsaved) Calibrations:\n")
            for marker_id, data in self.pending_calibrations.items():
                abs_pos = data['absolute_position']
                self.positions_listbox.insert("end", f"Marker ID: {marker_id} (pending)\n  X: {abs_pos['x']:.2f}mm\n  Y: {abs_pos['y']:.2f}mm\n  Z: {abs_pos['z']:.2f}mm\n\n")

        if not self.calibration_data and not self.pending_calibrations:
            self.positions_listbox.insert("end", "No saved or pending calibrations yet.\n")

        self.positions_listbox.configure(state="disabled")

        # Enable/disable management buttons
        has_pending = len(self.pending_calibrations) > 0
        has_any = has_pending or len(self.calibration_data) > 0

        self.save_button.configure(state="normal" if has_pending else "disabled")
        self.delete_button.configure(state="normal" if has_any else "disabled")
    
    def _load_calibration_data(self):
        """Load calibration data from file"""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    self.calibration_data = json.load(f)
                    # Convert string keys back to integers
                    self.calibration_data = {int(k): v for k, v in self.calibration_data.items()}
                    self.logger.debug(f"Loaded {len(self.calibration_data)} calibrations from file")
            self._update_ui()
        except Exception as e:
            self.logger.error(f"Failed to load calibration data: {e}")
            self.calibration_data = {}
    
    def _save_calibration_data(self):
        """Save calibration data to file"""
        try:
            os.makedirs(os.path.dirname(self.calibration_file), exist_ok=True)
            with open(self.calibration_file, 'w') as f:
                json.dump(self.calibration_data, f, indent=2)
                self.logger.debug(f"Saved {len(self.calibration_data)} calibrations to file")
        except Exception as e:
            self.logger.error(f"Failed to save calibration data: {e}")
    
    def pause_updates(self):
        """Pause update loop when tab is not active"""
        self._is_paused = True
    
    def resume_updates(self):
        """Resume update loop when tab is active"""
        self._is_paused = False
