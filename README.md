**EyeLink: Enhancing Patient-Care Provider Communication via Eye-Tracking**
**Project Overview**
EyeLink is a revolutionary multi-platform software system designed to enhance patient care and communication for individuals with severe physical disabilities (e.g., quadriplegia, ALS, paralysis) by leveraging real-time eye-tracking technology. This project enables patients to communicate their needs or "call" for assistance through their eye movements, which are captured by a desktop application and processed by a backend service for dynamic nurse assignment.

The core idea is to use eye-gaze data from these patients to provide a direct, non-verbal method of signaling needs, optimizing workflows, and ensuring prompt nurse attention when required. EyeLink offers an affordable, scalable, and cross-platform communication tool, significantly improving patient dignity and the overall healthcare experience.

**Components**
The EyeLink system consists of three interconnected components:

**1. Desktop Application (Patient Interface)**
This is the client-side application responsible for capturing and processing real-time eye-tracking data from the patient.

**Technology**: Python, OpenCV, Dlib (shape_predictor_68_face_landmarks.dat), PyQt5.

**Functionality:**

Real-time Eye Tracking: Integrates with standard HD webcams to capture a patient's gaze coordinates in real-time.

Data Processing: Processes raw eye-gaze data by interpreting gaze direction and blinks through Eye Aspect Ratio (EAR) calculation (a ratio > 4.7 indicates a blink) and a custom gaze ratio calculation for horizontal gaze (based on white pixel counts in thresholded eye regions).

GUI Interaction: Provides an intuitive graphical user interface for patients to display and track gaze-based options and issue commands via eye gestures, such as a sequence of three blinks for selection and gaze direction (left/right) for navigation.

Data Transmission: Securely sends processed eye-gaze data to the backend service for analysis and nurse assignment continuously and in real-time.

**2. Backend Service**
This is the central hub that receives eye-tracking data from the desktop application, applies business logic for nurse assignment, and manages patient and nurse information.

**Technology:** Python/Django/Django REST Framework.

**Functionality:**

Data Ingestion: Receives real-time eye-gaze data streams from the desktop application.

Nurse Assignment Logic: Implements core logic for assigning nurses based on patient signals, patient needs, and nurse availability/workload.

Database Integration: Utilizes SQLite for local development and Azure SQL for cloud deployment to store nurse profiles, availability, patient information, historical eye-gaze data, and assignment logs.

API Endpoints: Exposes REST APIs for the desktop app to send data and for other systems to query assignments or update nurse/patient status. Authentication is managed with JWT tokens.

Real-time Communication: Communicates real-time nurse assignments and patient 'calls' to nurses via Firebase Cloud Messaging (FCM). It also uses Firebase Firestore for real-time updates to the patient's desktop application.

**3. Nurse Mobile Application**
This is the mobile application used by nurses to receive real-time notifications and manage patient 'calls' and assignments.

**Technology:** Flutter (Dart).

**Functionality:**

Firebase Integration: Connects to Firebase Cloud Messaging (FCM) to receive real-time push notifications and data updates from the Backend Service regarding patient calls and assignments.

Notification Display: Clearly displays incoming patient requests, including patient ID and the nature of the request (e.g., "Patient X needs assistance," "Patient Y called for water").

Assignment Management: Allows nurses to acknowledge, accept, or update the status of assignments through the NurseDashboardScreen.

User Interface: Intuitive and easy-to-use interface designed for quick access to critical patient information and actions in a healthcare environment.

Authentication: Handles nurse login and registration, communicating with the Django backend via REST API calls and authenticating with JWT tokens stored in shared_preferences.

**How It Works**
The Desktop Application is installed on a device accessible to the patient (e.g., mounted near their bed, integrated into a wheelchair system). It continuously captures eye-gaze data in real-time using an integrated HD webcam, translating the patient's focus and blink patterns into actionable signals.

This real-time eye-gaze data is streamed to the Backend Service.

The Backend Service processes the incoming eye-gaze data, interpreting the patient's signals or 'calls.' Based on pre-defined logic, it determines the appropriate nurse to assign or notify.

If an assignment or notification is triggered, the backend updates its internal state and immediately pushes this information (e.g., 'Patient X needs assistance,' 'Patient Y called for water') via Firebase Cloud Messaging to the relevant nurse's Flutter mobile application, ensuring real-time awareness.

The system primarily operates in an online mode, enabling instantaneous communication between patients, nurses, and the backend.
