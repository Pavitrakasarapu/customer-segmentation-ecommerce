"""
Database Seeder for Customer Segmentation E-Commerce.
Seeds:
- 4 Product Categories (WOMEN, MEN, CHILDREN, BEAUTY)
- Expanded Product Catalog (120+ distinct products per subcategory across 25 subcategories)
- Administrator Account (pavitrakasarapu@gmail.com)

DATABASE SAFETY GUARANTEE:
- Completely ADDITIVE and IDEMPOTENT.
- NEVER deletes users, orders, carts, wishlists, or activities.
- Safe to run on every deployment on Render.
"""
import os
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from models import db
from models.user import User
from models.product import Category, Product, ensure_product_schema
from catalog_data import generate_catalog_data


def seed_database():
    app = create_app()
    with app.app_context():
        print("==================================================")
        print("  SEEDING PRODUCT CATALOG & ADMIN ACCOUNT        ")
        print("==================================================")

        # 0. Ensure schema migrations are applied additively
        ensure_product_schema()

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

        # Backfill existing legacy products with unique SKUs and fields if missing
        legacy_products = Product.query.filter((Product.sku.is_(None)) | (Product.brand.is_(None))).all()
        if legacy_products:
            print(f"      * Updating {len(legacy_products)} legacy products with SKUs and metadata...")
            for lp in legacy_products:
                if not lp.sku:
                    lp.sku = f"SKU-LEGACY-{lp.id:04d}"
                if not lp.brand:
                    lp.brand = "Heritage Collection"
                if lp.rating is None:
                    lp.rating = 4.3
                if lp.discount is None:
                    lp.discount = 10
                if not lp.tags:
                    lp.tags = f"{lp.subcategory.lower()}, classic, quality"
            db.session.commit()

        # 2. Seed Expanded Catalog Products (Additive & Idempotent)
        print("[2/3] Checking and seeding expanded catalog (3,000 products)...")
        existing_skus = {s[0] for s in db.session.query(Product.sku).filter(Product.sku.isnot(None)).all()}
        existing_names = {n[0] for n in db.session.query(Product.name).all()}

        catalog_items = generate_catalog_data()
        added_count = 0
        batch_size = 200

        for item in catalog_items:
            # Check for existing SKU or name to avoid duplicates
            if item["sku"] in existing_skus or item["name"] in existing_names:
                continue

            cat = cat_map.get(item["category"])
            if not cat:
                continue

            product = Product(
                category_id=cat.id,
                subcategory=item["subcategory"],
                sku=item["sku"],
                brand=item["brand"],
                name=item["name"],
                price=item["price"],
                rating=item["rating"],
                discount=item["discount"],
                stock=item["stock"],
                description=item["description"],
                tags=item["tags"],
                image_url=item["image_url"],
                created_at=datetime.utcnow()
            )
            db.session.add(product)
            existing_skus.add(item["sku"])
            existing_names.add(item["name"])
            added_count += 1

            if added_count % batch_size == 0:
                db.session.commit()
                print(f"      ... Inserted {added_count} products ...")

        db.session.commit()
        total_products = Product.query.count()
        print(f"      Total products in catalog: {total_products} (Newly added: {added_count})")

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

        print("==================================================")
        print("  CATALOG SEEDING COMPLETED SUCCESSFULLY!         ")
        print(f"  Total catalog items: {total_products}")
        print("  Existing customer profiles & data are 100% safe.")
        print("==================================================")


if __name__ == "__main__":
    seed_database()
