import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user

from models import db
from models.user import User
from models.activity import CustomerActivity, LoginSession
from models.segment import CustomerSegment
from models.otp import OTPVerification
from ml.segmenter import recalculate_customer_segment

auth_bp = Blueprint("auth", __name__)


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """Attempts to send OTP via SMTP if configured; otherwise logs and returns False for dev fallback"""
    mail_server = current_app.config.get("MAIL_SERVER")
    mail_port = current_app.config.get("MAIL_PORT", 587)
    mail_user = current_app.config.get("MAIL_USERNAME")
    mail_pass = current_app.config.get("MAIL_PASSWORD")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@customersegment.local")
    use_tls = current_app.config.get("MAIL_USE_TLS", True)

    if not mail_user or not mail_pass:
        return False  # Development OTP mode

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = "Your Password Reset OTP - Customer Segmentation E-Commerce"
        body = f"""Hello,

You requested a password reset for your Customer Segmentation E-Commerce account.
Your 6-digit OTP code is:

    {otp_code}

This code will expire in 5 minutes. If you did not request this, please ignore this email.

Best regards,
Customer Segmentation Team
"""
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(mail_server, mail_port, timeout=5)
        if use_tls:
            server.starttls()
        server.login(mail_user, mail_pass)
        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        current_app.logger.warning(f"SMTP sending failed: {e}. Falling back to dev mode.")
        return False


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("shop.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("login.html")

        if not user.is_active_account:
            flash("This account is currently disabled.", "danger")
            return render_template("login.html")

        login_user(user, remember=remember)

        # Create or update active LoginSession
        session_token = str(uuid.uuid4())
        session["session_token"] = session_token
        
        # Deactivate any previous hanging sessions for this user
        LoginSession.query.filter_by(user_id=user.id, is_active=True).update({"is_active": False, "logout_time": datetime.utcnow()})
        
        login_sess = LoginSession(
            user_id=user.id,
            session_token=session_token,
            login_time=datetime.utcnow(),
            last_active=datetime.utcnow(),
            is_active=True,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:250] if request.user_agent else None
        )
        db.session.add(login_sess)
        db.session.commit()

        # Log LOGIN activity
        CustomerActivity.log("LOGIN", user=user, metadata={"ip": request.remote_addr})

        flash(f"Welcome back, {user.name}!", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        
        if user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("shop.index"))

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("shop.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not name or not email or not phone or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        new_user = User(name=name, email=email, phone=phone, role="customer")
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Initialize CustomerSegment
        recalculate_customer_segment(new_user.id)

        # Log registration / initial activity
        CustomerActivity.log("PROFILE_VIEW", user=new_user, metadata={"event": "Registered account"})

        flash("Registration successful! Please log in with your credentials.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    # Invalidate active LoginSession if authenticated
    if current_user.is_authenticated:
        # Log LOGOUT activity before closing session
        CustomerActivity.log("LOGOUT", user=current_user)

        session_token = session.get("session_token")
        if session_token:
            sess = LoginSession.query.filter_by(session_token=session_token).first()
            if sess:
                sess.end_session()

        # Mark all active sessions for this user as inactive
        LoginSession.query.filter_by(user_id=current_user.id, is_active=True).update({
            "is_active": False,
            "logout_time": datetime.utcnow()
        })
        db.session.commit()

    # Clear server session and invalidate Flask-Login user
    session.clear()
    logout_user()
    session["_remember"] = "clear"
    flash("You have been successfully logged out.", "info")

    response = redirect(url_for("auth.login"))

    # Explicitly clear remember me cookie from the response
    remember_cookie_name = current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    remember_cookie_domain = current_app.config.get("REMEMBER_COOKIE_DOMAIN")
    remember_cookie_path = current_app.config.get("REMEMBER_COOKIE_PATH", "/")

    response.delete_cookie(
        remember_cookie_name,
        domain=remember_cookie_domain,
        path=remember_cookie_path
    )
    if remember_cookie_domain:
        response.delete_cookie(remember_cookie_name, path=remember_cookie_path)

    # Security & Cache Control: Prevent stale authenticated pages from browser cache
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("shop.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter your registered email address.", "danger")
            return render_template("forgot_password.html")

        user = User.query.filter_by(email=email).first()
        if not user:
            # Prevent email enumeration while giving helpful feedback
            flash("If an account with that email exists, an OTP has been dispatched.", "info")
            return redirect(url_for("auth.reset_password", email=email))

        otp_record = OTPVerification.generate_otp(email, expiry_minutes=5)
        sent = send_otp_email(email, otp_record.otp_code)

        if not sent:
            if current_app.config.get("DEBUG", False):
                # Development OTP Mode
                current_app.logger.info(f"\n========================================\n[DEV OTP MODE] Password Reset OTP for {email}: {otp_record.otp_code}\nExpires in 5 minutes.\n========================================\n")
                flash(f"[DEVELOPMENT MODE] Your OTP code is: {otp_record.otp_code} (Valid for 5 minutes)", "warning")
            else:
                current_app.logger.warning(f"SMTP delivery failed or unconfigured for password reset: {email}")
                flash("If this email is registered, instructions have been sent. Please check your inbox or contact the administrator.", "info")
        else:
            flash(f"A 6-digit OTP has been sent to {email}. It expires in 5 minutes.", "success")

        return redirect(url_for("auth.reset_password", email=email))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("shop.index"))

    email = request.args.get("email", "").strip().lower() or request.form.get("email", "").strip().lower()

    if request.method == "POST":
        otp_code = request.form.get("otp_code", "").strip()
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not otp_code or not new_password:
            flash("All fields are required.", "danger")
            return render_template("reset_password.html", email=email)

        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("reset_password.html", email=email)

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", email=email)

        # Retrieve the latest active OTP for this email
        otp_record = OTPVerification.query.filter_by(email=email, is_used=False).order_by(OTPVerification.created_at.desc()).first()
        if not otp_record:
            flash("No active OTP found. Please request a new OTP.", "danger")
            return redirect(url_for("auth.forgot_password"))

        max_attempts = current_app.config.get("OTP_MAX_ATTEMPTS", 5)
        valid, msg = otp_record.verify(otp_code, max_attempts=max_attempts)
        if not valid:
            flash(msg, "danger")
            return render_template("reset_password.html", email=email)

        # Update password
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            flash("Password reset successfully! You can now log in.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("User not found.", "danger")
            return redirect(url_for("auth.login"))

    return render_template("reset_password.html", email=email)
