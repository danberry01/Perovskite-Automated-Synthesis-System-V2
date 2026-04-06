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
from .aruco_calibration_layout import ArucoCalibrationLayout


class ArucoCalibrationFrame(ctk.CTkFrame):
    """Frame for calibrating ArUco marker positions.

    Coordinate system separation:
    - `relative_position`: marker position in the camera frame (meters)
    - `gantry_position`: physical gantry coordinates (mm) — never overridden by calibration
    - `abs_aruco_position`: computed gantry coordinates (mm) where the ARuCo marker is located

    `abs_aruco_position` is stored for reference only and is never used as
    a command target for motion. Motion is always driven by `gantry_position`.
    """
    
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
        
        # Shared frame buffer (updated by UI thread) for safe access from
        # the background calibration worker to avoid multiple threads
        # reading from the same VideoCapture instance concurrently.
        self._last_frame = None
        self._frame_lock = threading.Lock()
        # Calibration data storage
        self.calibration_data: Dict[int, Dict] = {}  # saved/permanent calibrations
        self.pending_calibrations: Dict[int, Dict] = {}  # newly scanned calibrations not yet saved
        self.calibration_file = "calibration_data/aruco_calibrations.json"

        # State tracking
        self._is_paused = False
        self._calibration_in_progress = False
        self._cancel_requested = False
        self._verification_results: List[Tuple[float, float, float]] = []
        self._video_feed_after_id = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.layout = ArucoCalibrationLayout(self, controller=self)
        self.layout.grid(row=0, column=0, sticky="nsew")

        self.camera_display = self.layout.main_panel.camera_display
        self.status_label = self.layout.main_panel.status_label
        self.position_label = self.layout.main_panel.position_label

        self.scan_button = self.layout.side_panel.scan_button
        self.cancel_button = self.layout.side_panel.cancel_button
        self.home_button = self.layout.side_panel.home_button
        self.refresh_position_button = self.layout.side_panel.refresh_position_button
        self.markers_display = self.layout.side_panel.markers_display
        self.positions_listbox = self.layout.side_panel.positions_listbox
        self.save_button = self.layout.side_panel.save_button
        self.delete_button = self.layout.side_panel.delete_button
        self.clear_all_button = self.layout.side_panel.clear_all_button

        self._load_calibration_data()
    
    
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
        # if result['count'] > 0:
        #     self.logger.debug(f"Detected {result['count']} markers")
        
        # Store a copy of the raw frame for the worker to use (avoid
        # concurrent reads from the VideoCapture). Use a lock for safety.
        try:
            with self._frame_lock:
                self._last_frame = frame.copy()
        except Exception:
            with self._frame_lock:
                self._last_frame = frame

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

    def _show_frame_on_ui(self, frame):
        """Helper to display an annotated BGR frame on the camera display.

        This method must be called from the UI thread (we schedule it with
        `_call_ui` from the worker thread).
        """
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            captured_image = Image.fromarray(frame_rgb)
            ctk_image = ctk.CTkImage(
                light_image=captured_image,
                dark_image=captured_image,
                size=(self.width, self.height)
            )
            self.camera_display.configure(image=ctk_image)
            self.camera_display.image = ctk_image
        except Exception:
            # Don't let UI display errors crash the worker
            pass
    
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
            # Worker reads frames from the UI-updated `_last_frame` buffer to
            # avoid multiple threads reading from the same VideoCapture.
            while not self._cancel_requested:
                self._call_ui(self._update_status, "Scanning for markers...")

                start_time = time.time()
                detected_markers = {}

                # Increase the initial scan window to give the camera time to
                # present stable frames. We sample the latest UI-updated frame.
                scan_window = 4.0
                min_detections_per_marker = 3
                span_threshold_m = 0.01  # 10 mm spread allowed across detections

                while time.time() - start_time < scan_window and not self._cancel_requested:
                    with self._frame_lock:
                        frame = None if self._last_frame is None else self._last_frame.copy()
                    if frame is None:
                        time.sleep(0.02)
                        continue

                    result = self.aruco_detector.detect_markers(frame)

                    # Show annotated frame in UI so the user sees each scan
                    if result and 'frame' in result:
                        self._call_ui(self._show_frame_on_ui, result['frame'])

                    if result['count'] > 0:
                        for marker in result['markers']:
                            marker_id = marker['id']
                            if marker_id not in detected_markers:
                                detected_markers[marker_id] = []
                            detected_markers[marker_id].append(marker['position'])

                    time.sleep(0.02)

                if self._cancel_requested:
                    break

                if not detected_markers:
                    self._call_ui(self._update_status, "No markers detected. Retry in 1 sec or Cancel.")
                    time.sleep(1.0)
                    continue

                # Filter and average detections for stability
                marker_positions = {}
                for marker_id, positions in detected_markers.items():
                    if len(positions) < min_detections_per_marker:
                        self.logger.debug(f"Marker {marker_id} seen only {len(positions)} times; skipping")
                        continue
                    xs = [p['x'] for p in positions]
                    ys = [p['y'] for p in positions]
                    zs = [p['z'] for p in positions]
                    span_x = max(xs) - min(xs)
                    span_y = max(ys) - min(ys)
                    span_z = max(zs) - min(zs)
                    if span_x > span_threshold_m or span_y > span_threshold_m or span_z > span_threshold_m:
                        self.logger.debug(f"Marker {marker_id} detections too spread (m): x={span_x:.4f} y={span_y:.4f} z={span_z:.4f}; skipping")
                        continue
                    marker_positions[marker_id] = {
                        'x': sum(xs) / len(xs),
                        'y': sum(ys) / len(ys),
                        'z': sum(zs) / len(zs)
                    }

                if not marker_positions:
                    self._call_ui(self._update_status, "Detections inconsistent; retrying scan.")
                    time.sleep(1.0)
                    continue

                # Record the gantry position(s) where each marker was observed
                recorded_gantry_positions = {mid: self.control_board.positions.copy() for mid in marker_positions.keys()}

                self._call_ui(self._update_status, "Verifying calibration...")

                verified_results = {}

                for marker_id, rel_pos in marker_positions.items():
                    if self._cancel_requested:
                        break

                    # Safety limits and verification tuning
                    tolerance_mm = 10.0
                    consecutive_successes = 0
                    attempts = 0
                    max_attempts = 20

                    recorded_gantry = recorded_gantry_positions.get(marker_id, self.control_board.positions.copy())

                    self.logger.info(f"Verifying Marker {marker_id} (relative camera pos x={rel_pos['x']:.3f} y={rel_pos['y']:.3f} z={rel_pos['z']:.3f}); recorded gantry {recorded_gantry}")

                    while consecutive_successes < 3 and attempts < max_attempts and not self._cancel_requested:
                        attempts += 1
                        self._call_ui(self._update_status, f"Attempt {attempts}: Homing and verifying Marker {marker_id}...")

                        # Home the gantry (use toolhead if available for safer homing)
                        try:
                            if hasattr(self.dispatcher, 'toolhead') and self.dispatcher.toolhead is not None:
                                self.dispatcher.toolhead.home()
                            else:
                                self.control_board.send_message("G28", require_lock=True)
                                self.control_board.finish_moves()
                        except Exception as e:
                            self.logger.exception(f"Failed to home gantry on attempt {attempts} for Marker {marker_id}: {e}")
                            time.sleep(0.3)
                            consecutive_successes = 0
                            continue

                        # Move to the recorded gantry position and ensure the move finished
                        try:
                            target = recorded_gantry
                            self.logger.debug(f"Moving to recorded gantry pos for Marker {marker_id}: {target}")
                            if hasattr(self.dispatcher, 'toolhead') and self.dispatcher.toolhead is not None:
                                self.dispatcher.toolhead.move_to(x=target['X'], y=target['Y'], z=target['Z'], relative=False, feedrate=2000, coordinated=True)
                            else:
                                self.control_board.move_axis('Z', target['Z'], feedrate_mm_per_minute=600)
                                self.control_board.move_axis('X', target['X'], feedrate_mm_per_minute=2000)
                                self.control_board.move_axis('Y', target['Y'], feedrate_mm_per_minute=2000)
                            # Request position update to refresh `self.control_board.positions`
                            try:
                                self.control_board.request_position()
                            except Exception:
                                pass
                        except Exception as e:
                            self.logger.exception(f"Failed to move to recorded gantry pos for Marker {marker_id} on attempt {attempts}: {e}")
                            consecutive_successes = 0
                            time.sleep(0.3)
                            continue

                        # Longer settle to allow mechanical vibration to die out
                        time.sleep(0.6)

                        # Now scan briefly for the marker at the moved position using
                        # the UI-updated frame buffer (avoid direct VideoCapture reads).
                        scan_start = time.time()
                        detections = []
                        scan_timeout = 2.0
                        while time.time() - scan_start < scan_timeout and not self._cancel_requested:
                            with self._frame_lock:
                                frame = None if self._last_frame is None else self._last_frame.copy()
                            if frame is None:
                                time.sleep(0.02)
                                continue
                            result = self.aruco_detector.detect_markers(frame)
                            # Show annotated frame during verification
                            if result and 'frame' in result:
                                self._call_ui(self._show_frame_on_ui, result['frame'])
                            for m in result['markers']:
                                if m['id'] == marker_id:
                                    detections.append(m['position'])
                            time.sleep(0.02)

                        if not detections:
                            self.logger.warning(f"Marker {marker_id} not detected on attempt {attempts}")
                            consecutive_successes = 0
                            continue

                        # Average detections
                        avg_rel = {
                            'x': sum(p['x'] for p in detections) / len(detections),
                            'y': sum(p['y'] for p in detections) / len(detections),
                            'z': sum(p['z'] for p in detections) / len(detections)
                        }

                        dx = abs((avg_rel['x'] - rel_pos['x']) * 1000)
                        dy = abs((avg_rel['y'] - rel_pos['y']) * 1000)
                        dz = abs((avg_rel['z'] - rel_pos['z']) * 1000)

                        self.logger.debug(f"Marker {marker_id} attempt {attempts}: relative delta(mm) dx={dx:.2f}, dy={dy:.2f}, dz={dz:.2f}")

                        if dx <= tolerance_mm and dy <= tolerance_mm and dz <= tolerance_mm:
                            consecutive_successes += 1
                            self.logger.info(f"Marker {marker_id} verification success {consecutive_successes}/3 (attempt {attempts})")
                        else:
                            consecutive_successes = 0
                            self.logger.info(f"Marker {marker_id} verification failed on attempt {attempts}: dx={dx:.2f} dy={dy:.2f} dz={dz:.2f}")

                        # Small delay to allow UI to update if needed
                        time.sleep(0.1)

                    # End attempts for this marker
                    if consecutive_successes >= 3:
                        abs_aruco_position = {
                            'x': recorded_gantry['X'] + rel_pos['x'] * 1000,
                            'y': recorded_gantry['Y'] + rel_pos['y'] * 1000,
                            'z': recorded_gantry['Z'] + rel_pos['z'] * 1000
                        }

                        verified_results[marker_id] = {
                            'relative_positions': [marker_positions[marker_id]],
                            'abs_aruco_position': abs_aruco_position,
                            'verification_count': consecutive_successes,
                            'gantry_reference': recorded_gantry,
                            'verification_average': {'x': avg_rel['x'], 'y': avg_rel['y'], 'z': avg_rel['z']},
                            'detection_variance': {}
                        }
                        self.logger.info(f"Marker {marker_id} calibration verified after {attempts} attempts")
                    else:
                        self.logger.warning(f"Marker {marker_id} verification unsuccessful after {attempts} attempts")

                if self._cancel_requested:
                    break

                if not verified_results:
                    self._call_ui(self._update_status, "No verified markers, retrying scan.")
                    time.sleep(1.0)
                    continue

                # Save to pending calibrations and update UI on the main thread
                def _finish_save():
                    self.pending_calibrations.update(verified_results)
                    self._update_status(f"Calibration complete: {len(verified_results)} marker(s) pending save.")
                    self._update_ui()

                self._call_ui(_finish_save)
                return

            if self._cancel_requested:
                self._call_ui(self._update_status, "Calibration cancelled by user")

        except Exception as e:
            self.logger.error(f"Calibration error: {e}")
            self._call_ui(self._update_status, f"Error: {e}")
        finally:
            self._call_ui(self._reset_calibration)
    
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
    
    def _clear_pending_calibrations(self):
        """Clear all pending calibrations"""
        if self.pending_calibrations:
            self.pending_calibrations.clear()
            self._update_ui()
            self._update_status("Cleared all pending calibrations")
        else:
            self._update_status("No pending calibrations to clear")
    
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

    def _call_ui(self, func, *args, **kwargs):
        """Schedule a UI call on the main thread via `after`."""
        try:
            # Use camera_display widget to schedule on mainloop
            self.camera_display.after(0, lambda: func(*args, **kwargs))
        except Exception:
            try:
                func(*args, **kwargs)
            except Exception:
                pass
    
    def _delete_marker(self, marker_id: int, is_pending: bool):
        """Delete a specific marker calibration"""
        if is_pending:
            if marker_id in self.pending_calibrations:
                del self.pending_calibrations[marker_id]
                self._update_ui()
                self._update_status(f"Deleted pending calibration for Marker {marker_id}")
            else:
                self._update_status(f"Marker ID {marker_id} not found in pending calibrations")
        else:
            if marker_id in self.calibration_data:
                del self.calibration_data[marker_id]
                self._save_calibration_data()
                self._update_ui()
                self._update_status(f"Deleted saved calibration for Marker {marker_id}")
            else:
                self._update_status(f"Marker ID {marker_id} not found in saved calibrations")
    
    def _create_marker_frame(self, marker_id: int, data: dict, is_pending: bool):
        """Create a frame for a single marker in the scrollable list"""
        frame = ctk.CTkFrame(self.positions_listbox, fg_color="#2B2B2B" if is_pending else "#1F1F1F")
        frame.pack(fill="x", padx=5, pady=2)

        # Marker ID
        id_label = ctk.CTkLabel(frame, text=f"ID: {marker_id}", font=("Arial", 15, "bold"), text_color = "#FFFFFF")
        id_label.pack(side = "left", padx=5, pady=2)

        # Position data (store/display the aruco absolute position only;
        # this is the location of the ARuCo marker in gantry coords)
        abs_pos = data.get('abs_aruco_position') or data.get('absolute_position') or {'x': 0, 'y': 0, 'z': 0}
        pos_text = f"X: {abs_pos['x']:.2f}mm  Y: {abs_pos['y']:.2f}mm  Z: {abs_pos['z']:.2f}mm"
        pos_label = ctk.CTkLabel(frame, text=pos_text, font=("Arial", 15), text_color = "#4BD5ED")
        pos_label.pack(side = "left", padx=5, pady=2)

        # Delete button
        delete_btn = ctk.CTkButton(
            frame,
            text="Delete",
            command=lambda: self._delete_marker(marker_id, is_pending),
            fg_color="#C62828",
            hover_color="#880E4F",
            width=60,
            height=25
        )
        delete_btn.pack(side = "right", padx=5, pady=5)
    
    def _update_ui(self):
        """Update the UI displays"""
        # Update detected markers display (pending calibrations)
        if self.pending_calibrations:
            text = "Pending (Newly Calibrated) Markers:\n"
            for marker_id, data in self.pending_calibrations.items():
                abs_pos = data.get('abs_aruco_position') or data.get('absolute_position') or {'x': 0, 'y': 0, 'z': 0}
                text += f"Marker ID {marker_id}: X={abs_pos['x']:.2f}, Y={abs_pos['y']:.2f}, Z={abs_pos['z']:.2f}\n"
        else:
            text = "No newly calibrated markers. Start a scan to detect markers."
        self.markers_display.configure(text=text)

        # Clear the scrollable frame
        for widget in self.positions_listbox.winfo_children():
            widget.destroy()

        # Add saved calibrations
        if self.calibration_data:
            saved_label = ctk.CTkLabel(self.positions_listbox, text="Saved (Permanent) Calibrations", font=("Arial", 14, "bold"))
            saved_label.pack(pady=(0, 5))

            for marker_id, data in self.calibration_data.items():
                self._create_marker_frame(marker_id, data, is_pending=False)

        # Add pending calibrations
        if self.pending_calibrations:
            pending_label = ctk.CTkLabel(self.positions_listbox, text="Pending (Unsaved) Calibrations", font=("Arial", 14, "bold"))
            pending_label.pack(pady=(10, 5) if self.calibration_data else (0, 5))

            for marker_id, data in self.pending_calibrations.items():
                self._create_marker_frame(marker_id, data, is_pending=True)

        if not self.calibration_data and not self.pending_calibrations:
            no_data_label = ctk.CTkLabel(self.positions_listbox, text="No saved or pending calibrations yet.")
            no_data_label.pack(pady=10)

        # Enable/disable management buttons
        has_pending = len(self.pending_calibrations) > 0
        has_any = has_pending or len(self.calibration_data) > 0

        self.save_button.configure(state="normal" if has_pending else "disabled")
        self.delete_button.configure(state="normal" if has_pending else "disabled")
    
    def _load_calibration_data(self):
        """Load calibration data from file"""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    self.calibration_data = json.load(f)
                    # Convert string keys back to integers
                    self.calibration_data = {int(k): v for k, v in self.calibration_data.items()}
                    # Migrate legacy keys: 'absolute_position' -> 'abs_aruco_position'
                    for k, v in list(self.calibration_data.items()):
                        if isinstance(v, dict) and 'absolute_position' in v and 'abs_aruco_position' not in v:
                            v['abs_aruco_position'] = v.pop('absolute_position')
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
