import customtkinter as ctk
import cv2
import cv2.aruco as aruco
import numpy as np
from PIL import Image, ImageTk
from ..components.constants import *

class CameraFrame(ctk.CTkFrame):
    """Frame for displaying camera feed with coordinate projection, and filter buttons"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color = FOREGROUND_COLOR)
        
        # Geometry data for what the pose detector expects
        self.data = np.load("gui/components/calibration_data.npz")
        self.camera_matrix = self.data["camera_matrix"]
        self.dist_coeffs = self.data["dist_coeffs"] 
        self.marker_length = 0.05  # 50 mm (this can be changed if you know the size of your markers)
        self.width, self.height = 600, 400 #For camera Resolution

        # Defines the dictionary the program expects a code to come from, and initailizes the detector
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        self.aruco_params = aruco.DetectorParameters()
        self.aruco_detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        #openCV video capture setup
        self.myVideoCapture = cv2.VideoCapture(0)
        if not self.myVideoCapture.isOpened():
            raise Exception("Can not connect to camera")

        self.myVideoCapture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.myVideoCapture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        #initialize qrcode detection
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        self.aruco_params = aruco.DetectorParameters()
        self.aruco_detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

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

    def hex_to_rgb(self, hex_code):
        hex_code = hex_code.lstrip('#')
        # Use a list comprehension to split the hex code into 2-character chunks,
        # convert each chunk to an integer base 16, and then convert the result to a tuple.
        return tuple(int(hex_code[i:i+2], 16) for i in range(0, len(hex_code), 2))

    # put this somewhere else later
    # Defines the function to open the camera and process the frames continuously
    def update_video_feed(self):

        # Reads one frame from the camera
        ret, frame = self.myVideoCapture.read()

        # Tells the function to rerun in 10ms if a frame is not detected (ret is a bool to determine if the frame was captured correctly)
        if not ret:
            self.myVideoWidget.after(10, self.update_video_feed)
            return

        # Converts the frame to grayscale
        grayFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        scale_percent = 0.5  # Scale down to 50%
        small_gray = cv2.resize(grayFrame, (0,0), fx=scale_percent, fy=scale_percent)

        # Detect ArUco markers from the grayscale frame
        corners, ids, rejected = cv2.aruco.detectMarkers(
            small_gray,
            self.aruco_dict,
            parameters=self.aruco_params
        )

        # Checks if an ID has been detected
        if ids is not None:
            
            corners = list(corners)
            for i in range(len(corners)):
                corners[i] = corners[i] / scale_percent
            # Estimate 3D pose of each marker with data from marker detection
            rotationVectors, translationVectors, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners,
                self.marker_length,
                self.camera_matrix,
                self.dist_coeffs
            )

            # Checks for each valid ID that can be detected
            for i in range(len(ids)):

                # Draw marker border for axis
                cv2.polylines(
                    frame,
                    [corners[i].astype(int)],
                    True,
                    (0, 255, 0),
                    2
                )

                # Draw 3D axis
                cv2.drawFrameAxes(
                    frame,
                    self.camera_matrix,
                    self.dist_coeffs,
                    rotationVectors[i],
                    translationVectors[i],
                    self.marker_length * 0.5
                )

                # Extract translation values (meters)
                x = translationVectors[i][0][0]
                y = translationVectors[i][0][1]
                z = translationVectors[i][0][2]
                marker_id = ids[i][0]

                # Display marker ID on the frame (info bar top left corner), 
                cv2.putText(
                    frame,
                    f"ID: {marker_id}",
                    org = (10, 40 + i * 60), #multiply y axis by index*60 so multiple markers dont overlap
                    fontFace = cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale = 0.7,
                    color = self.hex_to_rgb("#00C3FF"),
                    thickness = 2
                )

                # Display 3D position on frame (info bar top left corner)
                cv2.putText(
                    frame,
                    f"X: {x:.3f}m  Y: {y:.3f}m  Z: {z:.3f}m", # {coordinate:(decimal)(num type)}
                    org = (10, 65 + i * 60),
                    fontFace = cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale = 0.7,
                    color = self.hex_to_rgb("#00FF00"),
                    thickness = 2
                )

                print(f"Marker {marker_id} → X:{x:.3f}  Y:{y:.3f}  Z:{z:.3f}") # Console Display of ID and coords

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

        self.myVideoWidget.after(20, self.update_video_feed)