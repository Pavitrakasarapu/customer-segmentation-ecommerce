from datetime import datetime
from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required

from models import db
from models.user import User
from models.activity import LoginSession
from models.segment import CustomerSegment
from ml.segmenter import recalculate_customer_segment

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    """Client heartbeat ping to keep session presence active"""
    if not current_user.is_authenticated:
        return jsonify({"status": "anonymous"}), 200

    session_token = session.get("session_token")
    if session_token:
        sess = LoginSession.query.filter_by(session_token=session_token, is_active=True).first()
        if sess:
            sess.update_presence()
        else:
            # Recreate session if missing
            sess = LoginSession(
                user_id=current_user.id,
                session_token=session_token,
                login_time=datetime.utcnow(),
                last_active=datetime.utcnow(),
                is_active=True
            )
            db.session.add(sess)
            db.session.commit()
    else:
        # Fallback to user_id active session
        sess = LoginSession.query.filter_by(user_id=current_user.id, is_active=True).first()
        if sess:
            sess.update_presence()

    # Clean stale sessions
    LoginSession.clean_stale_sessions(timeout_minutes=10)

    return jsonify({"status": "active", "timestamp": datetime.utcnow().isoformat()}), 200


@api_bp.route("/active-customers", methods=["GET"])
@login_required
def active_customers():
    """
    Returns real-time list of active customers.
    Enforces strict customer privacy:
    - Normal customers see ONLY: Name and Current Segment
    - Admins see full technical metadata
    """
    LoginSession.clean_stale_sessions(timeout_minutes=10)

    active_sessions = LoginSession.query.join(User).filter(
        LoginSession.is_active == True,
        User.role == "customer"
    ).order_by(LoginSession.last_active.desc()).all()

    customers = []
    seen_ids = set()

    for sess in active_sessions:
        if sess.user_id in seen_ids:
            continue
        seen_ids.add(sess.user_id)

        seg = CustomerSegment.query.filter_by(user_id=sess.user_id).first()
        label = seg.segment_label if seg else "NEW CUSTOMER"
        badge = seg.badge_color if seg else "primary"

        # Customer privacy enforcement
        if current_user.is_admin:
            customers.append({
                "user_id": sess.user.id,
                "name": sess.user.name,
                "email": sess.user.email,
                "segment_label": label,
                "badge_color": badge,
                "last_active": sess.last_active.strftime("%H:%M:%S"),
                "is_current_user": sess.user_id == current_user.id
            })
        else:
            customers.append({
                "name": sess.user.name,
                "segment_label": label,
                "badge_color": badge,
                "is_current_user": sess.user_id == current_user.id
            })

    return jsonify({
        "active_count": len(customers),
        "customers": customers,
        "timestamp": datetime.utcnow().strftime("%H:%M:%S")
    }), 200


@api_bp.route("/my-segment", methods=["GET"])
@login_required
def my_segment_api():
    """Returns the logged-in customer's own segment details"""
    seg = recalculate_customer_segment(current_user.id)
    return jsonify(seg.to_dict()), 200
