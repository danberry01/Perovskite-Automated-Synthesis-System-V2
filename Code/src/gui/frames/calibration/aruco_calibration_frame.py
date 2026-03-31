import customtkinter as ctk
import threading
import logging
from typing import Dict, List, Tuple
import json
import os

from ...components.constants import *
from drivers.aruco_detector_driver import ArucoDetector
from drivers.controlboard_driver import ControlBoard


class ArucoCalibrationFrame(ctk.CTkFrame):
    """Frame for calibrating ArUco marker positions in absolute coordinate system"""
    
    def __init__(self, master, dispatcher, **kwargs):
        super().__init__(master, fg_color=FOREGROUND_COLOR, corner_radius=0)
        
        self.logger = logging.getLogger("Main Logger")
        self.dispatcher = dispatcher
        self.control_board: ControlBoard = dispatcher.control_board
        
        # ArUco detector
        self.aruco_detector = ArucoDetector(
            calibration_file="gui/components/calibration_data.npz",
            marker_length=0.05,
            frame_width=600,
            frame_height=400
        )
        
        # Calibration data storage
        self.calibration_data: Dict[int, Dict] = {}  # marker_id -> {'positions': [...], 'absolute_pos': {...}}
        self.calibration_file = "calibration_data/aruco_calibrations.json"
        self._load_calibration_data()
        
        # State tracking
        self._is_paused = False
        self._calibration_in_progress = False
        self._verification_results: List[Tuple[float, float, float]] = []
        
        # Setup UI
        self._setup_ui()
        self._load_calibration_data()
    
    def _setup_ui(self):
        """Setup the user interface"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkLabel(
            self,
            text="ArUco Marker Position Calibration",
            font=("Arial", 18, "bold")
        )
        header.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Main content area
        main_container = ctk.CTkFrame(self, fg_color=FOREGROUND_COLOR)
        main_container.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # Left side: Camera feed and controls
        left_panel = ctk.CTkFrame(main_container, fg_color=FOREGROUND_COLOR)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_panel.columnconfigure(0, weight=1)
        
        # Camera feed
        camera_label = ctk.CTkLabel(left_panel, text="Camera Feed", font=("Arial", 12, "bold"))
        camera_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.camera_display = ctk.CTkLabel(
            left_panel,
            width=600,
            height=400,
            bg_color="#000000",
            text="",
            corner_radius=0
        )
        self.camera_display.grid(row=1, column=0, padx=5, pady=5)
        
        # Status display
        status_frame = ctk.CTkFrame(left_panel, fg_color=FOREGROUND_COLOR_TWO)
        status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        status_frame.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(status_frame, text="Status:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=3)
        self.status_label = ctk.CTkLabel(status_frame, text="Ready", font=("Arial", 10))
        self.status_label.grid(row=0, column=1, padx=5, pady=3, sticky="w")
        
        # Gantry position display
        position_frame = ctk.CTkFrame(left_panel, fg_color=FOREGROUND_COLOR_TWO)
        position_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        position_frame.columnconfigure(0, weight=1)
        
        positions_text = "Gantry Position: X={:.2f}mm Y={:.2f}mm Z={:.2f}mm"
        self.position_label = ctk.CTkLabel(
            position_frame,
            text=positions_text.format(0, 0, 0),
            font=("Arial", 9),
            justify="left"
        )
        self.position_label.grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        
        # Right side: Controls and list
        right_panel = ctk.CTkFrame(main_container, fg_color=FOREGROUND_COLOR)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(3, weight=1)
        
        # Calibration controls
        controls_label = ctk.CTkLabel(right_panel, text="Calibration Controls", font=("Arial", 12, "bold"))
        controls_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        button_frame = ctk.CTkFrame(right_panel, fg_color=FOREGROUND_COLOR)
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        self.scan_button = ctk.CTkButton(
            button_frame,
            text="Start Calibration Scan",
            command=self._start_calibration_scan,
            fg_color="#2E7D32",
            hover_color="#1B5E20"
        )
        self.scan_button.grid(row=0, column=0, sticky="ew", padx=2, pady=5)
        
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel_calibration,
            fg_color="#C62828",
            hover_color="#880E4F",
            state="disabled"
        )
        self.cancel_button.grid(row=0, column=1, sticky="ew", padx=2, pady=5)
        
        self.home_button = ctk.CTkButton(
            button_frame,
            text="Home Gantry",
            command=self._home_gantry,
            fg_color="#1565C0",
            hover_color="#0D47A1"
        )
        self.home_button.grid(row=1, column=0, sticky="ew", padx=2, pady=5)
        
        self.refresh_position_button = ctk.CTkButton(
            button_frame,
            text="Refresh Position",
            command=self._refresh_position,
            fg_color="#616161",
            hover_color="#424242"
        )
        self.refresh_position_button.grid(row=1, column=1, sticky="ew", padx=2, pady=5)
        
        # Detected markers section
        markers_label = ctk.CTkLabel(right_panel, text="Detected Markers", font=("Arial", 12, "bold"))
        markers_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(10, 5))
        
        self.markers_display = ctk.CTkTextbox(
            right_panel,
            width=280,
            height=150,
            font=("Courier", 9),
            state="disabled"
        )
        self.markers_display.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        
        # Calibrated positions section
        positions_label = ctk.CTkLabel(right_panel, text="Calibrated Positions", font=("Arial", 12, "bold"))
        positions_label.grid(row=4, column=0, sticky="ew", padx=5, pady=(10, 5))
        
        self.positions_listbox = ctk.CTkTextbox(
            right_panel,
            width=280,
            height=150,
            font=("Courier", 9),
            state="disabled"
        )
        self.positions_listbox.grid(row=5, column=0, sticky="nsew", padx=5, pady=5)
        
        # Position management buttons
        management_frame = ctk.CTkFrame(right_panel, fg_color=FOREGROUND_COLOR)
        management_frame.grid(row=6, column=0, sticky="ew", padx=5, pady=5)
        management_frame.columnconfigure(0, weight=1)
        management_frame.columnconfigure(1, weight=1)
        
        self.save_button = ctk.CTkButton(
            management_frame,
            text="Save Selected",
            command=self._save_selected_position,
            fg_color="#00897B",
            hover_color="#004D40",
            state="disabled"
        )
        self.save_button.grid(row=0, column=0, sticky="ew", padx=2, pady=5)
        
        self.delete_button = ctk.CTkButton(
            management_frame,
            text="Delete Selected",
            command=self._delete_selected_position,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            state="disabled"
        )
        self.delete_button.grid(row=0, column=1, sticky="ew", padx=2, pady=5)
        
        self.clear_all_button = ctk.CTkButton(
            management_frame,
            text="Clear All",
            command=self._clear_all_calibrations,
            fg_color="#F57F17",
            hover_color="#E65100"
        )
        self.clear_all_button.grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=5)
    
    def _start_calibration_scan(self):
        """Start the calibration scanning process in a background thread"""
        if self._calibration_in_progress:
            self.logger.warning("Calibration already in progress")
            return
        
        self.scan_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self._calibration_in_progress = True
        
        # Run calibration in background thread
        calibration_thread = threading.Thread(target=self._calibration_worker, daemon=True)
        calibration_thread.start()
    
    def _calibration_worker(self):
        """Background worker for calibration process"""
        try:
            self._update_status("Scanning for markers...")
            
            # Wait for camera to capture frames
            import cv2
            import time
            import numpy as np
            
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 600)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 400)
            
            # Scan for markers (collect frames over 2 seconds)
            start_time = time.time()
            detected_markers = {}
            
            while time.time() - start_time < 2.0:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                result = self.aruco_detector.detect_markers(frame)
                
                for marker in result['markers']:
                    marker_id = marker['id']
                    if marker_id not in detected_markers:
                        detected_markers[marker_id] = []
                    detected_markers[marker_id].append(marker['position'])
            
            cap.release()
            
            if not detected_markers:
                self._update_status("No markers detected!")
                self.logger.warning("No ArUco markers detected during calibration")
                self._reset_calibration()
                return
            
            # Average the detections for each marker
            marker_positions = {}
            for marker_id, positions in detected_markers.items():
                if positions:
                    avg_x = sum(p['x'] for p in positions) / len(positions)
                    avg_y = sum(p['y'] for p in positions) / len(positions)
                    avg_z = sum(p['z'] for p in positions) / len(positions)
                    marker_positions[marker_id] = {'x': avg_x, 'y': avg_y, 'z': avg_z}
            
            # Get current gantry position
            gantry_pos = self.control_board.positions.copy()
            
            # Calculate absolute positions (relative marker pos + gantry pos)
            absolute_positions = {}
            for marker_id, rel_pos in marker_positions.items():
                abs_pos = {
                    'x': gantry_pos['X'] + rel_pos['x'] * 1000,  # Convert to mm
                    'y': gantry_pos['Y'] + rel_pos['y'] * 1000,
                    'z': gantry_pos['Z'] + rel_pos['z'] * 1000
                }
                absolute_positions[marker_id] = abs_pos
            
            # Verify position accuracy by moving to the detected position 3 times
            self._update_status("Verifying calibration...")
            
            for marker_id, abs_pos in absolute_positions.items():
                self._verification_results = []
                
                for attempt in range(3):
                    self._update_status(f"Verification {attempt + 1}/3 for Marker {marker_id}...")
                    
                    # Home the gantry first
                    self.logger.debug(f"Homing gantry for verification attempt {attempt + 1}")
                    self.control_board.send_message("G28")  # Home command
                    self.control_board.finish_moves()
                    time.sleep(0.5)
                    
                    # Move to the detected position
                    self.logger.debug(f"Moving to calibrated position: X={abs_pos['x']:.2f} Y={abs_pos['y']:.2f} Z={abs_pos['z']:.2f}")
                    self.control_board.move_axis('X', abs_pos['x'], feedrate_mm_per_minute=2000)
                    self.control_board.move_axis('Y', abs_pos['y'], feedrate_mm_per_minute=2000)
                    self.control_board.move_axis('Z', abs_pos['z'], feedrate_mm_per_minute=600)
                    
                    time.sleep(0.5)
                    
                    # Scan for markers at this position
                    cap = cv2.VideoCapture(0)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 600)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 400)
                    
                    scan_start = time.time()
                    while time.time() - scan_start < 1.0:
                        ret, frame = cap.read()
                        if not ret:
                            continue
                        
                        result = self.aruco_detector.detect_markers(frame)
                        for marker in result['markers']:
                            if marker['id'] == marker_id:
                                self._verification_results.append(marker['position'])
                    
                    cap.release()
                
                # Check if results are consistent (3/4 same = at least 2 detections out of 3 attempts)
                if len(self._verification_results) < 2:
                    self._update_status(f"Failed to verify Marker {marker_id} - retrying...")
                    # Keep trying until we get consistent results
                    continue
                
                # Calculate average of all verification results
                avg_result = {
                    'x': sum(p['x'] for p in self._verification_results) / len(self._verification_results),
                    'y': sum(p['y'] for p in self._verification_results) / len(self._verification_results),
                    'z': sum(p['z'] for p in self._verification_results) / len(self._verification_results)
                }
                
                # Store the calibration
                self.calibration_data[marker_id] = {
                    'relative_positions': [marker_positions[marker_id]],
                    'absolute_position': abs_pos,
                    'verification_count': len(self._verification_results),
                    'gantry_reference': gantry_pos
                }
                
                self.logger.info(f"Calibrated Marker {marker_id} at absolute position: X={abs_pos['x']:.2f} Y={abs_pos['y']:.2f} Z={abs_pos['z']:.2f}")
            
            self._update_status("Calibration complete!")
            self._update_ui()
            
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
        self._reset_calibration()
        self._update_status("Calibration cancelled")
    
    def _reset_calibration(self):
        """Reset calibration UI state"""
        self._calibration_in_progress = False
        self.scan_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
    
    def _save_selected_position(self):
        """Save a selected calibrated position"""
        # This will be implemented to save to file
        self._save_calibration_data()
        self._update_status("Calibration saved")
    
    def _delete_selected_position(self):
        """Delete a selected calibration"""
        # Get selected text from listbox
        selected = self.positions_listbox.selection_get()
        if selected:
            # Parse marker ID from selected text
            try:
                marker_id = int(selected.split("ID:")[1].split()[0])
                if marker_id in self.calibration_data:
                    del self.calibration_data[marker_id]
                    self._save_calibration_data()
                    self._update_ui()
                    self._update_status(f"Deleted calibration for Marker {marker_id}")
            except:
                self.logger.warning("Could not parse marker ID from selection")
    
    def _clear_all_calibrations(self):
        """Clear all calibrated positions"""
        self.calibration_data.clear()
        self._save_calibration_data()
        self._update_ui()
        self._update_status("All calibrations cleared")
    
    def _update_status(self, status: str):
        """Update the status label"""
        self.status_label.configure(text=status)
        self.logger.debug(f"[Calibration] {status}")
    
    def _update_ui(self):
        """Update the UI displays"""
        # Update calibrated positions list
        self.positions_listbox.configure(state="normal")
        self.positions_listbox.delete("1.0", "end")
        
        for marker_id, data in self.calibration_data.items():
            abs_pos = data['absolute_position']
            text = f"Marker ID: {marker_id}\n  X: {abs_pos['x']:.2f}mm\n  Y: {abs_pos['y']:.2f}mm\n  Z: {abs_pos['z']:.2f}mm\n\n"
            self.positions_listbox.insert("end", text)
        
        self.positions_listbox.configure(state="disabled")
        
        # Enable/disable management buttons
        has_calibrations = len(self.calibration_data) > 0
        self.save_button.configure(state="normal" if has_calibrations else "disabled")
        self.delete_button.configure(state="normal" if has_calibrations else "disabled")
    
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
