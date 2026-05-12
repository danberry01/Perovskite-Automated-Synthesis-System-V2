
import cv2
import cv2.aruco as aruco
import numpy as np
import logging
import os


class ArucoDetector:

    def __init__(
        self, 
        calibration_file: str = "gui/components/calibration_data.npz",
        marker_length: float = 0.05,
        dictionary: int = aruco.DICT_4X4_50,
        frame_width: int = 600,
        frame_height: int = 400
    ):

        self.logger = logging.getLogger("Main Logger")
        
        self.marker_length = marker_length
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Load calibration data
        self.camera_matrix, self.dist_coeffs = self._load_calibration(calibration_file)
        
        # Setup ArUco detector
        self.aruco_dict = aruco.getPredefinedDictionary(dictionary)
        self.aruco_params = aruco.DetectorParameters()
        self.aruco_detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        self.logger.debug(f"ArucoDetector initialized with {marker_length}m markers")
    
    def _load_calibration(self, calibration_file: str):

        try:
            if not os.path.exists(calibration_file):

                raise FileNotFoundError(f"Calibration file not found: {calibration_file}")
            
            data = np.load(calibration_file)
            camera_matrix = data["camera_matrix"]
            dist_coeffs = data["dist_coeffs"]
            
            self.logger.debug(f"Loaded calibration from {calibration_file}")
            return camera_matrix, dist_coeffs
            
        except Exception as e:
            self.logger.error(f"Failed to load calibration: {e}")
            raise
    
    def detect_markers(self, frame: np.ndarray):

        # Converts the picture to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Scale down for faster detection
        scale_percent = 0.5
        small_gray = cv2.resize(gray_frame, (0, 0), fx=scale_percent, fy=scale_percent)
        
        # Detect markers
        corners, ids, rejected = cv2.aruco.detectMarkers(
            small_gray,
            self.aruco_dict,
            parameters=self.aruco_params
        )
        
        result_frame = frame.copy()
        markers = []
        
        if ids is not None:
            # Scale corners back to original size
            corners = list(corners)
            for i in range(len(corners)):
                corners[i] = corners[i] / scale_percent
            
            # Estimates 3D pose for each marker
            rotation_vectors, translation_vectors, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners,
                self.marker_length,
                self.camera_matrix,
                self.dist_coeffs
            )
            
            # Processes each detected marker
            for i in range(len(ids)):

                marker_id = ids[i][0]
                corner = corners[i].astype(int)
                rot_vec = rotation_vectors[i]
                trans_vec = translation_vectors[i]
                
                # Extract the position
                x = trans_vec[0][0]
                y = trans_vec[0][1]
                z = trans_vec[0][2]
                
                # This actually makes the visual part you see
                self._draw_marker_visualization(
                    result_frame, corner, rot_vec, trans_vec, marker_id, i
                )
                
                # Store marker info
                markers.append({
                    'id': marker_id,
                    'corners': corner,
                    'position': {'x': x, 'y': y, 'z': z},
                    'rotation_vector': rot_vec,
                    'translation_vector': trans_vec
                })
        
        return {
            'frame': result_frame,
            'markers': markers,
            'count': len(markers)
        }
    
    def _draw_marker_visualization(
        self, 
        frame: np.ndarray, 
        corners: np.ndarray, 
        rot_vec: np.ndarray, 
        trans_vec: np.ndarray, 
        marker_id: int, 
        index: int
    ):

        # Draw marker border
        cv2.polylines(frame, [corners], True, (0, 255, 0), 2)
        
        # Draw 3D axis
        cv2.drawFrameAxes(
            frame,
            self.camera_matrix,
            self.dist_coeffs,
            rot_vec,
            trans_vec,
            self.marker_length * 0.5
        )
        
        # Extract position
        x = trans_vec[0][0]
        y = trans_vec[0][1]
        z = trans_vec[0][2]
        
        # Draws text ID. seperating the blocks is just for visual organization, no real reason to do it this way.
        cv2.putText(

            frame,
            f"ID: {marker_id}",
            org=(10, 40 + index * 60),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.7,
            color=(0, 195, 255),  # Cyan (BGR)
            thickness=2
        )
        
        # Draw position text
        cv2.putText(

            frame,
            f"X: {x:.3f}m  Y: {y:.3f}m  Z: {z:.3f}m",
            org=(10, 65 + index * 60),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.7,
            color=(0, 255, 0),  # Green (BGR)
            thickness=2

        )
    
    def get_marker_positions(self, markers: list) -> dict:

        positions = {}
        for marker in markers:
            positions[int(marker['id'])] = marker['position']
        return positions
    

    def log_detection_results(self, result: dict):

        # CAMERA level is DEBUG - 1 (defined in main.py)
        CAMERA_LEVEL = logging.DEBUG - 1
        

        if result['count'] == 0:
            self.logger.log(CAMERA_LEVEL, "No markers detected")
        else:
            
            self.logger.log(CAMERA_LEVEL, f"Detected {result['count']} marker(s)")
            for marker in result['markers']:
                pos = marker['position']
                self.logger.log(
                    CAMERA_LEVEL,
                    f"  Marker {int(marker['id'])}: X={pos['x']:.3f}m, "
                    f"Y={pos['y']:.3f}m, Z={pos['z']:.3f}m"
                )
