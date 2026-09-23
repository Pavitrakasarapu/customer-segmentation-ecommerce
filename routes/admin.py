import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db
from models.user import User
from models.product import Product, Category
from models.order import Order, OrderItem
from models.cart import CartItem, WishlistItem
from models.activity import CustomerActivity, LoginSession
from models.segment import CustomerSegment
from routes import admin_required
from ml.segmenter import SegmentationEngine, recalculate_all_segments
from train_model import train_model

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    # Clean stale sessions
    LoginSession.clean_stale_sessions(timeout_minutes=10)

    # Core KPIs
    total_customers = User.query.filter_by(role="customer").count()
    active_customers = db.session.query(
        func.count(func.distinct(LoginSession.user_id))
    ).join(User, User.id == LoginSession.user_id).filter(
        LoginSession.is_active == True,
        User.role == "customer"
    ).scalar() or 0

    total_orders = Order.query.count()
    total_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0.0)).scalar()

    # Segment Breakdown
    segments = ["HIGH VALUE CUSTOMER", "REGULAR CUSTOMER", "NEW CUSTOMER", "AT-RISK CUSTOMER", "DISCOUNT SEEKER"]
    segment_counts = {s: 0 for s in segments}
    seg_records = db.session.query(
        CustomerSegment.segment_label, func.count(CustomerSegment.id)
    ).join(User, User.id == CustomerSegment.user_id).filter(
        User.role == "customer"
    ).group_by(CustomerSegment.segment_label).all()
    for label, count in seg_records:
        if label in segment_counts:
            segment_counts[label] = count

    # Revenue by Segment & Orders by Segment
    revenue_by_segment = {s: 0.0 for s in segments}
    orders_by_segment = {s: 0 for s in segments}
    rev_query = db.session.query(
        CustomerSegment.segment_label,
        func.coalesce(func.sum(Order.total_amount), 0.0),
        func.count(Order.id)
    ).join(User, User.id == CustomerSegment.user_id).join(
        Order, Order.user_id == User.id
    ).filter(
        User.role == "customer"
    ).group_by(CustomerSegment.segment_label).all()

    for label, rev, ord_cnt in rev_query:
        if label in revenue_by_segment:
            revenue_by_segment[label] = round(float(rev), 2)
            orders_by_segment[label] = ord_cnt

    # Activity over last 7 days
    today = datetime.utcnow().date()
    activity_dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    activity_date_labels = [d.strftime("%b %d") for d in activity_dates]
    activity_counts_per_day = []

    for d in activity_dates:
        start_d = datetime(d.year, d.month, d.day, 0, 0, 0)
        end_d = datetime(d.year, d.month, d.day, 23, 59, 59)
        cnt = CustomerActivity.query.filter(
            CustomerActivity.created_at >= start_d,
            CustomerActivity.created_at <= end_d
        ).count()
        activity_counts_per_day.append(cnt)

    # Category popularity (by product views / customer activities)
    categories = Category.query.order_by(Category.id.asc()).all()
    category_labels = [c.name for c in categories]
    category_views = [CustomerActivity.query.filter_by(category_id=c.id).count() for c in categories]

    # Live active customers
    live_sessions = LoginSession.query.join(User).filter(
        LoginSession.is_active == True,
        User.role == "customer"
    ).order_by(LoginSession.last_active.desc()).all()

    active_customer_list = []
    seen = set()
    for s in live_sessions:
        if s.user_id not in seen:
            seen.add(s.user_id)
            seg = CustomerSegment.query.filter_by(user_id=s.user_id).first()
            active_customer_list.append({
                "user": s.user,
                "segment": seg.segment_label if seg else "NEW CUSTOMER",
                "badge_color": seg.badge_color if seg else "primary",
                "last_active": s.last_active.strftime("%H:%M:%S")
            })

    # Recent activities
    recent_activities = CustomerActivity.query.order_by(CustomerActivity.created_at.desc()).limit(8).all()

    chart_data = {
        "segment_labels": list(segment_counts.keys()),
        "segment_counts": list(segment_counts.values()),
        "revenue_by_segment": list(revenue_by_segment.values()),
        "orders_by_segment": list(orders_by_segment.values()),
        "activity_dates": activity_date_labels,
        "activity_counts": activity_counts_per_day,
        "category_labels": category_labels,
        "category_views": category_views,
    }

    return render_template(
        "admin/dashboard.html",
        total_customers=total_customers,
        active_customers=active_customers,
        total_orders=total_orders,
        total_revenue=round(total_revenue, 2),
        segment_counts=segment_counts,
        live_customers=active_customer_list,
        recent_activities=recent_activities,
        chart_data=chart_data
    )


@admin_bp.route("/customers")
@admin_required
def customers():
    search = request.args.get("q", "").strip()
    seg_filter = request.args.get("segment", "").strip()

    query = User.query.filter_by(role="customer")
    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%")
            )
        )

    all_customers = query.order_by(User.id.asc()).all()
    customer_rows = []

    for c in all_customers:
        seg = CustomerSegment.query.filter_by(user_id=c.id).first()
        if seg_filter and seg and seg.segment_label != seg_filter:
            continue

        orders = Order.query.filter_by(user_id=c.id).all()
        spending = sum(o.total_amount for o in orders)
        active_sess = LoginSession.query.filter_by(user_id=c.id, is_active=True).first()
        latest_sess = LoginSession.query.filter_by(user_id=c.id).order_by(LoginSession.login_time.desc()).first()

        customer_rows.append({
            "user": c,
            "segment": seg,
            "orders_count": len(orders),
            "spending": round(spending, 2),
            "is_active": active_sess is not None,
            "last_login": latest_sess.login_time.strftime("%Y-%m-%d %H:%M") if latest_sess else "Never"
        })

    return render_template(
        "admin/customers.html",
        customers=customer_rows,
        search=search,
        seg_filter=seg_filter
    )


@admin_bp.route("/customers/<int:user_id>")
@admin_required
def customer_detail(user_id: int):
    customer = User.query.filter_by(id=user_id, role="customer").first_or_404()
    segment = CustomerSegment.query.filter_by(user_id=customer.id).first()
    orders = Order.query.filter_by(user_id=customer.id).order_by(Order.created_at.desc()).all()
    cart_items = CartItem.query.filter_by(user_id=customer.id).all()
    wishlist_items = WishlistItem.query.filter_by(user_id=customer.id).all()
    login_sessions = LoginSession.query.filter_by(user_id=customer.id).order_by(LoginSession.login_time.desc()).limit(10).all()
    activities = CustomerActivity.query.filter_by(user_id=customer.id).order_by(CustomerActivity.created_at.desc()).limit(50).all()

    total_spent = sum(o.total_amount for o in orders)

    return render_template(
        "admin/customer_detail.html",
        customer=customer,
        segment=segment,
        orders=orders,
        total_spent=round(total_spent, 2),
        cart_items=cart_items,
        wishlist_items=wishlist_items,
        login_sessions=login_sessions,
        activities=activities
    )


@admin_bp.route("/activities")
@admin_required
def activities():
    page = request.args.get("page", 1, type=int)
    activity_type = request.args.get("type", "").strip()
    user_id = request.args.get("user_id", type=int)
    category_id = request.args.get("category_id", type=int)

    query = CustomerActivity.query

    if activity_type:
        query = query.filter_by(activity_type=activity_type)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if category_id:
        query = query.filter_by(category_id=category_id)

    pagination = query.order_by(CustomerActivity.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    
    activity_types = [
        "LOGIN", "LOGOUT", "PRODUCT_VIEW", "SEARCH", "CATEGORY_VIEW",
        "WISHLIST_ADD", "WISHLIST_REMOVE", "CART_ADD", "CART_REMOVE",
        "CART_UPDATE", "CHECKOUT", "ORDER_PLACED", "ORDER_VIEW", "PROFILE_VIEW"
    ]
    categories = Category.query.all()
    customers = User.query.filter_by(role="customer").order_by(User.name.asc()).all()

    return render_template(
        "admin/activities.html",
        pagination=pagination,
        activity_types=activity_types,
        categories=categories,
        customers=customers,
        selected_type=activity_type,
        selected_user_id=user_id,
        selected_cat_id=category_id
    )


@admin_bp.route("/retrain", methods=["POST"])
@admin_required
def retrain():
    try:
        success = train_model(n_clusters=5)
        if success:
            flash("Machine Learning KMeans model successfully retrained and customer segments updated!", "success")
        else:
            flash("Model training could not be completed. Please check data.", "warning")
    except Exception as e:
        flash(f"Error during model retraining: {e}", "danger")

    return redirect(url_for("admin.dashboard"))
