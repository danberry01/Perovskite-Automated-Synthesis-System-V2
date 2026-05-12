import threading
import logging
from time import sleep
import cv2
import customtkinter as ctk


class Camera(threading.Thread):
    def __init__(self):
        super().__init__(name="Camera",daemon=True)

        self.logger = logging.getLogger("Main Logger")

        self.video_capture = None
        self.frame = None
        self._frame_lock = threading.Lock()

        self.running = threading.Event()
        self.release = threading.Event()
        self._preferred_width = None
        self._preferred_height = None
        self.start()
        

    def connect(self, device_index: int = 0, width: int = None, height: int = None):

        if self.is_connected():

            self.logger.error("Camera is already connected")
            return False

        try:
            self.video_capture = cv2.VideoCapture(device_index)
            if not self.video_capture.isOpened():

                self.logger.error(f"Failed to open VideoCapture({device_index})")
                self.video_capture = None
                return False

            if width is not None and height is not None:

                self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
                self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))

            elif self._preferred_width and self._preferred_height:
                self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(self._preferred_width))
                self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self._preferred_height))

            self.running.set()
            self.logger.debug("Connected to camera")
            return True
        except cv2.error as e:
            self.logger.error(f"Error connecting to camera: {e}")
            return False
            
            
    def disconnect(self):
        if not self.is_connected():
            return
        self.running.clear()
        self.release.set()
        self.logger.debug("Camera stopped")
    
    

    def run(self):
        while True:
            self.running.wait()
            self.release.clear()
   
            while self.is_connected():
                sleep(0.0)
                try:
                    ret, frame = self.video_capture.read()
                    if ret is True:
                        try:
                            with self._frame_lock:
                                self.frame = frame.copy()
                        except Exception:
                            with self._frame_lock:
                                self.frame = frame
                    else:
                        self.logger.error(f"Camera stopped returning frames")
                        try:
                            self.video_capture.release()
                        except Exception:
                            pass
                        self.video_capture = None
                        self.running.clear()
                        break
                        
                except cv2.error as e:

                    self.logger.error(f"Error while reading videocapture: {e}")

                if self.release.is_set():
                    try:
                        self.video_capture.release()
                    except Exception:
                        pass
                    self.video_capture = None
                
            self.running.clear()

    def get_frame(self):
        
        with self._frame_lock:
            if self.frame is None:
                return None
            try:
                return self.frame.copy()
            except Exception:
                return self.frame
    
    def is_connected(self):
        return (self.video_capture is not None) and (self.video_capture.isOpened())
