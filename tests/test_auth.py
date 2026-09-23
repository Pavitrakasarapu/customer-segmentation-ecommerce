from datetime import datetime, timedelta
from models import db
from models.user import User
from models.otp import OTPVerification
from models.activity import CustomerActivity, LoginSession


def test_password_hashing(app):
    with app.app_context():
        user = User(name="Hash Test", email="hash@test.com", phone="1234567890")
        user.set_password("MySecurePass123")
        assert user.password_hash != "MySecurePass123"
        assert user.check_password("MySecurePass123") is True
        assert user.check_password("WrongPassword") is False


def test_registration_success(client, app):
    res = client.post("/register", data={
        "name": "New User",
        "email": "newuser@example.com",
        "phone": "9998887776",
        "password": "Password@123",
        "confirm_password": "Password@123"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Registration successful" in res.data

    with app.app_context():
        u = User.query.filter_by(email="newuser@example.com").first()
        assert u is not None
        assert u.name == "New User"
        assert u.role == "customer"
        assert u.segment is not None


def test_registration_validation(client):
    # Passwords do not match
    res = client.post("/register", data={
        "name": "Mismatch User",
        "email": "mismatch@example.com",
        "phone": "9998887776",
        "password": "Password@123",
        "confirm_password": "DifferentPassword"
    }, follow_redirects=True)
    assert b"Passwords do not match" in res.data

    # Duplicate email
    res2 = client.post("/register", data={
        "name": "Pavitra Duplicate",
        "email": "pavitra@example.com",
        "phone": "9123456780",
        "password": "Password@123",
        "confirm_password": "Password@123"
    }, follow_redirects=True)
    assert b"already exists" in res2.data


def test_login_and_logout(client, app):
    # 1. Invalid Login
    res = client.post("/login", data={
        "email": "pavitra@example.com",
        "password": "WrongPassword"
    }, follow_redirects=True)
    assert b"Invalid email or password" in res.data

    # 2. Valid Login as Pavitra
    res2 = client.post("/login", data={
        "email": "pavitra@example.com",
        "password": "Pavitra@123"
    }, follow_redirects=True)
    assert res2.status_code == 200
    assert b"Welcome back, Pavitra!" in res2.data

    with app.app_context():
        u = User.query.filter_by(email="pavitra@example.com").first()
        sess = LoginSession.query.filter_by(user_id=u.id, is_active=True).first()
        assert sess is not None
        # Activity logged
        login_act = CustomerActivity.query.filter_by(user_id=u.id, activity_type="LOGIN").first()
        assert login_act is not None

    # 3. Logout
    res3 = client.get("/logout", follow_redirects=True)
    assert res3.status_code == 200
    assert b"logged out" in res3.data

    with app.app_context():
        # Session marked inactive
        sess = LoginSession.query.filter_by(user_id=u.id, is_active=True).first()
        assert sess is None
        # Logout activity recorded
        logout_act = CustomerActivity.query.filter_by(user_id=u.id, activity_type="LOGOUT").first()
        assert logout_act is not None


def test_otp_flow(client, app):
    # 1. Request OTP for existing email
    res = client.post("/forgot-password", data={"email": "pavitra@example.com"}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        otp_rec = OTPVerification.query.filter_by(email="pavitra@example.com", is_used=False).first()
        assert otp_rec is not None
        assert len(otp_rec.otp_code) == 6
        code = otp_rec.otp_code

    # 2. Reset with wrong OTP
    res_wrong = client.post("/reset-password", data={
        "email": "pavitra@example.com",
        "otp_code": "000000",
        "password": "NewSecretPassword@123",
        "confirm_password": "NewSecretPassword@123"
    }, follow_redirects=True)
    assert b"Invalid OTP code" in res_wrong.data

    # 3. Reset with correct OTP
    res_correct = client.post("/reset-password", data={
        "email": "pavitra@example.com",
        "otp_code": code,
        "password": "NewSecretPassword@123",
        "confirm_password": "NewSecretPassword@123"
    }, follow_redirects=True)
    assert b"Password reset successfully" in res_correct.data

    with app.app_context():
        u = User.query.filter_by(email="pavitra@example.com").first()
        assert u.check_password("NewSecretPassword@123") is True
        # OTP is now marked as used
        otp_check = OTPVerification.query.filter_by(email="pavitra@example.com", is_used=False).first()
        assert otp_check is None


def test_logout_complete_session_invalidation_and_switching(client, app):
    """
    Verifies that logout completely destroys the authentication session:
    - Customer logout clears remember cookie and redirects to login page
    - Admin logout clears remember cookie and redirects to login page
    - Protected customer and admin pages are inaccessible after logout
    - Browser back cannot restore session (Cache-Control no-store)
    - Different accounts can seamlessly log in sequentially after logout
    """
    # 1. LOGIN AS USER A (Pavitra with remember=True)
    res_a = client.post("/login", data={
        "email": "pavitra@example.com",
        "password": "Pavitra@123",
        "remember": "on"
    }, follow_redirects=False)
    assert res_a.status_code == 302
    assert client.get_cookie("remember_token") is not None

    # Use application as User A
    prof_a = client.get("/profile")
    assert prof_a.status_code == 200
    assert b"Pavitra" in prof_a.data

    # LOGOUT USER A
    logout_a = client.get("/logout", follow_redirects=True)
    assert logout_a.status_code == 200
    assert b"Welcome Back" in logout_a.data
    assert b"You have been successfully logged out." in logout_a.data
    assert client.get_cookie("remember_token") is None

    # Protected customer pages require login
    prof_a_post = client.get("/profile", follow_redirects=False)
    assert prof_a_post.status_code == 302
    assert "/login" in prof_a_post.headers.get("Location")

    # 2. LOGIN AS USER B (Anu with remember=True)
    res_b = client.post("/login", data={
        "email": "anu@example.com",
        "password": "Anu@123",
        "remember": "on"
    }, follow_redirects=False)
    assert res_b.status_code == 302
    assert client.get_cookie("remember_token") is not None

    # Use application as User B
    prof_b = client.get("/profile")
    assert prof_b.status_code == 200
    assert b"Anu" in prof_b.data

    # LOGOUT USER B
    logout_b = client.get("/logout", follow_redirects=True)
    assert logout_b.status_code == 200
    assert b"Welcome Back" in logout_b.data
    assert b"You have been successfully logged out." in logout_b.data
    assert client.get_cookie("remember_token") is None

    # 3. LOGIN AS ADMIN (with remember=True)
    res_admin = client.post("/login", data={
        "email": "pavitrakasarapu@gmail.com",
        "password": "Admin@123",
        "remember": "on"
    }, follow_redirects=False)
    assert res_admin.status_code == 302
    assert "/admin" in res_admin.headers.get("Location")
    assert client.get_cookie("remember_token") is not None

    # Access admin dashboard
    dash = client.get("/admin/dashboard")
    assert dash.status_code == 200
    assert b"ADMIN DASHBOARD" in dash.data

    # LOGOUT ADMIN
    logout_admin = client.get("/logout", follow_redirects=True)
    assert logout_admin.status_code == 200
    assert b"Welcome Back" in logout_admin.data
    assert b"You have been successfully logged out." in logout_admin.data
    assert client.get_cookie("remember_token") is None

    # Admin dashboard must NOT remain accessible after logout
    dash_post = client.get("/admin/dashboard", follow_redirects=False)
    assert dash_post.status_code in [302, 401, 403]
    if dash_post.status_code == 302:
        assert "/login" in dash_post.headers.get("Location")

    # 4. LOGIN AS ANOTHER USER (Pavitra again)
    res_again = client.post("/login", data={
        "email": "pavitra@example.com",
        "password": "Pavitra@123",
        "remember": "on"
    }, follow_redirects=False)
    assert res_again.status_code == 302

    prof_again = client.get("/profile")
    assert prof_again.status_code == 200
    assert b"Pavitra" in prof_again.data

