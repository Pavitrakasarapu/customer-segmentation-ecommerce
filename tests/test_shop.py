from models import db
from models.user import User
from models.product import Product, Category
from models.cart import CartItem, WishlistItem
from models.order import Order
from models.activity import CustomerActivity


def login_as(client, email="pavitra@example.com", password="Pavitra@123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def test_product_browsing_and_search(client, app):
    login_as(client)

    # Browse catalog
    res = client.get("/shop")
    assert res.status_code == 200
    assert b"Test Summer Dress" in res.data
    assert b"Test Cotton Shirt" in res.data

    # Category filter
    res_cat = client.get("/shop?category=women")
    assert res_cat.status_code == 200
    assert b"Test Summer Dress" in res_cat.data

    # Search filter
    res_search = client.get("/shop?q=Cotton")
    assert res_search.status_code == 200
    assert b"Test Cotton Shirt" in res_search.data

    with app.app_context():
        # Check SEARCH activity recorded
        u = User.query.filter_by(email="pavitra@example.com").first()
        search_act = CustomerActivity.query.filter_by(user_id=u.id, activity_type="SEARCH").first()
        assert search_act is not None
        assert "Cotton" in search_act.metadata_json


def test_product_detail_and_view_activity(client, app):
    login_as(client)

    with app.app_context():
        p = Product.query.first()
        pid = p.id

    res = client.get(f"/product/{pid}")
    assert res.status_code == 200
    assert b"Behavioral Tracking Active" in res.data

    with app.app_context():
        u = User.query.filter_by(email="pavitra@example.com").first()
        view_act = CustomerActivity.query.filter_by(user_id=u.id, activity_type="PRODUCT_VIEW", product_id=pid).first()
        assert view_act is not None


def test_wishlist_operations(client, app):
    login_as(client)

    with app.app_context():
        p = Product.query.first()
        pid = p.id
        u = User.query.filter_by(email="pavitra@example.com").first()
        uid = u.id

    # Add to wishlist
    res_add = client.post(f"/wishlist/toggle/{pid}", follow_redirects=True)
    assert res_add.status_code == 200

    with app.app_context():
        w = WishlistItem.query.filter_by(user_id=uid, product_id=pid).first()
        assert w is not None
        act = CustomerActivity.query.filter_by(user_id=uid, activity_type="WISHLIST_ADD").first()
        assert act is not None

    # Remove from wishlist (toggle again)
    res_rem = client.post(f"/wishlist/toggle/{pid}", follow_redirects=True)
    assert res_rem.status_code == 200

    with app.app_context():
        w2 = WishlistItem.query.filter_by(user_id=uid, product_id=pid).first()
        assert w2 is None
        act2 = CustomerActivity.query.filter_by(user_id=uid, activity_type="WISHLIST_REMOVE").first()
        assert act2 is not None


def test_cart_and_checkout_flow(client, app):
    login_as(client)

    with app.app_context():
        p = Product.query.first()
        pid = p.id
        initial_stock = p.stock
        u = User.query.filter_by(email="pavitra@example.com").first()
        uid = u.id

    # 1. Add to Cart
    res_cart = client.post(f"/cart/add/{pid}", data={"quantity": 2}, follow_redirects=True)
    assert res_cart.status_code == 200

    with app.app_context():
        ci = CartItem.query.filter_by(user_id=uid, product_id=pid).first()
        assert ci is not None
        assert ci.quantity == 2
        cart_act = CustomerActivity.query.filter_by(user_id=uid, activity_type="CART_ADD").first()
        assert cart_act is not None

    # 2. View Cart
    res_view = client.get("/cart")
    assert res_view.status_code == 200
    assert b"Estimated Total" in res_view.data

    # 3. Checkout GET
    res_chk = client.get("/checkout")
    assert res_chk.status_code == 200
    assert b"Cash on Delivery" in res_chk.data

    # 4. Place Order POST
    res_order = client.post("/checkout", data={
        "address": "123 Test Street",
        "city": "Bangalore",
        "pincode": "560001",
        "payment_method": "Cash on Delivery"
    }, follow_redirects=True)
    assert res_order.status_code == 200
    assert b"Thank You! Order Confirmed" in res_order.data

    with app.app_context():
        # Cart cleared
        remaining_cart = CartItem.query.filter_by(user_id=uid).all()
        assert len(remaining_cart) == 0

        # Order created in DB
        order = Order.query.filter_by(user_id=uid).order_by(Order.created_at.desc()).first()
        assert order is not None
        assert order.total_amount == 100.0  # 2 x 50.0
        assert len(order.items) == 1

        # Stock decremented
        prod_updated = db.session.get(Product, pid)
        assert prod_updated.stock == initial_stock - 2

        # Activities recorded
        order_act = CustomerActivity.query.filter_by(user_id=uid, activity_type="ORDER_PLACED").first()
        assert order_act is not None


def test_currency_and_removed_ai_card(client):
    login_as(client)
    res = client.get("/shop")
    assert res.status_code == 200

    # TEST A: Product price displays as ₹ instead of $
    assert "₹".encode('utf-8') in res.data
    assert b"$50.00" not in res.data
    assert b"$40.00" not in res.data

    # TEST B: "Active AI Engine / K-Means 5-Cluster Machine Learning" card is NOT visible
    assert b"Active AI Engine" not in res.data
    assert b"K-Means 5-Cluster Machine Learning" not in res.data
