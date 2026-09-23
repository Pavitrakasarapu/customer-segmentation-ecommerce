"""
Automated Test Suite for Real User Dynamic Analytics & Segmentation
Verifies:
1. Zero fake/seeded customer data in real analytics
2. Dynamic feature extraction and segment calculation for newly registered users
3. Dynamic behavioral updates (views, searches, cart, wishlist, orders)
4. Multi-user real customer presence with strict privacy
5. Dynamic Admin Dashboard analytics (real revenue, orders, segment counts)
6. Admin and customer logout security (session invalidation, cache control headers)
"""
import pytest
from app import create_app
from models import db
from models.user import User
from models.product import Category, Product
from models.order import Order, OrderItem
from models.cart import CartItem, WishlistItem
from models.activity import CustomerActivity, LoginSession
from models.segment import CustomerSegment
from ml.segmenter import recalculate_customer_segment


def test_clean_start_zero_fabricated_analytics(client, app):
    """Admin dashboard must honestly show 0 customers, 0 orders, ₹0 revenue when no customers exist"""
    # Log in as admin
    client.post("/login", data={"email": "pavitrakasarapu@gmail.com", "password": "Admin@123"}, follow_redirects=True)

    with app.app_context():
        # Clear any customer accounts for clean start test
        OrderItem.query.delete()
        Order.query.delete()
        CustomerActivity.query.delete()
        CustomerSegment.query.delete()
        User.query.filter_by(role="customer").delete()
        db.session.commit()

    res = client.get("/admin/dashboard")
    assert res.status_code == 200
    # Dynamic real stats: 0 customers, 0 orders, ₹0.00 revenue
    assert b">0</h3>" in res.data  # Total customers or total orders
    assert b"\xe2\x82\xb90.00" in res.data  # ₹0.00 revenue
    assert b"No customers currently active" in res.data


def test_new_user_registration_and_real_segment(client, app):
    """Newly registered customer starts with real 0 orders, ₹0 spend, and 'NEW CUSTOMER' segment"""
    # 1. Register a real customer
    reg_res = client.post("/register", data={
        "name": "Rohan Sharma",
        "email": "rohan@example.com",
        "phone": "9876543210",
        "password": "Password@123",
        "confirm_password": "Password@123"
    }, follow_redirects=True)
    assert reg_res.status_code == 200

    # 2. Login as Rohan
    login_res = client.post("/login", data={
        "email": "rohan@example.com",
        "password": "Password@123"
    }, follow_redirects=True)
    assert login_res.status_code == 200

    # 3. Check customer profile
    prof_res = client.get("/profile")
    assert prof_res.status_code == 200
    assert b"NEW CUSTOMER" in prof_res.data
    assert b"\xe2\x82\xb90.00" in prof_res.data  # ₹0.00 spend

    # 4. Check customer segmentation page
    seg_res = client.get("/segmentation/my-segment")
    assert seg_res.status_code == 200
    assert b"NEW CUSTOMER" in seg_res.data
    assert b"\xe2\x82\xb90.00" in seg_res.data
    assert b"No Purchases Yet" in seg_res.data


def test_behavioral_actions_update_analytics_dynamically(client, app):
    """Product views, searches, wishlist, cart, and orders dynamically update real customer stats"""
    # Register and Login as Rohan
    client.post("/register", data={
        "name": "Rohan Sharma",
        "email": "rohan@example.com",
        "phone": "9876543210",
        "password": "Password@123",
        "confirm_password": "Password@123"
    }, follow_redirects=True)
    client.post("/login", data={"email": "rohan@example.com", "password": "Password@123"}, follow_redirects=True)

    with app.app_context():
        p = Product.query.first()
        pid = p.id
        price = p.price

    # 1. View Product
    client.get(f"/product/{pid}")

    # 2. Search Product
    client.get("/shop?q=Dress")

    # 3. Add to Wishlist
    client.post(f"/wishlist/toggle/{pid}", follow_redirects=True)

    # 4. Add to Cart
    client.post(f"/cart/add/{pid}", data={"quantity": 2}, follow_redirects=True)

    # 5. Place Order (COD)
    order_res = client.post("/checkout", data={
        "address": "42 Tech Park",
        "city": "Bangalore",
        "pincode": "560001",
        "payment_method": "Cash on Delivery"
    }, follow_redirects=True)
    assert order_res.status_code == 200

    # 6. Verify customer profile reflects the actual order
    prof_res = client.get("/profile")
    assert prof_res.status_code == 200
    expected_spend = price * 2
    assert f"{expected_spend:.2f}".encode() in prof_res.data

    # 7. Verify Admin Dashboard reflects this real customer's exact spending and order
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"email": "pavitrakasarapu@gmail.com", "password": "Admin@123"}, follow_redirects=True)
    admin_dash = client.get("/admin/dashboard")
    assert admin_dash.status_code == 200
    assert b"Rohan Sharma" in admin_dash.data
    assert b"ORDER_PLACED" in admin_dash.data


def test_multi_user_real_presence_and_privacy(client, app):
    """Verify multiple real users show only name & segment to peers, no private data leaked"""
    # User 1: Rohan
    client.post("/register", data={
        "name": "Rohan Sharma",
        "email": "rohan@example.com",
        "phone": "9876543210",
        "password": "Password@123",
        "confirm_password": "Password@123"
    }, follow_redirects=True)
    client.post("/login", data={"email": "rohan@example.com", "password": "Password@123"}, follow_redirects=True)

    # User 2: Priya (simulating concurrent active user)
    with app.app_context():
        priya = User(name="Priya Patel", email="priya@example.com", phone="9812345678", role="customer")
        priya.set_password("Password@123")
        db.session.add(priya)
        db.session.flush()
        sess_priya = LoginSession(user_id=priya.id, session_token="priya-test-token-active", is_active=True)
        seg_priya = CustomerSegment(user_id=priya.id, segment_label="NEW CUSTOMER")
        db.session.add_all([sess_priya, seg_priya])
        db.session.commit()

    # Rohan checks active customers API
    api_res = client.get("/api/active-customers")
    assert api_res.status_code == 200
    data = api_res.get_json()
    assert data["active_count"] >= 2
    names = [c["name"] for c in data["customers"]]
    assert "Rohan Sharma" in names
    assert "Priya Patel" in names

    # Verify privacy: No private details leaked to customer
    for c in data["customers"]:
        assert "email" not in c
        assert "phone" not in c
        assert "spending" not in c
        assert "orders" not in c


def test_admin_and_customer_logout_security(client, app):
    """Logout must clear session, invalidate access, set cache control headers, and block back button"""
    # 1. Admin login
    login_res = client.post("/login", data={"email": "pavitrakasarapu@gmail.com", "password": "Admin@123"}, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"ADMIN DASHBOARD" in login_res.data

    # Admin access dashboard
    dash_res = client.get("/admin/dashboard")
    assert dash_res.status_code == 200
    # Verify Cache-Control header is present to prevent browser back navigation
    assert "no-store" in dash_res.headers.get("Cache-Control", "")

    # 2. Admin Logout
    logout_res = client.get("/logout", follow_redirects=False)
    assert logout_res.status_code == 302
    assert "/login" in logout_res.headers.get("Location", "")
    assert "no-store" in logout_res.headers.get("Cache-Control", "")

    # 3. Direct access to /admin/dashboard after logout must be rejected (redirected to login or 403)
    post_logout_res = client.get("/admin/dashboard")
    assert post_logout_res.status_code in [302, 401, 403]
    if post_logout_res.status_code == 302:
        assert "/login" in post_logout_res.headers.get("Location", "")
