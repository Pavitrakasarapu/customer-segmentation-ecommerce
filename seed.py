"""
Database Seeder for Customer Segmentation E-Commerce.
Seeds ONLY real foundational catalog data and administrator account:
- 4 Product Categories (WOMEN, MEN, CHILDREN, BEAUTY)
- 24 Catalog Products across subcategories
- Administrator Account (pavitrakasarapu@gmail.com)

Customer profiles, activities, orders, carts, wishlists, and segmentation
are generated DYNAMICALLY as REAL users register, browse, and shop.
No fake or synthetic customer analytics are seeded.
"""
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from models import db
from models.user import User
from models.product import Category, Product
from models.order import Order, OrderItem
from models.cart import CartItem, WishlistItem
from models.activity import CustomerActivity, LoginSession
from models.segment import CustomerSegment
from models.otp import OTPVerification
from ml.segmenter import recalculate_all_segments


DEMO_PRODUCTS = [
    # WOMEN
    {"category": "WOMEN", "subcategory": "Dresses", "name": "Floral Summer Midi Dress", "price": 49.99, "stock": 45,
     "description": "Breezy floral midi dress with tie waist and ruffled hem, perfect for casual outings.",
     "image_url": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=500&auto=format&fit=crop&q=60"},
    {"category": "WOMEN", "subcategory": "Tops", "name": "Classic Linen White Blouse", "price": 34.50, "stock": 60,
     "description": "Breathable 100% pure organic linen blouse with relaxed fit and button-down collar.",
     "image_url": "https://images.unsplash.com/photo-1534126511673-b6899657816a?w=500&auto=format&fit=crop&q=60"},
    {"category": "WOMEN", "subcategory": "Kurtis", "name": "Embroidered Anarkali Kurti", "price": 55.00, "stock": 35,
     "description": "Elegant cotton silk Anarkali kurti featuring handcrafted zari embroidery on yoke.",
     "image_url": "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=500&auto=format&fit=crop&q=60"},
    {"category": "WOMEN", "subcategory": "Jeans", "name": "High-Rise Skinny Denim", "price": 64.99, "stock": 50,
     "description": "Premium stretch denim with sculpting high waist and comfortable ankle cut.",
     "image_url": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=60"},
    {"category": "WOMEN", "subcategory": "Sarees", "name": "Banarasi Silk Saree", "price": 119.00, "stock": 25,
     "description": "Traditional Banarasi silk saree woven with intricate golden floral motifs and rich pallu.",
     "image_url": "https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=500&auto=format&fit=crop&q=60"},
    {"category": "WOMEN", "subcategory": "Ethnic Wear", "name": "Festive Velvet Lehenga Set", "price": 149.99, "stock": 20,
     "description": "Designer three-piece lehenga choli set with sequin embellishments and matching dupatta.",
     "image_url": "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=500&auto=format&fit=crop&q=60"},

    # MEN
    {"category": "MEN", "subcategory": "Shirts", "name": "Oxford Cotton Formal Shirt", "price": 42.00, "stock": 80,
     "description": "Crisp light-blue Oxford cotton tailored shirt suited for office and formal wear.",
     "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop&q=60"},
    {"category": "MEN", "subcategory": "T-Shirts", "name": "Premium Crewneck Cotton Tee", "price": 24.99, "stock": 100,
     "description": "Ultra-soft combed ringspun cotton t-shirt with durable ribbed collar.",
     "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop&q=60"},
    {"category": "MEN", "subcategory": "Jeans", "name": "Slim Fit Tapered Blue Jeans", "price": 59.50, "stock": 55,
     "description": "Vintage washed authentic denim featuring comfortable slight flex technology.",
     "image_url": "https://images.unsplash.com/photo-1542272604-780c96856592?w=500&auto=format&fit=crop&q=60"},
    {"category": "MEN", "subcategory": "Trousers", "name": "Stretch Chino Trousers", "price": 48.00, "stock": 40,
     "description": "Versatile flat-front khaki chinos designed for everyday casual smart comfort.",
     "image_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=500&auto=format&fit=crop&q=60"},
    {"category": "MEN", "subcategory": "Jackets", "name": "Urban Rugged Denim Jacket", "price": 89.99, "stock": 30,
     "description": "Timeless trucker jacket crafted with heavy-duty stonewashed denim and metal buttons.",
     "image_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500&auto=format&fit=crop&q=60"},

    # CHILDREN
    {"category": "CHILDREN", "subcategory": "Girls Dresses", "name": "Princess Tulle Party Frock", "price": 36.00, "stock": 40,
     "description": "Glittering layered tulle frock with satin bow belt, ideal for birthdays and parties.",
     "image_url": "https://images.unsplash.com/photo-1518831959646-742c3a14ebf7?w=500&auto=format&fit=crop&q=60"},
    {"category": "CHILDREN", "subcategory": "Boys Dresses", "name": "Boys 3-Piece Waistcoat Suit", "price": 45.00, "stock": 30,
     "description": "Formal tuxedo set featuring vest, shirt, trousers, and clip-on bow tie.",
     "image_url": "https://images.unsplash.com/photo-1503944583220-79d8926ad5e2?w=500&auto=format&fit=crop&q=60"},
    {"category": "CHILDREN", "subcategory": "Kids Shirts", "name": "Boys Plaid Check Cotton Shirt", "price": 22.50, "stock": 50,
     "description": "Soft brushed flannel shirt in cheerful red-blue check pattern with chest pocket.",
     "image_url": "https://images.unsplash.com/photo-1519238263530-99bdd11df2ea?w=500&auto=format&fit=crop&q=60"},
    {"category": "CHILDREN", "subcategory": "Kids Jeans", "name": "Comfy Elastic Waist Kids Jeans", "price": 28.00, "stock": 60,
     "description": "Flexible and durable denim pants with rib-knit stretchy waistband for active play.",
     "image_url": "https://images.unsplash.com/photo-1519457431-44ccd64a579b?w=500&auto=format&fit=crop&q=60"},
    {"category": "CHILDREN", "subcategory": "Footwear", "name": "LED Light-Up Sneaker Shoes", "price": 32.00, "stock": 45,
     "description": "Fun, glowing athletic sneakers with hook-and-loop straps and non-slip rubber soles.",
     "image_url": "https://images.unsplash.com/photo-1514989940723-e8e51635b782?w=500&auto=format&fit=crop&q=60"},
    {"category": "CHILDREN", "subcategory": "Toys", "name": "Eco Wooden Building Blocks Set", "price": 26.00, "stock": 70,
     "description": "50-piece non-toxic rainbow wooden blocks promoting creativity and motor skills.",
     "image_url": "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=500&auto=format&fit=crop&q=60"},

    # BEAUTY
    {"category": "BEAUTY", "subcategory": "Creams", "name": "Hydrating Day Radiance Cream", "price": 29.99, "stock": 75,
     "description": "Infused with hyaluronic acid and niacinamide for 24-hour deep moisture and glow.",
     "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60"},
    {"category": "BEAUTY", "subcategory": "Face Wash", "name": "Gentle Green Tea Foaming Cleanser", "price": 18.50, "stock": 85,
     "description": "Sulfate-free soothing facial cleanser that balances sebum without drying skin.",
     "image_url": "https://images.unsplash.com/photo-1556228722-d0b5de70b79b?w=500&auto=format&fit=crop&q=60"},
    {"category": "BEAUTY", "subcategory": "Moisturizer", "name": "Ceramide Deep Repair Moisturizer", "price": 32.00, "stock": 60,
     "description": "Restores damaged skin barrier with 5 essential ceramides and soothing centella.",
     "image_url": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=500&auto=format&fit=crop&q=60"},
    {"category": "BEAUTY", "subcategory": "Sunscreen", "name": "Invisible Shield Matte SPF 50+", "price": 25.00, "stock": 90,
     "description": "Ultra-lightweight, broad-spectrum UV protection with zero white cast or greasy finish.",
     "image_url": "https://images.unsplash.com/photo-1567928815104-b7980ee070b6?w=500&auto=format&fit=crop&q=60"},
    {"category": "BEAUTY", "subcategory": "Serum", "name": "Vitamin C 15% Brightening Serum", "price": 38.00, "stock": 50,
     "description": "Potent antioxidant serum targeting hyperpigmentation, fine lines, and dull texture.",
     "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500&auto=format&fit=crop&q=60"},
    {"category": "BEAUTY", "subcategory": "Body Lotion", "name": "Shea Butter Nourishing Body Milk", "price": 21.00, "stock": 65,
     "description": "Velvety body lotion with unrefined African shea butter and sweet almond oil.",
     "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500&auto=format&fit=crop&q=60"},
    {"category": "BEAUTY", "subcategory": "Lip Care", "name": "Berry Tinted Peptide Lip Balm", "price": 14.00, "stock": 100,
     "description": "Glossy nourishing lip balm packed with peptides for plump, soft, hydrated lips.",
     "image_url": "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=500&auto=format&fit=crop&q=60"},
    {"category": "BEAUTY", "subcategory": "Skincare", "name": "Rosewater Balancing Toner Mist", "price": 19.50, "stock": 70,
     "description": "Pure organic Moroccan rosewater mist to hydrate, tone, and refresh complexion anytime.",
     "image_url": "https://images.unsplash.com/photo-1608248597359-bb47cf2b694b?w=500&auto=format&fit=crop&q=60"},
]


def clean_synthetic_data():
    """Removes any old synthetic demo customers, fake orders, and fake activities"""
    # Delete synthetic customer accounts (emails starting with demo_ or old test names)
    synthetic_users = User.query.filter(User.role == "customer", User.email.ilike("demo_%")).all()
    for u in synthetic_users:
        db.session.delete(u)
    db.session.commit()


def seed_database(clean_fake_data: bool = False):
    app = create_app()
    with app.app_context():
        print("==================================================")
        print("  SEEDING PRODUCT CATALOG & ADMIN ACCOUNT        ")
        print("==================================================")

        # 1. Seed Categories
        print("[1/3] Checking and seeding product categories...")
        cat_defs = [
            ("WOMEN", "women", "Fashion, clothing, and ethnic wear for women", "bi-gender-female"),
            ("MEN", "men", "Apparel, casual wear, and suits for men", "bi-gender-male"),
            ("CHILDREN", "children", "Outfits, toys, and essentials for kids and toddlers", "bi-balloon"),
            ("BEAUTY", "beauty", "Skincare, cosmetics, and self-care essentials", "bi-stars"),
        ]
        cat_map = {}
        for name, slug, desc, icon in cat_defs:
            cat = Category.query.filter_by(slug=slug).first()
            if not cat:
                cat = Category(name=name, slug=slug, description=desc, icon=icon)
                db.session.add(cat)
                db.session.flush()
                print(f"      + Added category: {name}")
            cat_map[name] = cat
        db.session.commit()

        # 2. Seed Catalog Products
        print("[2/3] Checking and seeding product catalog...")
        prod_count = 0
        for p in DEMO_PRODUCTS:
            prod = Product.query.filter_by(name=p["name"]).first()
            if not prod:
                cat = cat_map.get(p["category"])
                prod = Product(
                    category_id=cat.id,
                    subcategory=p["subcategory"],
                    name=p["name"],
                    price=p["price"],
                    stock=p["stock"],
                    description=p["description"],
                    image_url=p["image_url"],
                    created_at=datetime.utcnow()
                )
                db.session.add(prod)
                prod_count += 1
        db.session.commit()
        all_products = Product.query.all()
        print(f"      Total products in catalog: {len(all_products)} (Added: {prod_count})")

        # 3. Seed Admin User
        print("[3/3] Setting up Admin user...")
        admin_email = os.environ.get("ADMIN_EMAIL", "pavitrakasarapu@gmail.com").strip().lower()
        admin_pass = os.environ.get("ADMIN_PASSWORD", "Admin@123")
        admin_name = os.environ.get("ADMIN_NAME", "Administrator")
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                name=admin_name,
                email=admin_email,
                phone="9876543210",
                role="admin",
                is_active_account=True
            )
            admin.set_password(admin_pass)
            db.session.add(admin)
            db.session.commit()
            print(f"      + Created Admin: {admin_email}")
        else:
            admin.role = "admin"
            admin.is_active_account = True
            db.session.commit()
            print(f"      Admin user verified (existing credentials preserved): {admin_email}")

        if clean_fake_data:
            clean_synthetic_data()

        print("==================================================")
        print("  CATALOG SEEDING COMPLETED SUCCESSFULLY!         ")
        print("  Customer analytics are 100% real dynamic data.  ")
        print("==================================================")


if __name__ == "__main__":
    seed_database()
