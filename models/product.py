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
    subcategory = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    stock = db.Column(db.Integer, default=50, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    category = db.relationship("Category", back_populates="products")
    order_items = db.relationship("OrderItem", back_populates="product", cascade="all, delete-orphan", lazy="select")
    cart_items = db.relationship("CartItem", back_populates="product", cascade="all, delete-orphan", lazy="select")
    wishlist_items = db.relationship("WishlistItem", back_populates="product", cascade="all, delete-orphan", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "name": self.name,
            "subcategory": self.subcategory,
            "price": self.price,
            "description": self.description,
            "image_url": self.image_url,
            "stock": self.stock,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }

    def __repr__(self):
        return f"<Product {self.name} (₹{self.price})>"
