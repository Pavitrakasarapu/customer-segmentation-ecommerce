import json
from models import db
from models.user import User
from models.activity import LoginSession
from models.segment import CustomerSegment
from ml.segmenter import recalculate_customer_segment


def test_multi_user_active_and_privacy(client, app):
    # 1. Login Pavitra
    client.post("/login", data={"email": "pavitra@example.com", "password": "Pavitra@123"})
    
    # Check active customers API as Pavitra
    res1 = client.get("/api/active-customers")
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["active_count"] == 1
    assert data1["customers"][0]["name"] == "Pavitra"
    assert data1["customers"][0]["segment_label"] == "HIGH VALUE CUSTOMER"

    # CRUCIAL PRIVACY TEST:
    # Ensure no private fields are leaked to normal customers!
    cust_record = data1["customers"][0]
    assert "email" not in cust_record
    assert "phone" not in cust_record
    assert "spending" not in cust_record
    assert "orders" not in cust_record
    assert "recency" not in cust_record
    assert "raw_activities" not in cust_record

    # 2. Simulate Anu also being logged in simultaneously
    with app.app_context():
        anu = User.query.filter_by(email="anu@example.com").first()
        sess_anu = LoginSession(
            user_id=anu.id,
            session_token="anu-session-token-123",
            is_active=True
        )
        db.session.add(sess_anu)
        db.session.commit()

    # Pavitra polls /api/active-customers again
    res2 = client.get("/api/active-customers")
    data2 = res2.get_json()
    assert data2["active_count"] == 2
    names = [c["name"] for c in data2["customers"]]
    segments = [c["segment_label"] for c in data2["customers"]]
    assert "Pavitra" in names
    assert "Anu" in names
    assert "HIGH VALUE CUSTOMER" in segments
    assert "REGULAR CUSTOMER" in segments

    # Verify Anu's record also has strict privacy applied
    anu_rec = next(c for c in data2["customers"] if c["name"] == "Anu")
    assert "email" not in anu_rec
    assert "phone" not in anu_rec
    assert "spending" not in anu_rec

    # 3. Pavitra logs out
    client.get("/logout")

    # Re-check active list with new client session
    # Anu is still active, Pavitra has disappeared from active list!
    client_new = app.test_client()
    # Log in as Anu to check
    client_new.post("/login", data={"email": "anu@example.com", "password": "Anu@123"})
    res3 = client_new.get("/api/active-customers")
    data3 = res3.get_json()
    names_after_logout = [c["name"] for c in data3["customers"]]
    assert "Anu" in names_after_logout
    assert "Pavitra" not in names_after_logout


def test_customer_own_segmentation_page(client, app):
    client.post("/login", data={"email": "pavitra@example.com", "password": "Pavitra@123"})

    res = client.get("/segmentation/my-segment")
    assert res.status_code == 200
    assert b"PERSONAL BEHAVIORAL PROFILE" in res.data
    assert b"Total Orders (F)" in res.data
    assert b"Total Spend (M)" in res.data
    assert b"Why are you in this segment?" in res.data

    with app.app_context():
        u = User.query.filter_by(email="pavitra@example.com").first()
        assert u.segment.segment_label.encode() in res.data


def test_real_time_segment_recalculation(app):
    with app.app_context():
        u = User.query.filter_by(email="anu@example.com").first()
        seg_before = recalculate_customer_segment(u.id)
        assert seg_before is not None
        assert seg_before.segment_label in [
            "HIGH VALUE CUSTOMER", "REGULAR CUSTOMER", "NEW CUSTOMER", "AT-RISK CUSTOMER", "DISCOUNT SEEKER"
        ]
