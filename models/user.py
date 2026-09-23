from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from models import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")  # 'customer' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan", lazy="select")
    cart_items = db.relationship("CartItem", back_populates="user", cascade="all, delete-orphan", lazy="select")
    wishlist_items = db.relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan", lazy="select")
    activities = db.relationship("CustomerActivity", back_populates="user", cascade="all, delete-orphan", lazy="select")
    login_sessions = db.relationship("LoginSession", back_populates="user", cascade="all, delete-orphan", lazy="select")
    segment = db.relationship("CustomerSegment", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="select")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    ADMIN_EMAIL = "pavitrakasarapu@gmail.com"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin" and (self.email or "").strip().lower() == self.ADMIN_EMAIL.lower()

    @property
    def is_active(self) -> bool:
        return self.is_active_account

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
