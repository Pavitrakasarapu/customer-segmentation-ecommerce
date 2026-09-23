from models import db
from models.user import User


def test_customer_unauthorized_admin_access(client):
    # Log in as normal customer Pavitra
    login_res = client.post("/login", data={"email": "pavitra@example.com", "password": "Pavitra@123"}, follow_redirects=True)
    assert login_res.status_code == 200
    # Customer should NOT see Admin Dashboard link in navbar
    assert b"ADMIN DASHBOARD" not in login_res.data

    # Customer attempts to access admin routes directly -> 403 Forbidden
    res1 = client.get("/admin/dashboard")
    assert res1.status_code == 403

    res2 = client.get("/admin/customers")
    assert res2.status_code == 403

    res3 = client.get("/admin/activities")
    assert res3.status_code == 403


def test_admin_dashboard_and_customers(client, app):
    # Log in as authorized Admin pavitrakasarapu@gmail.com
    login_res = client.post("/login", data={"email": "pavitrakasarapu@gmail.com", "password": "Admin@123"}, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"ADMIN DASHBOARD" in login_res.data

    # 1. Dashboard
    res_dash = client.get("/admin/dashboard")
    assert res_dash.status_code == 200
    assert b"Executive Analytics &amp; Segmentation Dashboard" in res_dash.data or b"Executive Analytics & Segmentation Dashboard" in res_dash.data
    assert b"Segment Distribution" in res_dash.data

    # 2. Customers Table
    res_custs = client.get("/admin/customers")
    assert res_custs.status_code == 200
    assert b"Pavitra" in res_custs.data
    assert b"Anu" in res_custs.data

    # 3. Customer Detail (360 View)
    with app.app_context():
        pavitra = User.query.filter_by(email="pavitra@example.com").first()
        pid = pavitra.id

    res_detail = client.get(f"/admin/customers/{pid}")
    assert res_detail.status_code == 200
    assert b"CUSTOMER 360 INTELLIGENCE" in res_detail.data
    assert b"Pavitra" in res_detail.data
    assert b"pavitra@example.com" in res_detail.data

    # Verify currency representation is ₹
    assert "₹".encode('utf-8') in res_dash.data
    assert "₹".encode('utf-8') in res_detail.data

    # 4. Activity Logs
    res_logs = client.get("/admin/activities")
    assert res_logs.status_code == 200
    assert b"Customer Activity Audit Logs" in res_logs.data


def test_other_user_with_admin_role_blocked(client, app):
    # If someone manually sets role="admin" with a different email, they must STILL be denied!
    with app.app_context():
        impostor = User(name="Impostor", email="hacker@example.com", phone="1234567890", role="admin")
        impostor.set_password("Hack@123")
        db.session.add(impostor)
        db.session.commit()

    # Log in as the unauthorized user
    login_res = client.post("/login", data={"email": "hacker@example.com", "password": "Hack@123"}, follow_redirects=True)
    # Admin dashboard link must NOT be shown
    assert b"ADMIN DASHBOARD" not in login_res.data

    # Direct URL access to admin must be 403 Forbidden
    res = client.get("/admin/dashboard")
    assert res.status_code == 403
