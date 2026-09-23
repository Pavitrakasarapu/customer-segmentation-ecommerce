from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import func
from models import db
from models.user import User
from models.order import Order, OrderItem
from models.product import Product
from models.cart import WishlistItem, CartItem
from models.activity import CustomerActivity

FEATURE_COLUMNS = [
    "recency_days",
    "frequency",
    "monetary",
    "avg_order_value",
    "product_views",
    "searches",
    "wishlist_count",
    "cart_additions",
    "categories_bought",
    "recent_activity_count"
]


def extract_single_customer_features(user_id: int) -> dict:
    """Extract RFM and behavioral feature dictionary for a single user"""
    user = db.session.get(User, user_id)
    if not user:
        return {}

    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    # Orders summary
    orders = Order.query.filter_by(user_id=user_id).all()
    frequency = len(orders)
    monetary = float(sum(o.total_amount for o in orders))
    avg_order_value = monetary / frequency if frequency > 0 else 0.0

    if orders:
        latest_order = max(orders, key=lambda o: o.created_at)
        recency_days = float((now - latest_order.created_at).total_seconds() / 86400.0)
    else:
        # If no orders, recency based on registration or last activity
        recency_days = float((now - user.created_at).total_seconds() / 86400.0)

    # Categories bought
    order_ids = [o.id for o in orders]
    if order_ids:
        categories_bought = db.session.query(Product.category_id).join(
            OrderItem, OrderItem.product_id == Product.id
        ).filter(OrderItem.order_id.in_(order_ids)).distinct().count()
    else:
        categories_bought = 0

    # Activities summary
    activities = CustomerActivity.query.filter_by(user_id=user_id).all()
    product_views = sum(1 for a in activities if a.activity_type == "PRODUCT_VIEW")
    searches = sum(1 for a in activities if a.activity_type == "SEARCH")
    cart_additions = sum(1 for a in activities if a.activity_type == "CART_ADD")
    recent_activity_count = sum(1 for a in activities if a.created_at >= seven_days_ago)

    # Wishlist items
    wishlist_count = WishlistItem.query.filter_by(user_id=user_id).count()

    return {
        "user_id": user_id,
        "customer_name": user.name,
        "recency_days": max(0.0, recency_days),
        "frequency": frequency,
        "monetary": max(0.0, monetary),
        "avg_order_value": max(0.0, avg_order_value),
        "product_views": product_views,
        "searches": searches,
        "wishlist_count": wishlist_count,
        "cart_additions": cart_additions,
        "categories_bought": categories_bought,
        "recent_activity_count": recent_activity_count,
    }


def extract_all_customer_features() -> pd.DataFrame:
    """Extract features for all registered customers"""
    customers = User.query.filter_by(role="customer").all()
    rows = []
    for customer in customers:
        feats = extract_single_customer_features(customer.id)
        if feats:
            rows.append(feats)

    if not rows:
        return pd.DataFrame(columns=["user_id", "customer_name"] + FEATURE_COLUMNS)
    return pd.DataFrame(rows)
