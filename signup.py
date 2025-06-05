import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer

class SignupWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.setWindowTitle("Sign Up")
        self.setGeometry(300, 300, 500, 600) # Increased height for more fields
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
        self.main_layout.setSpacing(20)

        self.title = QLabel("SIGN UP")
        self.title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title)

        form_container = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        form_layout.setAlignment(Qt.AlignCenter)
        form_container.setLayout(form_layout)
        form_container.setFixedWidth(360)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username (required)")
        form_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password (required)")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_input)

        self.password2_input = QLineEdit()
        self.password2_input.setPlaceholderText("Confirm Password (required)")
        self.password2_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password2_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone Number (optional)")
        form_layout.addWidget(self.phone_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Address (optional)")
        form_layout.addWidget(self.address_input)

        self.bed_number_input = QLineEdit()
        self.bed_number_input.setPlaceholderText("Bed Number (optional)")
        form_layout.addWidget(self.bed_number_input)

        self.signup_button = QPushButton("SIGN UP")
        self.signup_button.clicked.connect(self.handle_signup)
        form_layout.addWidget(self.signup_button)

        self.goto_login_button = QPushButton("Already have an account? Log In")
        self.goto_login_button.setStyleSheet("QPushButton { background-color: transparent; color: white; font-size: 10pt; border: none; } QPushButton:hover { text-decoration: underline; }")
        self.goto_login_button.clicked.connect(self.controller.show_login_window)
        form_layout.addWidget(self.goto_login_button)

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

    def handle_signup(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        password2 = self.password2_input.text()
        phone_number = self.phone_input.text().strip()
        address = self.address_input.text().strip()
        bed_number = self.bed_number_input.text().strip()

        if not username or not password or not password2:
            QMessageBox.warning(self, "Error", "Username and password fields are required.")
            return
        if password != password2:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        self.overlay.setVisible(True)
        self.progress_bar.setVisible(True)
        self.adjust_overlay_and_progress_bar_position()

        # Simulate network request
        QTimer.singleShot(500, lambda: self.perform_signup(username, password, password2, phone_number, address, bed_number))

    def perform_signup(self, username, password, password2, phone_number, address, bed_number):
        try:
            data = {
                "username": username,
                "password": password,
                "password2": password2
            }
            if phone_number:
                data["phone_number"] = phone_number
            if address:
                data["address"] = address
            if bed_number:
                data["bed_number"] = bed_number

            response = requests.post(f"{self.base_url}/api/patients/register/", json=data)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            response_data = response.json()

            QMessageBox.information(self, "Success", response_data.get("message", "Registration successful. Please log in."))
            self.clear_fields()
            self.controller.show_login_window()

        except requests.exceptions.RequestException as e:
            error_message = "An error occurred during registration."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("message", error_message)
                    if e.response.status_code == 400:
                        if "username" in error_data:
                            error_message = "Username already exists or is invalid."
                        elif "password" in error_data:
                            error_message = "Password invalid."
                        elif "non_field_errors" in error_data:
                            error_message = error_data["non_field_errors"][0]
                except ValueError:
                    error_message = f"Server error: {e.response.status_code} {e.response.text}"
            else:
                error_message = f"Network error: {e}"
            QMessageBox.warning(self, "Error", error_message)
        finally:
            self.overlay.setVisible(False)
            self.progress_bar.setVisible(False)

    def clear_fields(self):
        self.username_input.clear()
        self.password_input.clear()
        self.password2_input.clear()
        self.phone_input.clear()
        self.address_input.clear()
        self.bed_number_input.clear()

    def adjust_overlay_and_progress_bar_position(self):
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        progress_width = 200
        self.progress_bar.setGeometry(self.width() // 2 - progress_width // 2, self.height() // 2 - 20, progress_width, 20)