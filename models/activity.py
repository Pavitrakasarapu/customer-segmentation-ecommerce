from datetime import datetime, timedelta
import json
from models import db


class CustomerActivity(db.Model):
    __tablename__ = "customer_activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    customer_name = db.Column(db.String(100), nullable=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="activities")
    product = db.relationship("Product")
    category = db.relationship("Category")

    @property
    def metadata_dict(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {"raw": self.metadata_json}

    @metadata_dict.setter
    def metadata_dict(self, val):
        self.metadata_json = json.dumps(val) if val else None

    @classmethod
    def log(cls, activity_type: str, user=None, product_id=None, category_id=None, metadata=None):
        """Helper to log an activity seamlessly"""
        activity = cls(
            user_id=user.id if user and hasattr(user, "id") and user.is_authenticated else None,
            customer_name=user.name if user and hasattr(user, "name") and user.is_authenticated else "Guest",
            activity_type=activity_type,
            product_id=product_id,
            category_id=category_id,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return activity

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "customer_name": self.customer_name,
            "activity_type": self.activity_type,
            "product_name": self.product.name if self.product else None,
            "category_name": self.category.name if self.category else None,
            "metadata": self.metadata_dict,
            "timestamp": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def __repr__(self):
        return f"<CustomerActivity {self.activity_type} user={self.user_id} @ {self.created_at}>"


class LoginSession(db.Model):
    __tablename__ = "login_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    session_token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    login_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    logout_time = db.Column(db.DateTime, nullable=True)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="login_sessions")

    @classmethod
    def clean_stale_sessions(cls, timeout_minutes: int = 15):
        """Mark sessions inactive if last_active is older than timeout_minutes"""
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        cls.query.filter(cls.is_active == True, cls.last_active < cutoff).update({"is_active": False, "logout_time": datetime.utcnow()})
        db.session.commit()

    def update_presence(self):
        self.last_active = datetime.utcnow()
        self.is_active = True
        db.session.commit()

    def end_session(self):
        self.is_active = False
        self.logout_time = datetime.utcnow()
        self.last_active = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f"<LoginSession user={self.user_id} active={self.is_active}>"
