import cv2
import threading
import time

class CameraStream:
    def __init__(self, rtsp_url):
        # Convert "0" or "1" to integer for webcams
        self.rtsp_url = int(rtsp_url) if str(rtsp_url).isdigit() else rtsp_url
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.latest_frame = None
        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()
        
    def _reader_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.latest_frame = frame
            else:
                # Try to reconnect
                self.cap.release()
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.rtsp_url)
                
    def read(self):
        return self.latest_frame
        
    def stop(self):
        self.running = False
        self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
