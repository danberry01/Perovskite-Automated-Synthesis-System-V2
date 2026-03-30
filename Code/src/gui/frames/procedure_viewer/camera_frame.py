import customtkinter as ctk
import cv2
import logging
from PIL import Image, ImageTk
from ...components.constants import *
from ...drivers.aruco_detector_driver import ArucoDetector

class CameraFrame(ctk.CTkFrame):
    """Frame for displaying camera feed with ArUco marker detection and annotation"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR, corner_radius = 0)
        
        self.logger = logging.getLogger("Main Logger")
        
        # Video feed update tracking
        self._video_feed_after_id = None
        self._is_paused = False

        # Camera resolution
        self.width, self.height = 600, 400

        # Initialize ArUco detector driver
        try:
            self.aruco_detector = ArucoDetector(
                calibration_file="gui/components/calibration_data.npz",
                marker_length=0.05,  # 50 mm
                frame_width=self.width,
                frame_height=self.height
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize ArUco detector: {e}")
            raise

        # OpenCV video capture setup
        self.myVideoCapture = cv2.VideoCapture(0)
        if not self.myVideoCapture.isOpened():
            raise Exception("Can not connect to camera")

        self.myVideoCapture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.myVideoCapture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        #CustomTKinter widgets (just the camera and button)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.myVideoWidget = ctk.CTkLabel(
            master = self,
            width= self.width,
            height= self.height,
            bg_color="#000000",
            text = "",
            corner_radius = 0
        )
        self.myVideoWidget.grid(row=0,column=0, padx = 5, pady = 5, sticky = "nsew")

        self.openCameraButton = ctk.CTkButton(
            master = self, 
            text="Open Camera", 
            command=self.update_video_feed,
            corner_radius = 0,
            fg_color = FOREGROUND_COLOR

        )
        
        self.openCameraButton.grid(row=0,column=0, padx = 10, pady = 10, sticky = "s")

    # Update video feed - now uses the ArUco detector driver
    def update_video_feed(self):
        
        # Check if paused - don't process frames but keep the loop scheduled
        if self._is_paused:
            self._video_feed_after_id = self.myVideoWidget.after(20, self.update_video_feed)
            return

        # Reads one frame from the camera
        ret, frame = self.myVideoCapture.read()

        # Tells the function to rerun in 10ms if a frame is not detected
        if not ret:
            self._video_feed_after_id = self.myVideoWidget.after(10, self.update_video_feed)
            return

        # Process frame with ArUco detector driver
        result = self.aruco_detector.detect_markers(frame)
        frame = result['frame']
        
        # Log detection results
        if result['count'] > 0:
            self.aruco_detector.log_detection_results(result)

        # Convert for Tkinter display
        # Convert BGR → RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        captured_image = Image.fromarray(frame_rgb)

        # Converts captured_image to ctkImage format
        ctk_image = ctk.CTkImage(
            light_image=captured_image,
            dark_image=captured_image,
            size=(self.width, self.height)
        )

        # Updates current frame of tkinter widget
        self.myVideoWidget.configure(image=ctk_image)
        self.myVideoWidget.image = ctk_image  # prevent garbage collection

        self._video_feed_after_id = self.myVideoWidget.after(20, self.update_video_feed)

    def pause_video_feed(self):
        """Pause the video feed processing to reduce CPU usage"""
        self._is_paused = True

    def resume_video_feed(self):
        """Resume the video feed processing"""
        self._is_paused = False
        if self._video_feed_after_id is None:
            self.update_video_feed()
