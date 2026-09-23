from datetime import datetime
from models import db


class CustomerSegment(db.Model):
    __tablename__ = "customer_segments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    segment_label = db.Column(db.String(50), nullable=False, default="NEW CUSTOMER")
    cluster_id = db.Column(db.Integer, default=0, nullable=False)
    
    # RFM features
    recency_days = db.Column(db.Float, default=0.0, nullable=False)
    frequency = db.Column(db.Integer, default=0, nullable=False)
    monetary = db.Column(db.Float, default=0.0, nullable=False)
    avg_order_value = db.Column(db.Float, default=0.0, nullable=False)
    
    # Behavioral features
    product_views = db.Column(db.Integer, default=0, nullable=False)
    searches = db.Column(db.Integer, default=0, nullable=False)
    wishlist_count = db.Column(db.Integer, default=0, nullable=False)
    cart_additions = db.Column(db.Integer, default=0, nullable=False)
    categories_bought = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="segment")

    @property
    def badge_color(self) -> str:
        """Returns Bootstrap color class for segment badges"""
        mapping = {
            "HIGH VALUE CUSTOMER": "success",
            "REGULAR CUSTOMER": "info",
            "NEW CUSTOMER": "primary",
            "AT-RISK CUSTOMER": "danger",
            "DISCOUNT SEEKER": "warning",
        }
        return mapping.get(self.segment_label, "secondary")

    @property
    def explanation(self) -> str:
        """Plain English explanation for why customer is in this segment"""
        if self.segment_label == "HIGH VALUE CUSTOMER":
            return "Your segment is HIGH VALUE CUSTOMER because your order frequency and total spending are high with regular active purchases."
        elif self.segment_label == "REGULAR CUSTOMER":
            return "Your segment is REGULAR CUSTOMER because you make steady, consistent purchases with consistent engagement across our store."
        elif self.segment_label == "NEW CUSTOMER":
            return "Your segment is NEW CUSTOMER because your account was recently created and you are exploring our products."
        elif self.segment_label == "AT-RISK CUSTOMER":
            return "Your segment is AT-RISK CUSTOMER because your last purchase was a long time ago. We'd love to welcome you back!"
        elif self.segment_label == "DISCOUNT SEEKER":
            return "Your segment is DISCOUNT SEEKER because you actively browse items, maintain high wishlist and cart activity, and look for great deals."
        return "Your segment is based on your recent shopping behavior, order frequency, and engagement."

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "customer_name": self.user.name if self.user else "",
            "segment_label": self.segment_label,
            "cluster_id": self.cluster_id,
            "badge_color": self.badge_color,
            "recency_days": round(self.recency_days, 1),
            "frequency": self.frequency,
            "monetary": round(self.monetary, 2),
            "avg_order_value": round(self.avg_order_value, 2),
            "product_views": self.product_views,
            "searches": self.searches,
            "wishlist_count": self.wishlist_count,
            "cart_additions": self.cart_additions,
            "categories_bought": self.categories_bought,
            "explanation": self.explanation,
            "last_updated": self.last_updated.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def __repr__(self):
        return f"<CustomerSegment user={self.user_id} label='{self.segment_label}'>"
