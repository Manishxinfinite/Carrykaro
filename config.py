import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "supersecretkey"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    QR_FOLDER = os.path.join(BASE_DIR, 'static', 'qrcodes')