from datetime import datetime
from models import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # WOMEN, MEN, CHILDREN, BEAUTY
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default="bi-tag")

    products = db.relationship("Product", back_populates="category", cascade="all, delete-orphan", lazy="select")

    def __repr__(self):
        return f"<Category {self.name}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    sku = db.Column(db.String(60), unique=True, index=True, nullable=True)
    brand = db.Column(db.String(100), index=True, nullable=True)
    subcategory = db.Column(db.String(100), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, default=4.2, nullable=True)
    discount = db.Column(db.Integer, default=0, nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    stock = db.Column(db.Integer, default=50, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    category = db.relationship("Category", back_populates="products")
    order_items = db.relationship("OrderItem", back_populates="product", cascade="all, delete-orphan", lazy="select")
    cart_items = db.relationship("CartItem", back_populates="product", cascade="all, delete-orphan", lazy="select")
    wishlist_items = db.relationship("WishlistItem", back_populates="product", cascade="all, delete-orphan", lazy="select")

    @property
    def original_price(self):
        """Calculates original price before discount if discount > 0"""
        if self.discount and self.discount > 0 and self.discount < 100:
            return round(self.price / (1 - (self.discount / 100.0)), 2)
        return self.price

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "name": self.name,
            "sku": self.sku or f"SKU-{self.id}",
            "brand": self.brand or "",
            "subcategory": self.subcategory,
            "price": self.price,
            "original_price": self.original_price,
            "rating": self.rating or 4.2,
            "discount": self.discount or 0,
            "tags": self.tags or "",
            "description": self.description,
            "image_url": self.image_url,
            "stock": self.stock,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

    def __repr__(self):
        return f"<Product {self.name} [{self.sku}] (₹{self.price})>"


def ensure_product_schema(engine=None):
    """
    Safely and additively ensures products table has new columns (sku, brand, rating, discount, tags)
    without dropping tables or touching any customer data. Compatible with SQLite and PostgreSQL.
    """
    from sqlalchemy import inspect, text
    target_engine = engine or db.engine
    inspector = inspect(target_engine)
    if "products" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("products")}
    with target_engine.connect() as conn:
        if "sku" not in cols:
            conn.execute(text("ALTER TABLE products ADD COLUMN sku VARCHAR(60)"))
        if "brand" not in cols:
            conn.execute(text("ALTER TABLE products ADD COLUMN brand VARCHAR(100)"))
        if "rating" not in cols:
            conn.execute(text("ALTER TABLE products ADD COLUMN rating FLOAT DEFAULT 4.2"))
        if "discount" not in cols:
            conn.execute(text("ALTER TABLE products ADD COLUMN discount INTEGER DEFAULT 0"))
        if "tags" not in cols:
            conn.execute(text("ALTER TABLE products ADD COLUMN tags VARCHAR(255)"))
        
        # Safe unique index on sku
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_products_sku ON products (sku)"))
        except Exception:
            pass

        # Index on subcategory if not present
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_subcategory ON products (subcategory)"))
        except Exception:
            pass

        # Index on brand if not present
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_brand ON products (brand)"))
        except Exception:
            pass

        conn.commit()
