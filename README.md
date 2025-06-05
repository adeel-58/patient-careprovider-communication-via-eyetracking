**EyeLink: Patient-CareProvider Communication via Real-time Eye-Tracking**

**Project Overview**
The EyeGazeApp is a revolutionary system designed to enhance patient care and communication for individuals with severe disabilities (e.g., quadriplegia, unable to speak), by leveraging real-time eye-tracking technology. This project enables patients to communicate their needs or "call" for assistance through their eye movements, which are captured by a desktop application and processed by a backend service for dynamic nurse assignment.

The core idea is to use eye-gaze data from these patients to provide a direct, non-verbal method of signaling needs, optimizing workflows, and ensuring prompt nurse attention when required.

**Components**
1. Desktop Application (EyeGazeApp Folder)
This is the client-side application responsible for capturing and processing real-time eye-tracking data from the patient.

Technology: Python, Dlib, shape_predictor_68_face_landmarks

Functionality:

Real-time Eye Tracking: Integrates with eye-tracking hardware/SDKs to capture a patient's gaze coordinates in real-time.

Data Processing: Processes raw eye-gaze data, potentially filtering noise, calculating gaze duration, heatmaps, or areas of interest (AOIs) that correspond to patient needs or commands (e.g., a "Call Nurse" button, options for specific requests like "water," "pain medicine").

Data Transmission: Securely sends processed eye-gaze data to the backend service for analysis and nurse assignment. The transmission is continuous and real-time.

2. Backend Service (Backend Folder)
This is the central hub that receives eye-tracking data from the desktop application, applies business logic for nurse assignment, and manages patient and nurse information.

Technology: Python/Flask/Django

Functionality:

Data Ingestion: Receives real-time eye-gaze data streams from the desktop application.

Nurse Assignment Logic: Implements the core logic for assigning nurses. This logic could be based on:

Patient Signaling: Interpreting specific eye-gaze patterns from patients as signals for assistance (e.g., focusing on a 'call nurse' button, specific blink patterns, or dwelling on an object indicating a need).

Patient Needs: Dynamically adjusting assignments based on real-time assessment of patient status derived from eye-gaze data.

Nurse Availability/Workload: Integrating with a nurse scheduling or availability system.

Database Integration: Sqlite3 to store:

Nurse profiles and availability.

Patient information.

Historical eye-gaze data (for auditing or analytics).

Assignment logs.

API Endpoints: Exposes APIs for the desktop app to send data and potentially for other systems to query assignments or update nurse/patient status.

Real-time Communication: Communicates real-time nurse assignments and patient 'calls' to nurses via Firebase. These notifications are received by a dedicated Flutter mobile application on the nurses' devices, informing them which patient requires attention and why.

3. Nurse Mobile Application (Flutter App)
This is the mobile application used by nurses to receive real-time notifications and manage patient 'calls' and assignments.

Technology: Flutter (Dart)

Functionality:

Firebase Integration: Connects to Firebase to receive real-time push notifications and data updates from the Backend Service regarding patient calls and assignments.

Notification Display: Clearly displays incoming patient requests, including patient ID and the nature of the request (e.g., "Patient X needs assistance," "Patient Y called for water").

Assignment Management: Allows nurses to acknowledge, accept, or update the status of assignments.

User Interface: Intuitive and easy-to-use interface designed for quick access to critical patient information and actions in a healthcare environment.

How It Works
The Desktop Application is installed on a device accessible to the patient (e.g., mounted near their bed, integrated into a wheelchair system, infront of patient's bed). It captures their eye-gaze data, enabling them to signal specific needs or 'call' for assistance.

It continuously captures eye-gaze data in real-time using integrated eye-tracking hardware, translating the patient's focus into actionable signals.

This real-time eye-gaze data is streamed to the Backend Service.

The Backend Service processes the incoming eye-gaze data, interpreting the patient's signals or 'calls.' Based on pre-defined logic, it determines the appropriate nurse to assign or notify.

If an assignment or notification is triggered, the backend updates its internal state and immediately pushes this information (e.g., 'Patient X needs assistance,' 'Patient Y called for water') via Firebase to the relevant nurse's Flutter mobile application, ensuring real-time awareness.

