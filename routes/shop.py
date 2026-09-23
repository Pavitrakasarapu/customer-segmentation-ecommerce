from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db
from models.product import Product, Category
from models.cart import CartItem, WishlistItem
from models.order import Order, OrderItem
from models.activity import CustomerActivity
from ml.segmenter import recalculate_customer_segment

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/")
@shop_bp.route("/shop")
@login_required
def index():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    query = request.args.get("q", "").strip()
    category_slug = request.args.get("category", "").strip().lower()
    subcategory = request.args.get("subcategory", "").strip()

    categories = Category.query.all()
    products_query = Product.query

    selected_category = None
    if category_slug:
        selected_category = Category.query.filter_by(slug=category_slug).first()
        if selected_category:
            products_query = products_query.filter_by(category_id=selected_category.id)
            CustomerActivity.log("CATEGORY_VIEW", user=current_user, category_id=selected_category.id, metadata={"category": selected_category.name})

    if subcategory:
        products_query = products_query.filter(Product.subcategory.ilike(f"%{subcategory}%"))

    if query:
        products_query = products_query.filter(
            db.or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%"),
                Product.subcategory.ilike(f"%{query}%")
            )
        )
        CustomerActivity.log("SEARCH", user=current_user, metadata={"query": query})

    products = products_query.order_by(Product.id.asc()).all()

    # User's current wishlist product IDs for easy UI heart toggles
    wishlist_product_ids = {
        item.product_id for item in WishlistItem.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        "shop/index.html",
        products=products,
        categories=categories,
        selected_category=selected_category,
        query=query,
        subcategory=subcategory,
        wishlist_product_ids=wishlist_product_ids
    )


@shop_bp.route("/product/<int:product_id>")
@login_required
def product_detail(product_id: int):
    product = db.get_or_404(Product, product_id)

    # Log PRODUCT_VIEW activity & update behavioral segment
    CustomerActivity.log(
        "PRODUCT_VIEW",
        user=current_user,
        product_id=product.id,
        category_id=product.category_id,
        metadata={"name": product.name, "price": product.price}
    )
    recalculate_customer_segment(current_user.id)

    is_in_wishlist = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product.id).first() is not None
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()

    return render_template(
        "shop/product_detail.html",
        product=product,
        is_in_wishlist=is_in_wishlist,
        related_products=related_products
    )


@shop_bp.route("/cart")
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.subtotal for item in cart_items)
    shipping = 0.0  # Free shipping demo
    total = subtotal + shipping

    return render_template("shop/cart.html", cart_items=cart_items, subtotal=subtotal, shipping=shipping, total=total)


@shop_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id: int):
    product = db.get_or_404(Product, product_id)
    quantity = int(request.form.get("quantity", 1))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()

    # Log CART_ADD & update segment
    CustomerActivity.log(
        "CART_ADD",
        user=current_user,
        product_id=product.id,
        category_id=product.category_id,
        metadata={"quantity": quantity, "price": product.price}
    )
    recalculate_customer_segment(current_user.id)

    flash(f"Added '{product.name}' to your cart.", "success")
    return redirect(request.referrer or url_for("shop.cart"))


@shop_bp.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id: int):
    cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    quantity = int(request.form.get("quantity", 1))

    if quantity <= 0:
        db.session.delete(cart_item)
        CustomerActivity.log("CART_REMOVE", user=current_user, product_id=cart_item.product_id)
        flash("Item removed from cart.", "info")
    else:
        cart_item.quantity = quantity
        CustomerActivity.log("CART_UPDATE", user=current_user, product_id=cart_item.product_id, metadata={"quantity": quantity})
        flash("Cart updated.", "success")

    db.session.commit()
    recalculate_customer_segment(current_user.id)
    return redirect(url_for("shop.cart"))


@shop_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id: int):
    cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    prod_id = cart_item.product_id
    db.session.delete(cart_item)
    db.session.commit()

    CustomerActivity.log("CART_REMOVE", user=current_user, product_id=prod_id)
    recalculate_customer_segment(current_user.id)

    flash("Item removed from cart.", "info")
    return redirect(url_for("shop.cart"))


@shop_bp.route("/wishlist")
@login_required
def wishlist():
    items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template("shop/wishlist.html", wishlist_items=items)


@shop_bp.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id: int):
    product = db.get_or_404(Product, product_id)
    item = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()

    if item:
        db.session.delete(item)
        db.session.commit()
        CustomerActivity.log("WISHLIST_REMOVE", user=current_user, product_id=product.id, category_id=product.category_id)
        flash(f"Removed '{product.name}' from your wishlist.", "info")
    else:
        item = WishlistItem(user_id=current_user.id, product_id=product.id)
        db.session.add(item)
        db.session.commit()
        CustomerActivity.log("WISHLIST_ADD", user=current_user, product_id=product.id, category_id=product.category_id)
        flash(f"Added '{product.name}' to your wishlist.", "success")

    recalculate_customer_segment(current_user.id)
    return redirect(request.referrer or url_for("shop.wishlist"))


@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty. Please add items before checking out.", "warning")
        return redirect(url_for("shop.index"))

    total = sum(item.subtotal for item in cart_items)

    if request.method == "POST":
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        pincode = request.form.get("pincode", "").strip()
        payment_method = request.form.get("payment_method", "Cash on Delivery")

        if not address or not city or not pincode:
            flash("Please complete all shipping address fields.", "danger")
            return render_template("shop/checkout.html", cart_items=cart_items, total=total)

        # Log CHECKOUT activity
        CustomerActivity.log("CHECKOUT", user=current_user, metadata={"total": total, "items_count": len(cart_items)})

        # Create Order
        order = Order(
            user_id=current_user.id,
            order_number=Order.generate_order_number(),
            total_amount=total,
            status="Confirmed",
            payment_method=payment_method,
            shipping_address=address,
            shipping_city=city,
            shipping_pincode=pincode,
            created_at=datetime.utcnow()
        )
        db.session.add(order)
        db.session.flush()  # populate order.id

        # Create OrderItems
        for ci in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=ci.product_id,
                quantity=ci.quantity,
                price=ci.product.price,
                subtotal=ci.subtotal
            )
            db.session.add(order_item)
            # Decrement stock safely
            if ci.product.stock >= ci.quantity:
                ci.product.stock -= ci.quantity

        # Clear cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        # Log ORDER_PLACED activity
        CustomerActivity.log(
            "ORDER_PLACED",
            user=current_user,
            metadata={"order_number": order.order_number, "total": total}
        )

        # Recalculate customer segment immediately (Real-Time update!)
        updated_seg = recalculate_customer_segment(current_user.id)

        flash(f"Order #{order.order_number} placed successfully! Your current segment is: {updated_seg.segment_label}", "success")
        return redirect(url_for("shop.order_confirmation", order_number=order.order_number))

    return render_template("shop/checkout.html", cart_items=cart_items, total=total)


@shop_bp.route("/order-confirmation/<order_number>")
@login_required
def order_confirmation(order_number: str):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    CustomerActivity.log("ORDER_VIEW", user=current_user, metadata={"order_number": order.order_number})
    return render_template("shop/order_confirmation.html", order=order)


@shop_bp.route("/orders")
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("shop/orders.html", orders=user_orders)


@shop_bp.route("/orders/<order_number>")
@login_required
def order_detail(order_number: str):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    CustomerActivity.log("ORDER_VIEW", user=current_user, metadata={"order_number": order.order_number})
    return render_template("shop/order_detail.html", order=order)


@shop_bp.route("/profile")
@login_required
def profile():
    CustomerActivity.log("PROFILE_VIEW", user=current_user)
    orders_count = Order.query.filter_by(user_id=current_user.id).count()
    orders_total = sum(o.total_amount for o in Order.query.filter_by(user_id=current_user.id).all())
    return render_template("shop/profile.html", user=current_user, orders_count=orders_count, orders_total=orders_total)
