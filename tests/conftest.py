import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from app import create_app
from models import db
from models.user import User
from models.product import Category, Product
from models.segment import CustomerSegment
from models.activity import LoginSession


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        # Seed minimal test categories and products
        cat_women = Category(name="WOMEN", slug="women", icon="bi-gender-female")
        cat_men = Category(name="MEN", slug="men", icon="bi-gender-male")
        db.session.add_all([cat_women, cat_men])
        db.session.flush()

        prod1 = Product(
            category_id=cat_women.id,
            subcategory="Dresses",
            name="Test Summer Dress",
            price=50.0,
            stock=20,
            description="A lovely test summer dress."
        )
        prod2 = Product(
            category_id=cat_men.id,
            subcategory="Shirts",
            name="Test Cotton Shirt",
            price=40.0,
            stock=30,
            description="A crisp test cotton shirt."
        )
        db.session.add_all([prod1, prod2])

        # Seed Test Users: Pavitra, Anu, and Admin
        pavitra = User(name="Pavitra", email="pavitra@example.com", phone="9123456780", role="customer")
        pavitra.set_password("Pavitra@123")

        anu = User(name="Anu", email="anu@example.com", phone="9123456781", role="customer")
        anu.set_password("Anu@123")

        admin = User(name="Administrator", email="pavitrakasarapu@gmail.com", phone="9876543210", role="admin")
        admin.set_password("Admin@123")

        db.session.add_all([pavitra, anu, admin])
        db.session.commit()

        from models.order import Order, OrderItem

        # Seed orders for Pavitra (High Value: 5 orders, $1600)
        for i in range(5):
            ord_p = Order(
                user_id=pavitra.id,
                order_number=f"TEST-ORD-P-{i+1}",
                total_amount=320.0,
                status="Delivered",
                payment_method="Cash on Delivery",
                shipping_address="Pavitra Test Street",
                shipping_city="Bangalore",
                shipping_pincode="560001"
            )
            db.session.add(ord_p)
            db.session.flush()
            item = OrderItem(order_id=ord_p.id, product_id=prod1.id, quantity=4, price=50.0, subtotal=200.0)
            db.session.add(item)

        # Seed orders for Anu (Regular: 2 orders, $500)
        for j in range(2):
            ord_a = Order(
                user_id=anu.id,
                order_number=f"TEST-ORD-A-{j+1}",
                total_amount=250.0,
                status="Delivered",
                payment_method="Cash on Delivery",
                shipping_address="Anu Test Street",
                shipping_city="Bangalore",
                shipping_pincode="560001"
            )
            db.session.add(ord_a)
            db.session.flush()
            item_a = OrderItem(order_id=ord_a.id, product_id=prod2.id, quantity=5, price=40.0, subtotal=200.0)
            db.session.add(item_a)

        db.session.commit()

        # Seed segments
        seg_p = CustomerSegment(user_id=pavitra.id, segment_label="HIGH VALUE CUSTOMER", monetary=1600.0, frequency=5)
        seg_a = CustomerSegment(user_id=anu.id, segment_label="REGULAR CUSTOMER", monetary=500.0, frequency=2)
        db.session.add_all([seg_p, seg_a])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
