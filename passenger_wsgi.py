import sys
import os

# Dodaj katalog aplikacji do ścieżki Pythona
sys.path.insert(0, os.path.dirname(__file__))

from app import app as application
