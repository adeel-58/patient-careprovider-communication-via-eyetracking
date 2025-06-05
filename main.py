from PyQt5.QtWidgets import QApplication
from login import LoginWindow
from signup import SignupWindow # New: Import SignupWindow
from desktopGUI import AdvancedDesignApp
import sys

class AppController:
    def __init__(self):
        self.login_window = LoginWindow(self)
        self.signup_window = SignupWindow(self) # New: Initialize SignupWindow
        self.login_window.show()

        # Store access token and patient details globally after login
        self.access_token = None
        self.patient_id = None
        self.patient_username = None
        self.patient_phone_number = None # Assuming these might be needed later
        self.patient_address = None
        self.patient_bed_number = None

    def show_login_window(self):
        self.signup_window.hide()
        self.login_window.show()

    def show_signup_window(self):
        self.login_window.hide()
        self.signup_window.show()

    def show_main_window(self):
        # Only create and show the main window once the user has logged in
        # Pass patient data and access token to the main app
        self.main_window = AdvancedDesignApp(
            access_token=self.access_token,
            patient_id=self.patient_id,
            patient_username=self.patient_username,
            patient_bed_number=self.patient_bed_number # Pass bed number
        )
        self.main_window.showMaximized()
        self.login_window.close() # Close login and signup windows
        self.signup_window.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    sys.exit(app.exec_())