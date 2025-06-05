import requests # New: Import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, QApplication, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer
# from desktopGUI import AdvancedDesignApp # No longer directly importing AdvancedDesignApp

class LoginWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(300, 300, 500, 400)
        self.setStyleSheet("""
            QWidget { background-color: #013220; font-family: 'Poppins', sans-serif; }
            QLineEdit { padding: 10px; font-size: 12pt; border-radius: 10px; border: 2px solid #2e8b57; color: white; }
            QLineEdit::placeholder { color: #cccccc; }
            QPushButton { background-color: #2e8b57; color: white; padding: 10px; border-radius: 10px; font-size: 14pt; }
            QPushButton:hover { background-color: #3cb371; }
            QLabel { color: white; font-size: 20pt; font-weight: 600; }
            QProgressBar {
                border: 2px solid #2e8b57;
                border-radius: 10px;
                background-color: #1c3c2b;
                text-align: center;
                height: 20px;
                width: 200px;
                margin: 0 auto;
            }
            QProgressBar::chunk {
                background-color: #3cb371;
                width: 20px;
                margin: 0.5px;
            }
        """)

        self.controller = controller
        self.base_url = "http://127.0.0.1:8000" # Your backend URL

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setSpacing(30)

        self.title = QLabel("LOGIN")
        self.title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title)

        form_container = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        form_layout.setAlignment(Qt.AlignCenter)
        form_container.setLayout(form_layout)
        form_container.setFixedWidth(360)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        form_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_input)

        self.login_button = QPushButton("LOG IN")
        self.login_button.clicked.connect(self.handle_login)
        form_layout.addWidget(self.login_button)

        self.goto_signup_button = QPushButton("Don't have an account? Sign Up") # New button
        self.goto_signup_button.setStyleSheet("QPushButton { background-color: transparent; color: white; font-size: 10pt; border: none; } QPushButton:hover { text-decoration: underline; }")
        self.goto_signup_button.clicked.connect(self.controller.show_signup_window) # Connect to show signup
        form_layout.addWidget(self.goto_signup_button)

        self.main_layout.addWidget(form_container)

        self.setLayout(self.main_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.overlay.setVisible(False)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password.")
            return

        self.overlay.setVisible(True)
        self.progress_bar.setVisible(True)
        self.adjust_overlay_and_progress_bar_position()

        # Simulate network request delay before actual login
        QTimer.singleShot(500, lambda: self.perform_login(username, password))

    def perform_login(self, username, password):
        try:
            data = {
                "username": username,
                "password": password
            }
            response = requests.post(f"{self.base_url}/api/patients/login/", json=data)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            response_data = response.json()

            # Save tokens and patient info to the controller
            self.controller.access_token = response_data.get("access_token")
            self.controller.patient_id = response_data.get("patient_id")
            self.controller.patient_username = response_data.get("username")
            # Assuming these might be returned by login or fetched later
            # For now, let's assume bed_number might come from login for simplicity if your API provides it
            # If not, it will be None, and you might need to fetch it from a patient profile API
            self.controller.patient_bed_number = response_data.get("bed_number")

            QMessageBox.information(self, "Success", response_data.get("message", "Logged in successfully!"))
            self.accept_login()

        except requests.exceptions.RequestException as e:
            error_message = "An error occurred during login."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("message", error_message)
                    if e.response.status_code == 401:
                        error_message = "Invalid username or password."
                except ValueError:
                    error_message = f"Server error: {e.response.status_code} {e.response.text}"
            else:
                error_message = f"Network error: {e}"
            QMessageBox.warning(self, "Error", error_message)
        finally:
            self.overlay.setVisible(False)
            self.progress_bar.setVisible(False)

    def adjust_overlay_and_progress_bar_position(self):
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        progress_width = 200
        self.progress_bar.setGeometry(self.width() // 2 - progress_width // 2, self.height() // 2 - 20, progress_width, 20)

    def accept_login(self):
        self.username_input.clear()
        self.password_input.clear()
        self.controller.show_main_window()
        # self.close() # main_window handles closing login