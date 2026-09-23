from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user

from models import db
from models.user import User
from models.activity import LoginSession, CustomerActivity
from models.segment import CustomerSegment
from models.product import Product
from models.order import Order
from ml.segmenter import recalculate_customer_segment

segmentation_bp = Blueprint("segmentation", __name__)


def get_personalized_recommendations(segment_label: str):
    """Generate smart personalized product recommendations based on segment"""
    if segment_label == "HIGH VALUE CUSTOMER":
        # Premium/luxury items
        return Product.query.order_by(Product.price.desc()).limit(4).all()
    elif segment_label == "DISCOUNT SEEKER":
        # Budget-friendly items
        return Product.query.order_by(Product.price.asc()).limit(4).all()
    elif segment_label == "AT-RISK CUSTOMER":
        # Popular high-stock staple items
        return Product.query.order_by(Product.stock.desc()).limit(4).all()
    else:  # NEW CUSTOMER or REGULAR CUSTOMER
        # Trending/newest items
        return Product.query.order_by(Product.id.desc()).limit(4).all()


@segmentation_bp.route("/segmentation")
@login_required
def index():
    # Clean stale sessions older than 10 minutes
    LoginSession.clean_stale_sessions(timeout_minutes=10)

    # Ensure the current user has an up-to-date segment
    my_segment = recalculate_customer_segment(current_user.id)

    # Query active customer sessions
    active_sessions = LoginSession.query.join(User).filter(
        LoginSession.is_active == True,
        User.role == "customer"
    ).all()

    # Build privacy-compliant active customer list (ONLY name and current segment)
    active_customers = []
    seen_user_ids = set()
    for sess in active_sessions:
        if sess.user_id not in seen_user_ids:
            seen_user_ids.add(sess.user_id)
            seg = CustomerSegment.query.filter_by(user_id=sess.user_id).first()
            label = seg.segment_label if seg else "NEW CUSTOMER"
            badge = seg.badge_color if seg else "primary"
            active_customers.append({
                "name": sess.user.name,
                "segment_label": label,
                "badge_color": badge,
                "is_current_user": sess.user_id == current_user.id
            })

    recommendations = get_personalized_recommendations(my_segment.segment_label)

    return render_template(
        "segmentation/index.html",
        active_customers=active_customers,
        active_count=len(active_customers),
        my_segment=my_segment,
        recommendations=recommendations
    )


@segmentation_bp.route("/segmentation/my-segment")
@login_required
def my_segment():
    # Ensure freshly calculated
    seg = recalculate_customer_segment(current_user.id)
    recommendations = get_personalized_recommendations(seg.segment_label)

    # Calculate additional friendly stats
    orders = Order.query.filter_by(user_id=current_user.id).all()
    last_order = max(orders, key=lambda o: o.created_at) if orders else None

    # Purchase frequency description
    if seg.frequency >= 5:
        purchase_freq = "Frequent Shopper (Multiple orders per month)"
    elif seg.frequency >= 2:
        purchase_freq = "Regular Shopper"
    elif seg.frequency == 1:
        purchase_freq = "First-time Buyer"
    else:
        purchase_freq = "Browsing / Prospect"

    # Spending level description
    if seg.monetary >= 1500:
        spending_level = "High Tier Spending"
    elif seg.monetary >= 400:
        spending_level = "Moderate Tier Spending"
    elif seg.monetary > 0:
        spending_level = "Entry Tier Spending"
    else:
        spending_level = "No Purchases Yet"

    return render_template(
        "segmentation/my_segment.html",
        seg=seg,
        last_order=last_order,
        purchase_freq=purchase_freq,
        spending_level=spending_level,
        recommendations=recommendations
    )
