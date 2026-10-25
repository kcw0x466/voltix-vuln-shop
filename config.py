import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv('VOLTIX_SECRET') or os.urandom(32).hex()
    DATABASE = str(Path(os.getenv('VOLTIX_DB', ROOT / 'instance/voltix.sqlite3')).resolve())
    UPLOAD_FOLDER = str(ROOT / 'instance/uploads')
    LAB_FILES = str(ROOT / 'instance/lab-files')
    LAB_MODE = os.getenv('VOLTIX_LAB_MODE', '0') == '1'
    VULNS = os.getenv('VOLTIX_VULNS', 'all')
    WORKER_URL = os.getenv('VOLTIX_WORKER_URL', '')
    WORKER_TOKEN = os.getenv('VOLTIX_WORKER_TOKEN', '')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
