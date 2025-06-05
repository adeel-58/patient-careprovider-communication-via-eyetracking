# apps/notifications/utils.py

import firebase_admin
from firebase_admin import credentials, messaging, firestore
from django.conf import settings
import os

_firebase_app = None # To store the initialized app

def initialize_firebase():
    """Initializes the Firebase Admin SDK if not already initialized."""
    global _firebase_app
    if _firebase_app is None:
        try:
            # Ensure the path is correct
            cred_path = settings.FIREBASE_CREDENTIALS_PATH
            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")

            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            _firebase_app = None # Reset to None if initialization fails

def get_fcm_messaging():
    """Returns the Firebase Cloud Messaging service."""
    if _firebase_app is None:
        initialize_firebase()
    if _firebase_app:
        return messaging
    return None

def get_firestore_db():
    """Returns the Firestore database client."""
    if _firebase_app is None:
        initialize_firebase()
    if _firebase_app:
        return firestore.client()
    return None

# Call initialize_firebase when the module is imported
# This ensures it's ready when get_fcm_messaging or get_firestore_db are called
initialize_firebase()