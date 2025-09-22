from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    bags_sold = db.Column(db.Integer, default=0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    discount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, used
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.String(20))  # 'vendor', 'sponsor', 'admin'
    approved_at = db.Column(db.DateTime)
    used_at = db.Column(db.DateTime)
    scanned_count = db.Column(db.Integer, default=0)

class ScanLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'), nullable=False)
    user_agent = db.Column(db.String(200))
    ip = db.Column(db.String(45))
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)