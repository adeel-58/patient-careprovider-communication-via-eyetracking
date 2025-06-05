import cv2
import numpy as np
import dlib
from math import hypot
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSizePolicy, QScrollArea, QDialog, QMessageBox
)
from PyQt5.QtGui import QFont, QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QWaitCondition, QMutex
from PyQt5.QtWidgets import QDesktopWidget
import time
import requests
# Removed firebase_admin imports

# Removed FirestoreSignal class

# Blink and Gaze Detection in a Separate Thread
class BlinkGazeDetectionThread(QThread):
    """
    A QThread subclass responsible for continuously capturing video frames,
    detecting faces, and analyzing eye blinks and gaze direction.
    It emits signals for detected blinks, gaze direction, and processed frames.
    """
    # Signal emitted when a sequence of 3 blinks is detected
    blink_sequence_detected = pyqtSignal()
    # Signal emitted with the detected gaze direction (e.g., "LEFT", "RIGHT", "CENTER")
    gaze_direction = pyqtSignal(str)
    # Signal emitted with the raw camera frame (NumPy array) for display
    frame_ready = pyqtSignal(np.ndarray)
    # Signal emitted with the thresholded eye image (NumPy array) for display
    threshold_eye_ready = pyqtSignal(np.ndarray)
    # Signal emitted with the current count of consecutive blinks
    consecutive_blinks_count = pyqtSignal(int)
    # Signal emitted with the calculated gaze ratio (float)
    gaze_ratio_value = pyqtSignal(float)

    def __init__(self, app):
        """
        Initializes the BlinkGazeDetectionThread.
        Args:
            app: A reference to the main application instance (AdvancedDesignApp)
                 to allow updating its status messages.
        """
        super().__init__()
        self.app = app # Reference to the main app to update status messages
        self.cap = None # OpenCV VideoCapture object
        
        # Initialize dlib's face detector and facial landmark predictor
        # Ensure 'shape_predictor_68_face_landmarks.dat' is in the same directory as the script
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        
        self.last_blink_time = 0 # Timestamp of the last detected blink
        self.last_gaze_time = 0 # Timestamp of the last detected gaze change
        self.blink_cooldown = 0.5 # Cooldown (in seconds) to prevent multiple detections from one blink
        self.gaze_cooldown = 3 # Cooldown (in seconds) for gaze direction detection

        self.consecutive_blinks = 0 # Counter for consecutive blinks
        self.blink_reset_timer = QTimer()
        self.blink_reset_timer.setInterval(1000) # Reset blinks if no new blink within 1 second
        self.blink_reset_timer.setSingleShot(True) # Timer runs only once
        self.blink_reset_timer.timeout.connect(self.reset_consecutive_blinks)

        # Variables for pausing/resuming the thread
        self._is_paused = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()

    def midpoint(self, p1 ,p2):
        """
        Calculates the midpoint between two dlib points.
        Args:
            p1, p2: dlib.point objects.
        Returns:
            A tuple (x, y) representing the midpoint coordinates.
        """
        return int((p1.x + p2.x)/2) , int((p1.y + p2.y)/2)

    def get_blinking_ratio(self, eye_points, facial_landmarks):
        """
        Calculates the Eye Aspect Ratio (EAR) for a given eye.
        EAR is a measure of how open or closed an eye is.
        Args:
            eye_points: A list of indices corresponding to the 6 facial landmarks
                        for a specific eye (e.g., [36,37,38,39,40,41] for right eye).
            facial_landmarks: The dlib.full_object_detection object containing all 68 landmarks.
        Returns:
            The calculated EAR, or float('inf') if the vertical line length is zero.
        """
        # Get coordinates of the eye landmarks
        left_point = (facial_landmarks.part(eye_points[0]).x, facial_landmarks.part(eye_points[0]).y)
        right_point = (facial_landmarks.part(eye_points[3]).x, facial_landmarks.part(eye_points[3]).y)
        center_top = self.midpoint(facial_landmarks.part(eye_points[1]), facial_landmarks.part(eye_points[2]))
        center_bottom = self.midpoint(facial_landmarks.part(eye_points[5]), facial_landmarks.part(eye_points[4]))

        # Calculate the Euclidean distances between the horizontal and vertical eye landmarks
        hor_line_length = hypot((left_point[0] - right_point[0]), (left_point[1] - right_point[1]))
        ver_line_length = hypot((center_top[0] - center_bottom[0]), (center_top[1] - center_bottom[1]))

        if ver_line_length == 0:
            return float('inf') # Avoid division by zero, indicates fully closed eye
        return hor_line_length / ver_line_length

    def get_gaze_ratio(self, eye_points, facial_landmarks, gray):
        """
        Calculates the gaze ratio for a given eye to determine horizontal gaze direction.
        This is done by thresholding the eye region and comparing white pixel counts
        in the left and right halves of the eye.
        Args:
            eye_points: A list of indices for the 6 facial landmarks of an eye.
            facial_landmarks: The dlib.full_object_detection object.
            gray: The grayscale camera frame.
        Returns:
            The calculated gaze ratio, or 1.0 (neutral) if eye region is invalid.
        """
        # Get the eye region coordinates from facial landmarks
        eye_region = np.array([
            (facial_landmarks.part(eye_points[0]).x, facial_landmarks.part(eye_points[0]).y),
            (facial_landmarks.part(eye_points[1]).x, facial_landmarks.part(eye_points[1]).y),
            (facial_landmarks.part(eye_points[2]).x, facial_landmarks.part(eye_points[2]).y),
            (facial_landmarks.part(eye_points[3]).x, facial_landmarks.part(eye_points[3]).y),
            (facial_landmarks.part(eye_points[4]).x, facial_landmarks.part(eye_points[4]).y),
            (facial_landmarks.part(eye_points[5]).x, facial_landmarks.part(eye_points[5]).y)
        ], np.int32)

        # Create a mask for the eye region to isolate it from the rest of the face
        mask = np.zeros_like(gray)
        cv2.polylines(mask, [eye_region], True, 255, 2) # Draw outline
        cv2.fillPoly(mask, [eye_region], 255) # Fill the eye region

        # Apply the mask to the grayscale frame to get only the eye pixels
        eye = cv2.bitwise_and(gray, gray, mask=mask)

        # Determine the bounding box for the eye region
        min_x = np.min(eye_region[:, 0])
        max_x = np.max(eye_region[:, 0])
        min_y = np.min(eye_region[:, 1])
        max_y = np.max(eye_region[:, 1])

        # Handle cases where eye region might be invalid (e.g., face partially out of frame)
        if max_y - min_y <= 0 or max_x - min_x <= 0:
            return 1.0 # Return neutral gaze if eye region is degenerate (height or width is zero)

        # Crop the eye from the grayscale image using its bounding box
        gray_eye = eye[min_y: max_y, min_x: max_x]

        # Apply thresholding to highlight the pupil (darker areas) as white pixels
        # The threshold value (70) may need adjustment based on lighting conditions
        _, threshold_eye = cv2.threshold(gray_eye, 70, 255, cv2.THRESH_BINARY)
        
        # Emit the thresholded eye image for display in the UI
        if threshold_eye.size > 0: # Ensure the array is not empty
            self.threshold_eye_ready.emit(threshold_eye)

        # Divide the thresholded eye into left and right halves
        left_side_threshold = threshold_eye[:, :threshold_eye.shape[1] // 2]
        right_side_threshold = threshold_eye[:, threshold_eye.shape[1] // 2:]

        # Count non-zero pixels (white pixels, representing pupil/dark areas) in each half
        left_side_white = cv2.countNonZero(left_side_threshold)
        right_side_white = cv2.countNonZero(right_side_threshold)

        # Calculate gaze ratio: ratio of white pixels in left half to right half
        # A smaller ratio indicates gaze to the right (more white on left),
        # a larger ratio indicates gaze to the left (more white on right).
        if right_side_white == 0:
            return 1.0 # Avoid division by zero, treat as neutral if no white pixels on right side
        return left_side_white / right_side_white
    
    def reset_consecutive_blinks(self):
        """Resets the consecutive blink count and updates the UI display."""
        self.consecutive_blinks = 0
        self.consecutive_blinks_count.emit(self.consecutive_blinks)

    def run(self):
        """
        The main loop of the thread. It continuously captures frames,
        performs face, blink, and gaze detection, and emits signals.
        """
        # IMPORTANT: Confirm your external camera index here. Common values are 0, 1, 2.
        # If 1 doesn't work, try 0 or 2, or check your system's camera settings.
        self.cap = cv2.VideoCapture(0) 
        if not self.cap.isOpened():
            print("Error: Could not open camera. Please check camera index or if camera is in use by another application.")
            return

        try:
            while True:
                # Acquire mutex before checking pause state
                self._mutex.lock()
                while self._is_paused:
                    # If paused, wait for the condition to be signaled
                    self._condition.wait(self._mutex)
                self._mutex.unlock() # Release mutex after processing pause state

                ret, frame = self.cap.read() # Read a frame from the camera
                if not ret or frame is None:
                    # If frame is not read correctly, continue to the next iteration
                    continue

                gray = cv2.cvtColor(frame , cv2.COLOR_BGR2GRAY) # Convert frame to grayscale
                faces = self.detector(gray) # Detect faces in the grayscale frame
                self.frame_ready.emit(frame) # Emit the raw frame for display in the UI

                if len(faces) == 0:
                    # If no face is detected, reset blinks and update status
                    self.gaze_direction.emit("No face detected")
                    self.app.update_status_message("Status: No face detected")
                    self.consecutive_blinks = 0
                    self.consecutive_blinks_count.emit(self.consecutive_blinks)
                    self.gaze_ratio_value.emit(1.0) # Emit neutral gaze ratio
                    cv2.waitKey(1) # Small delay to prevent 100% CPU usage
                    continue

                for face in faces:
                    landmarks = self.predictor(gray,face) # Get facial landmarks for the detected face
                    
                    # Calculate blinking ratio for both eyes
                    right_eye_ratio = self.get_blinking_ratio([36,37,38,39,40,41],landmarks)
                    left_eye_ratio = self.get_blinking_ratio([42,43,44,45,46,47],landmarks)
                    blinking_ratio = (left_eye_ratio + right_eye_ratio ) / 2

                    # Blink detection logic
                    # A ratio > 4.7 typically indicates a closed eye (blink)
                    if blinking_ratio > 4.7:
                        # Apply cooldown to prevent multiple blink detections from a single actual blink
                        if time.time() - self.last_blink_time > self.blink_cooldown:
                            self.last_blink_time = time.time() # Update last blink time
                            self.consecutive_blinks += 1 # Increment consecutive blink count
                            self.consecutive_blinks_count.emit(self.consecutive_blinks) # Update UI
                            self.app.update_status_message(f"Blink {self.consecutive_blinks} detected!")
                            self.blink_reset_timer.start() # Start or restart the timer to reset blinks

                            if self.consecutive_blinks >= 3:
                                # Emit signal when 3 consecutive blinks are detected
                                self.blink_sequence_detected.emit()
                                # Reset consecutive blinks immediately after emitting the signal
                                # The main app will handle the action and further resets if needed
                                self.consecutive_blinks = 0
                                self.consecutive_blinks_count.emit(self.consecutive_blinks)
                                self.blink_reset_timer.stop() # Stop the reset timer as blinks were consumed

                    # Gaze detection logic
                    # Only calculate gaze if not in a cooldown period to avoid rapid, erratic changes
                    gaze_ratio_right_eye = self.get_gaze_ratio([36,37,38,39,40,41],landmarks,gray)
                    gaze_ratio_left_eye = self.get_gaze_ratio([42,43,44,45,46,47],landmarks,gray)
                    gaze_ratio = (gaze_ratio_right_eye + gaze_ratio_left_eye) / 2
                    self.gaze_ratio_value.emit(gaze_ratio) # Emit the gaze ratio value

                    if time.time() - self.last_gaze_time > self.gaze_cooldown:
                        if gaze_ratio <= 0.5: # Smaller ratio implies looking RIGHT
                            self.gaze_direction.emit("RIGHT")
                            self.app.update_status_message("Gaze: RIGHT")
                        elif 0.6 < gaze_ratio < 1.15: # Ratio in this range implies looking CENTER
                            self.gaze_direction.emit("CENTER")
                            self.app.update_status_message("Gaze: CENTER")
                        else: # Otherwise, assume LEFT gaze
                            self.gaze_direction.emit("LEFT")
                            self.app.update_status_message("Gaze: LEFT")
                        
                        self.last_gaze_time = time.time() # Reset gaze cooldown timer
                        # Reset consecutive blinks after a gaze detection, as gaze implies user is not trying to blink-confirm
                        self.consecutive_blinks = 0
                        self.consecutive_blinks_count.emit(self.consecutive_blinks)

                cv2.waitKey(1) # Small delay to yield control and prevent high CPU usage

        except Exception as e:
            print(f"Error in BlinkGazeDetectionThread: {e}")

        finally:
            # Release camera resources when the thread stops or an error occurs
            if self.cap and self.cap.isOpened():
                self.cap.release()
                print("Camera released")

    def stop(self):
        """
        Terminates the thread and ensures camera resources are released cleanly.
        Call this method when closing the application.
        """
        self.terminate() # Request the thread to terminate
        self.wait() # Wait for the thread to finish execution cleanly

    def pause(self):
        """Pauses the execution of the thread's run loop."""
        self._mutex.lock()
        self._is_paused = True
        self._mutex.unlock()
        print("BlinkGazeDetectionThread paused.")
        self.app.update_status_message("Eye commands paused.") # Update main app status

    def resume(self):
        """Resumes the execution of the thread's run loop."""
        self._mutex.lock()
        self._is_paused = False
        self._condition.wakeAll() # Wake up all waiting threads
        self._mutex.unlock()
        print("BlinkGazeDetectionThread resumed.")
        self.app.update_status_message("Eye commands resumed.") # Update main app status

class RequestSentPopup(QDialog):
    """
    A modal popup dialog displayed after a service request has been successfully sent.
    It shows the selected option and a status message, typically including the assigned nurse.
    This popup now automatically closes after a set duration.
    """
    def __init__(self, selected_option, request_status_message=""):
        """
        Initializes the RequestSentPopup.
        Args:
            selected_option (dict): The dictionary representing the service option that was requested.
            request_status_message (str): A message indicating the status of the request (e.g., assigned nurse).
        """
        super().__init__()
        self.selected_option = selected_option
        self.request_status_message = request_status_message
        self.init_ui()

        # Automatically close the popup after 3 seconds
        QTimer.singleShot(3000, self.accept) # Call accept() to close the dialog

    def init_ui(self):
        """Sets up the user interface for the popup."""
        self.setWindowTitle("Request Sent!")
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.8);") # Darker semi-transparent background
        # Remove title bar and keep on top for a more immersive popup experience
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose) # Automatically delete the widget when it's closed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30) # Padding around content
        layout.setSpacing(20) # Spacing between widgets

        # Image label for the selected service option
        image_label = QLabel(self)
        pixmap = QPixmap(self.selected_option["image"]).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        # Text label for the selected service option's name
        text_label = QLabel(self.selected_option["text"], self)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        layout.addWidget(text_label)

        # Label to display the request status message (e.g., nurse assigned)
        status_label = QLabel(self.request_status_message, self)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("color: #ADD8E6; font-size: 20px; font-weight: bold; margin-top: 10px;") # Light blue text
        layout.addWidget(status_label)

        self.setLayout(layout)
        self.setModal(True) # Make it a modal dialog (blocks interaction with parent window)
        self.adjustSize() # Adjust size to fit content

        # Center the dialog on the screen
        qr = self.frameGeometry() # Get the rectangle of the dialog frame
        cp = QApplication.desktop().availableGeometry().center() # Get the center point of the available screen geometry
        qr.moveCenter(cp) # Move the dialog's center to the screen's center
        self.move(qr.topLeft()) # Move the dialog to the calculated top-left position

class AdvancedDesignApp(QWidget):
    """
    The main application window for the patient interface.
    It integrates camera feed, blink/gaze detection, option selection,
    service request handling, and real-time status updates.
    """
    def __init__(self, access_token, patient_id, patient_username, patient_bed_number):
        """
        Initializes the AdvancedDesignApp.
        Args:
            access_token (str): Authentication token for API requests.
            patient_id (str): Unique ID of the patient.
            patient_username (str): Name of the patient.
            patient_bed_number (str): Bed number of the patient.
        """
        super().__init__()
        self.access_token = access_token
        self.patient_id = patient_id
        self.patient_username = patient_username
        self.patient_bed_number = patient_bed_number if patient_bed_number else "B100"
        self.base_url = "http://127.0.0.1:8000" # Base URL for your FastAPI backend

        # Removed Firebase setup
        # self.firebase_initialized = False
        # try:
        #     cred = credentials.Certificate('firebase_service_account.json')
        #     firebase_admin.initialize_app(cred)
        #     self.db = firestore.client()
        #     self.firebase_initialized = True
        #     print("Firebase initialized successfully.")
        # except Exception as e:
        #     print(f"Error initializing Firebase: {e}")
        #     QMessageBox.critical(self, "Firebase Error", f"Failed to initialize Firebase: {e}\n"
        #                                                  "Ensure 'firebase_service_account.json' is in the correct directory.")

        self.current_index = 0 # Index of the currently selected service option
        self.card_widgets = [] # List to hold the small card widgets in the top scroll area
        self.selected_cards_data = [] # Stores manually selected options (for debugging/tracking)

        self.gaze_cooldown_active = False # Flag to prevent rapid gaze-based scrolling
        self.dialog_open = False # General flag to indicate if any modal dialog (popup) is currently open

        # Status message timer: resets the status label text after a short delay
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(2000) # 2 seconds
        self.status_timer.setSingleShot(True) # Timer runs only once
        self.status_timer.timeout.connect(lambda: self.status_label.setText("Status: Ready"))

        # Removed Service request monitoring (Firestore listener)
        # self.current_service_request_id = None
        # self.firestore_listener_unsub = None
        # self.firestore_signal = FirestoreSignal()
        # self.firestore_signal.data_changed.connect(self.handle_firestore_update)

        # New: Store available nurses fetched from the API
        self.available_nurses = []

        # Timer to hide the nurse status message after 5 minutes
        self.nurse_display_timer = QTimer(self)
        self.nurse_display_timer.setInterval(5 * 60 * 1000) # 5 minutes (in milliseconds)
        self.nurse_display_timer.setSingleShot(True) # Timer runs only once
        self.nurse_display_timer.timeout.connect(self.hide_nurse_status)

        # Define the available service options
        self.options = [
            {"text": "Call Nurse", "image": "./assets/nurse.png", "need": "a nurse"},
            {"text": "Go to Washroom", "image": "./assets/toilet.png", "need": "to go to the washroom"},
            {"text": "Need Food", "image": "./assets/diet.png", "need": "food"},
            {"text": "Turn Off Lights", "image": "./assets/switch-off.png", "need": "lights turned off"},
            {"text": "Adjust Bed", "image": "./assets/bed.png", "need": "bed adjusted"},
            {"text": "Request Water", "image": "./assets/water.png", "need": "a glass of water"},
            {"text": "Request Blanket", "image": "./assets/blanket.png", "need": "a blanket"},
            {"text": "Open Window", "image": "./assets/window.png", "need": "window opened"},
        ]

        self.init_ui() # Initialize the user interface components
        self.start_blink_gaze_thread() # Start the camera and detection thread
        
        # Fetch available nurses from the backend after UI is initialized
        self.fetch_available_nurses()
        
    def start_blink_gaze_thread(self):
        """Initializes and starts the blink and gaze detection thread."""
        self.blink_gaze_thread = BlinkGazeDetectionThread(self)
        # Connect signals from the thread to appropriate handlers in the main app
        self.blink_gaze_thread.gaze_direction.connect(self.handle_gaze_direction)
        self.blink_gaze_thread.frame_ready.connect(self.update_camera_view)
        self.blink_gaze_thread.threshold_eye_ready.connect(self.update_threshold_eye_view)
        self.blink_gaze_thread.consecutive_blinks_count.connect(self.update_blink_count_display)
        self.blink_gaze_thread.blink_sequence_detected.connect(self.on_blink_sequence_detected)
        self.blink_gaze_thread.gaze_ratio_value.connect(self.update_gaze_ratio_display)
        self.blink_gaze_thread.start() # Start the QThread

    def on_blink_sequence_detected(self):
        """
        Handles the signal from the detection thread when 3 blinks are detected.
        This method now directly triggers the service request and pauses eye commands.
        """
        if not self.dialog_open: # Ensure no other modal dialog is already open
            self.dialog_open = True # Set general dialog flag to prevent further actions
            selected_option = self.options[self.current_index]
            self.update_status_message("Sending Request...") # Immediate feedback
            self.send_service_request(selected_option)
            # Reset blinks immediately after triggering the request
            self.blink_gaze_thread.consecutive_blinks = 0
            self.blink_gaze_thread.consecutive_blinks_count.emit(0)
            self.blink_gaze_thread.blink_reset_timer.stop()
            
            # Pause eye command processing and camera feed after sending request
            # It will remain paused as there's no Firestore to resume it.
            self.blink_gaze_thread.pause()

    def show_request_sent_popup(self, selected_option, request_status_message=""):
        """
        Displays the RequestSentPopup after a service request has been successfully sent.
        Args:
            selected_option (dict): The dictionary representing the service option that was requested.
            request_status_message (str): A message indicating the status of the request (e.g., assigned nurse).
        """
        self.dialog_open = True # Set general dialog flag
        popup = RequestSentPopup(selected_option, request_status_message)
        popup.finished.connect(self.request_sent_popup_closed) # Connect to closure handler
        popup.exec_() # Show modal popup

    def request_sent_popup_closed(self, result):
        """
        Callback function executed when the RequestSentPopup is closed.
        Resets general dialog flag and blink counts.
        Args:
            result (int): The result code of the dialog (QDialog.Accepted or QDialog.Rejected).
        """
        self.dialog_open = False # Reset general dialog flag
        self.blink_gaze_thread.consecutive_blinks = 0 # Reset thread's internal blink count
        self.blink_gaze_thread.consecutive_blinks_count.emit(0) # Update UI
        self.blink_gaze_thread.blink_reset_timer.stop() # Ensure the blink reset timer is stopped


    def fetch_available_nurses(self):
        """
        Fetches a list of available nurses from the backend API.
        This list is used to assign a nurse to a service request.
        """
        if not self.access_token:
            print("Cannot fetch nurses: Access token not available.")
            return

        self.update_status_message("Fetching available nurses...")
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        try:
            response = requests.get(f"{self.base_url}/api/nurses/available/", headers=headers)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            self.available_nurses = response.json()
            self.update_status_message(f"{len(self.available_nurses)} nurses available.")
            print(f"Available Nurses: {self.available_nurses}")
            if not self.available_nurses:
                QMessageBox.warning(self, "No Nurses", "Currently, no nurses are available. Please try again later.")
        except requests.exceptions.RequestException as e:
            error_message = "Failed to fetch available nurses."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("detail", error_data.get("message", error_message))
                    if e.response.status_code == 401:
                        error_message = "Unauthorized. Please log in again."
                        QMessageBox.critical(self, "Session Expired", error_message)
                except ValueError: # If response is not JSON
                    error_message = f"Server error: {e.response.status_code} {e.response.text}"
            else: # Network error
                error_message = f"Network error: {e}"
            self.update_status_message(f"Failed to fetch nurses: {error_message}")
            QMessageBox.critical(self, "API Error", f"Failed to fetch available nurses: {error_message}")

    def send_service_request(self, selected_option):
        """
        Sends a service request to the backend API.
        It attempts to assign the request to an available nurse.
        Args:
            selected_option (dict): The service option chosen by the user.
        """
        if not self.access_token:
            QMessageBox.warning(self, "Authentication Error", "You are not logged in. Please log in first.")
            self.dialog_open = False # Allow further interaction
            self.blink_gaze_thread.resume() # Resume eye commands if request failed
            return
        
        # Ensure we have available nurses before attempting to send a request
        if not self.available_nurses:
            QMessageBox.warning(self, "No Nurses Available", "Cannot send request: No nurses are currently available.")
            self.update_status_message("Request failed: No nurses available.")
            self.dialog_open = False # Allow further interaction
            self.blink_gaze_thread.resume() # Resume eye commands if request failed
            return

        # Select the first available nurse from the fetched list
        selected_nurse_id = self.available_nurses[0].get("id")
        if not selected_nurse_id:
            QMessageBox.critical(self, "Error", "Selected nurse has no ID. Cannot send request.")
            self.update_status_message("Request failed: Nurse ID missing.")
            self.dialog_open = False # Allow further interaction
            self.blink_gaze_thread.resume() # Resume eye commands if request failed
            return

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json" # Explicitly set content type for JSON payload
        }
        
        data = {
            "need": selected_option["need"],
            "patient_name": self.patient_username,
            "patient_bed_number": self.patient_bed_number,
            "selected_nurse_id": selected_nurse_id # Pass the selected nurse ID
        }

        print("\n--- Request Data (Service Request - BEFORE Sending) ---")
        print(json.dumps(data, indent=4))
        print("-------------------------------------------------------\n")

        try:
            # Send the POST request to create a service request
            response = requests.post(f"{self.base_url}/api/service-requests/create/", headers=headers, json=data)

            print("\n--- Response Data (Service Request - AFTER Sending) ---")
            print(f"Status Code: {response.status_code}")
            try:
                response_json = response.json()
                print("Response JSON:")
                print(json.dumps(response_json, indent=4))
            except json.JSONDecodeError:
                print("Response Text (Not JSON):")
                print(response.text)
            print("-------------------------------------------------------\n")

            response.raise_for_status() # This will raise an HTTPError for 4xx/5xx responses
            response_data = response.json()
            
            # self.current_service_request_id = str(response_data.get("request_id")) # Not needed without Firestore
            assigned_nurse_name = response_data.get("assigned_nurse_name", "N/A")

            print(f"Service request created successfully! Assigned Nurse: {assigned_nurse_name}")
            self.update_status_message(f"Request sent! Assigned to: {assigned_nurse_name}")
            
            # Show the "Request Sent!" popup to the user
            self.show_request_sent_popup(selected_option, f"Request sent! Assigned to: {assigned_nurse_name}")

            # Display nurse status on the main window for 5 minutes
            self.display_nurse_status(f"Nurse {assigned_nurse_name} is on the way!")

            # Removed Firestore listener start

        except requests.exceptions.HTTPError as e:
            error_message = f"Failed to create service request: {e.response.status_code} "
            try:
                error_data = e.response.json()
                error_message += error_data.get("detail", error_data.get("message", e.response.text))
            except ValueError: # Handle non-JSON error responses
                error_message += e.response.text
            print(f"HTTP Error: {error_message}")
            QMessageBox.critical(self, "API Error", error_message)
            self.update_status_message(f"Request failed: {error_message}")
            self.dialog_open = False # Allow further interaction
            self.blink_gaze_thread.resume() # Resume eye commands if request failed
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error: Could not connect to the API server. Is it running? {e}")
            QMessageBox.critical(self, "Network Error", "Could not connect to the API server. Please ensure it is running.")
            self.update_status_message("Request failed: Network error.")
            self.dialog_open = False # Allow further interaction
            self.blink_gaze_thread.resume() # Resume eye commands if request failed
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            self.update_status_message(f"Request failed: Unexpected error.")
            self.dialog_open = False # Allow further interaction
            self.blink_gaze_thread.resume() # Resume eye commands if request failed
        
    # Removed start_firestore_listener method
    # Removed handle_firestore_update method

    def display_nurse_status(self, message):
        """
        Displays the nurse status message on the main window for a limited time (5 minutes).
        Args:
            message (str): The message to display (e.g., "Nurse John Doe is on the way!").
        """
        self.nurse_status_label.setText(message)
        self.nurse_status_label.show() # Make the label visible
        self.nurse_display_timer.start() # Start the timer to hide the message after 5 minutes

    def hide_nurse_status(self):
        """Hides the nurse status message label and clears its text."""
        self.nurse_status_label.hide()
        self.nurse_status_label.setText("") # Clear text

    def update_camera_view(self, frame):
        """
        Updates the QLabel with the current camera frame.
        Args:
            frame (np.ndarray): The raw camera frame as a NumPy array (BGR format).
        """
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # Convert BGR to RGB for QImage
        h, w, ch = rgb_image.shape # Get height, width, and channels
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        qt_image = qt_image.scaled(200, 150, Qt.KeepAspectRatio) # Scale for display
        self.camera_label.setPixmap(QPixmap.fromImage(qt_image))

    def update_threshold_eye_view(self, threshold_frame):
        """
        Updates the QLabel with the thresholded eye view.
        Args:
            threshold_frame (np.ndarray): The thresholded eye image as a grayscale NumPy array.
        """
        # Convert grayscale thresholded image to RGB for QImage display
        rgb_image = cv2.cvtColor(threshold_frame, cv2.COLOR_GRAY2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        qt_image = qt_image.scaled(100, 75, Qt.KeepAspectRatio) # Scale for display
        self.threshold_eye_label.setPixmap(QPixmap.fromImage(qt_image))

    def update_gaze_ratio_display(self, gaze_ratio):
        """
        Updates the QLabel displaying the current gaze ratio.
        Args:
            gaze_ratio (float): The calculated gaze ratio.
        """
        self.gaze_ratio_label.setText(f"Gaze Ratio: {gaze_ratio:.2f}") # Format to 2 decimal places

    def update_status_message(self, message):
        """
        Updates the main status label with a new message and starts a timer to reset it.
        Args:
            message (str): The status message to display.
        """
        self.status_label.setText(message)
        self.status_timer.start() # Restart the timer

    def update_blink_count_display(self, count):
        """
        Updates the display for the current consecutive blink count.
        Args:
            count (int): The current number of consecutive blinks.
        """
        self.blink_count_label.setText(f"Blinks: {count}/3")
        
    def handle_gaze_direction(self, direction):
        """
        Handles gaze direction changes to navigate through the service options.
        Args:
            direction (str): The detected gaze direction ("LEFT", "RIGHT", or "CENTER").
        """
        # Prevent gaze actions if a modal dialog is open or during a cooldown period
        if self.gaze_cooldown_active or self.dialog_open:
            return

        print(f"Gaze direction: {direction}")
        self.gaze_cooldown_active = True # Activate cooldown to prevent rapid scrolling

        if direction == "RIGHT":
            self.next_option()
        elif direction == "LEFT":
            self.prev_option()
        
        self.update_status_message(f"Gaze: {direction}")

        # Start a timer to reset gaze cooldown after 1 second
        QTimer.singleShot(1000, self.reset_gaze_cooldown)
        
    def reset_gaze_cooldown(self):
        """Resets the gaze cooldown flag, allowing further gaze detection."""
        self.gaze_cooldown_active = False

    def init_ui(self):
        """Initializes all the user interface components and their layout."""
        self.setWindowTitle("Patient App")
        # Set initial window size and style
        self.setGeometry(100, 100, 1024, 768) # Increased default size for better layout
        self.setStyleSheet("background-color: #013220; font-family: 'Inter', sans-serif;") # Dark green background, Inter font
        
        # Get screen geometry to center the window on the screen
        screen = QDesktopWidget().screenGeometry()
        self.move(int((screen.width() - self.width()) / 2), int((screen.height() - self.height()) / 2))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # Padding around the main layout
        main_layout.setSpacing(15) # Spacing between major sections

        # --- Top Section: Camera Feed, Status, and Patient Info ---
        top_info_layout = QHBoxLayout()
        top_info_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # Layout for camera feed and status labels
        camera_and_status_layout = QVBoxLayout()
        camera_and_status_layout.setSpacing(5)

        self.camera_label = QLabel()
        self.camera_label.setFixedSize(200, 150)
        # Styling for camera feed label
        self.camera_label.setStyleSheet("border: 3px solid #2e8b57; border-radius: 15px; background-color: #000;")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setText("Camera Feed") # Placeholder text until feed starts
        self.camera_label.setFont(QFont("Inter", 12))
        self.camera_label.setStyleSheet("color: gray; border: 3px solid #2e8b57; border-radius: 15px; background-color: #000;")

        self.threshold_eye_label = QLabel()
        self.threshold_eye_label.setFixedSize(100, 75)
        # Styling for thresholded eye label
        self.threshold_eye_label.setStyleSheet("border: 2px solid #a2d2ff; border-radius: 10px; background-color: #000;")
        self.threshold_eye_label.setAlignment(Qt.AlignCenter)
        self.threshold_eye_label.setText("Threshold Eye") # Placeholder text
        self.threshold_eye_label.setFont(QFont("Inter", 10))
        self.threshold_eye_label.setStyleSheet("color: gray; border: 2px solid #a2d2ff; border-radius: 10px; background-color: #000;")

        self.status_label = QLabel("Status: Ready")
        # Styling for general status message
        self.status_label.setStyleSheet("color: #E0FFFF; font-size: 18px; font-weight: bold; padding: 5px; background-color: rgba(46, 139, 87, 0.5); border-radius: 8px;")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.blink_count_label = QLabel("Blinks: 0/3")
        # Styling for consecutive blink count display
        self.blink_count_label.setStyleSheet("color: #FFD700; font-size: 18px; font-weight: bold; padding: 5px; background-color: rgba(46, 139, 87, 0.5); border-radius: 8px;")
        self.blink_count_label.setAlignment(Qt.AlignCenter)

        camera_and_status_layout.addWidget(self.camera_label)
        camera_and_status_layout.addWidget(self.threshold_eye_label)
        camera_and_status_layout.addWidget(self.status_label)
        camera_and_status_layout.addWidget(self.blink_count_label)
        
        top_info_layout.addLayout(camera_and_status_layout)
        top_info_layout.addStretch(1) # Pushes elements to the left

        # Patient Info Section (aligned to the right)
        patient_info_layout = QVBoxLayout()
        patient_info_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
        patient_info_layout.setSpacing(5)

        patient_name_label = QLabel(f"Patient: {self.patient_username}")
        patient_name_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        patient_name_label.setAlignment(Qt.AlignRight)

        patient_bed_label = QLabel(f"Bed: {self.patient_bed_number}")
        patient_bed_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        patient_bed_label.setAlignment(Qt.AlignRight)

        # Gaze Ratio Label
        self.gaze_ratio_label = QLabel("Gaze Ratio: N/A")
        self.gaze_ratio_label.setStyleSheet("color: #90EE90; font-size: 18px; font-weight: bold; padding: 5px; background-color: rgba(46, 139, 87, 0.5); border-radius: 8px;")
        self.gaze_ratio_label.setAlignment(Qt.AlignRight)

        patient_info_layout.addWidget(patient_name_label)
        patient_info_layout.addWidget(patient_bed_label)
        patient_info_layout.addWidget(self.gaze_ratio_label) # Add gaze ratio label to the patient info layout
        
        top_info_layout.addLayout(patient_info_layout)

        main_layout.addLayout(top_info_layout)

        # Nurse Status Label (initially hidden, appears after request is sent)
        self.nurse_status_label = QLabel("")
        self.nurse_status_label.setStyleSheet("color: #FFD700; font-size: 22px; font-weight: bold; padding: 10px; background-color: rgba(0, 0, 0, 0.7); border-radius: 15px;")
        self.nurse_status_label.setAlignment(Qt.AlignCenter)
        self.nurse_status_label.hide() # Initially hidden
        main_layout.addWidget(self.nurse_status_label)

        # --- Middle Section: Scroll Area for Small Option Cards ---
        self.top_scroll_area = QScrollArea()
        self.top_scroll_area.setFixedHeight(200) # Fixed height for the scroll area
        self.top_scroll_area.setWidgetResizable(True) # Allow widget inside to resize
        self.top_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Hide horizontal scrollbar
        self.top_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Hide vertical scrollbar
        self.top_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.top_widget = QWidget() # Widget to hold the horizontal layout of cards
        self.top_layout = QHBoxLayout(self.top_widget)
        self.top_layout.setSpacing(20) # Spacing between small cards
        self.top_layout.setContentsMargins(15, 10, 5, 10) # Margins around cards
        self.top_layout.setAlignment(Qt.AlignLeft) # Align cards to the left within the scroll area

        self.top_scroll_area.setWidget(self.top_widget)
        main_layout.addWidget(self.top_scroll_area)

        # --- Bottom Section: Navigation Buttons and Selected Card Display ---
        self.bottom_widget = QWidget()
        bottom_wrapper_layout = QVBoxLayout(self.bottom_widget)
        bottom_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        bottom_wrapper_layout.setAlignment(Qt.AlignTop)

        arrow_row = QHBoxLayout()
        # Adjusted top margin to push content down from the scroll area
        arrow_row.setContentsMargins(0, int(screen.height() * 0.05), 0, 0)
        arrow_row.setAlignment(Qt.AlignCenter)
        arrow_row.setStretch(0, 1) # Left button stretch factor
        arrow_row.setStretch(1, 3) # Content container stretch factor
        arrow_row.setStretch(2, 1) # Right button stretch factor

        self.left_button = QPushButton("←")
        self.left_button.setFixedSize(100, 100) # Fixed size for navigation buttons
        self.left_button.clicked.connect(self.prev_option) # Connect to previous option handler
        # Styling for navigation buttons
        self.left_button.setStyleSheet("""
            QPushButton {
                font-size: 40px;
                color: white;
                background-color: #2e8b57; /* Sea Green */
                border-radius: 50px; /* Circular buttons */
                border: 3px solid #1e7041;
                box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3);
            }
            QPushButton:hover {
                background-color: #3cb371; /* Medium Sea Green on hover */
                box-shadow: 5px 5px 20px rgba(0, 0, 0, 0.5);
            }
            QPushButton:pressed {
                background-color: #1e7041; /* Darker green when pressed */
                box-shadow: inset 2px 2px 5px rgba(0, 0, 0, 0.3);
            }
        """)

        self.content_container = QWidget() # Container for the large selected option card
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setAlignment(Qt.AlignCenter) # Center the content within its container

        self.right_button = QPushButton("→")
        self.right_button.setFixedSize(100, 100) # Fixed size for navigation buttons
        self.right_button.clicked.connect(self.next_option) # Connect to next option handler
        # Styling for navigation buttons (same as left button)
        self.right_button.setStyleSheet("""
            QPushButton {
                font-size: 40px;
                color: white;
                background-color: #2e8b57; /* Sea Green */
                border-radius: 50px;
                border: 3px solid #1e7041;
                box-shadow: 5px 5px 15px rgba(0, 0, 0, 0.3);
            }
            QPushButton:hover {
                background-color: #3cb371; /* Medium Sea Green on hover */
                box-shadow: 5px 5px 20px rgba(0, 0, 0, 0.5);
            }
            QPushButton:pressed {
                background-color: #1e7041; /* Darker green when pressed */
                box-shadow: inset 2px 2px 5px rgba(0, 0, 0, 0.3);
            }
        """)

        # Add buttons and content container to the arrow row layout
        arrow_row.addWidget(self.left_button)
        arrow_row.addStretch(1) # Flexible space before content
        arrow_row.addWidget(self.content_container)
        arrow_row.addStretch(1) # Flexible space after content
        arrow_row.addWidget(self.right_button)

        bottom_wrapper_layout.addLayout(arrow_row)
        main_layout.addWidget(self.bottom_widget)

        self.update_selected_card() # Initial display of the selected card

    def create_card(self, text, image_path, small=False, index=None):
        """
        Creates a QWidget representing an option card with an image and text.
        Args:
            text (str): The text to display on the card.
            image_path (str): The path to the image for the card.
            small (bool): If True, creates a smaller card for the top scroll area.
                          If False, creates a larger card for the main display.
            index (int, optional): The index of the card, used for highlighting in the small view.
        Returns:
            QWidget: The created card widget.
        """
        card = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10) # Spacing between image and text

        text_label = QLabel(text)
        # Font size varies based on card size
        text_label.setFont(QFont("Inter", 14 if small else 28, QFont.Bold))
        text_label.setStyleSheet("color: white;")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True) # Allow text to wrap within the label

        image_label = QLabel()
        # Image size varies based on card size
        image_size = 80 if small else 200
        pixmap = QPixmap(image_path).scaled(image_size, image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(image_label)
        layout.addWidget(text_label)
        card.setLayout(layout)

        if small:
            card.setFixedSize(180, 160) # Fixed size for small cards
        else:
            # Dynamic size for the main selected card based on window dimensions
            card_width = int(self.width() * 0.4) # 40% of main window width
            card_height = int(self.height() * 0.4) # 40% of main window height
            card.setFixedSize(card_width, card_height)

        # Styling for the card, with a yellow border highlight for the selected small card
        border = "none"
        shadow = ""
        if small and index == self.current_index:
            border = "4px solid yellow" # Highlight selected small card
            shadow = "box-shadow: 0 0 20px yellow;" # Add a glow effect
        
        card.setStyleSheet(f"""
            QWidget {{
                background-color: #2e8b57; /* Sea Green */
                border-radius: 25px; /* More rounded corners */
                padding: 15px;
                border: {border};
                {shadow}
            }}
        """)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return card

    def update_top_cards(self, enable_interaction=True):
        """
        Updates the small option cards in the top scroll area.
        It clears existing cards and re-adds them to reflect the current selection highlight.
        Can also disable interaction on the cards.
        """
        # Clear existing cards from the layout
        for i in reversed(range(self.top_layout.count())):
            widget_to_remove = self.top_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
        self.card_widgets.clear() # Clear the list of card widgets

        # Add new cards to the layout
        for idx, option in enumerate(self.options):
            card = self.create_card(option["text"], option["image"], small=True, index=idx)
            card.setEnabled(enable_interaction) # Enable/disable card interaction
            self.top_layout.addWidget(card)
            self.card_widgets.append(card)

    def update_selected_card(self, enable_interaction=True):
        """
        Updates the main selected card displayed in the center of the screen
        and ensures the corresponding small card in the top scroll area is visible.
        Can also disable interaction on the main card.
        """
        self.update_top_cards(enable_interaction) # Re-render top cards to update the highlight

        # Scroll to the currently selected card in the top scroll area
        def scroll_to_selected():
            if 0 <= self.current_index < len(self.card_widgets):
                self.top_scroll_area.ensureWidgetVisible(
                    self.card_widgets[self.current_index], xMargin=40, yMargin=0
                )
        # Use QTimer.singleShot(0, ...) to ensure scrolling happens after layout updates are complete
        QTimer.singleShot(0, scroll_to_selected)

        # Clear existing main selected card from its layout
        for i in reversed(range(self.content_layout.count())):
            widget_to_remove = self.content_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        # Create and add the new main selected card
        selected_option = self.options[self.current_index]
        new_card = self.create_card(selected_option["text"], selected_option["image"], small=False)
        new_card.setEnabled(enable_interaction) # Enable/disable main card interaction

        # Allow manual click on the main card to trigger selection (for testing/accessibility)
        # This simulates the 3-blink trigger for convenience
        new_card.mousePressEvent = lambda event: self.on_blink_sequence_detected()

        self.content_layout.addWidget(new_card)

    def save_selection(self, selected_option):
        """
        Saves the manually selected option data (primarily for debugging/tracking).
        Args:
            selected_option (dict): The option dictionary that was selected.
        """
        self.selected_cards_data.append(selected_option)
        print("Selected Cards Data:")
        for i, item in enumerate(self.selected_cards_data, start=1):
            print(f"{i}. {item['text']} - {item['image']}")
        self.update_status_message(f"Manually Selected: {selected_option['text']}")

    def next_option(self):
        """Navigates to the next service option in the list."""
        # Only allow navigation if eye commands are not paused
        if not self.blink_gaze_thread._is_paused:
            self.current_index = (self.current_index + 1) % len(self.options)
            self.update_selected_card() # Update UI to show the new selection

    def prev_option(self):
        """Navigates to the previous service option in the list."""
        # Only allow navigation if eye commands are not paused
        if not self.blink_gaze_thread._is_paused:
            self.current_index = (self.current_index - 1 + len(self.options)) % len(self.options)
            self.update_selected_card() # Update UI to show the new selection

    def closeEvent(self, event):
        """
        Overrides the default close event handler for the application window.
        Ensures proper cleanup of resources, especially threads.
        """
        # Removed Firestore listener unsubscribing
        
        # Stop the blink/gaze detection thread cleanly
        if self.blink_gaze_thread and self.blink_gaze_thread.isRunning():
            self.blink_gaze_thread.stop() # Request the thread to stop
            self.blink_gaze_thread.wait() # Wait for the thread to terminate cleanly
            print("BlinkGazeDetectionThread stopped.")
            
        super().closeEvent(event) # Call the base class close event handler

