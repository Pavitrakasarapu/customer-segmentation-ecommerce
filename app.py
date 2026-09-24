import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_login import current_user

from config import config_by_name
from models import db, login_manager
from models.cart import CartItem, WishlistItem
from models.activity import LoginSession
from models.user import User

csrf = CSRFProtect()


def create_app(config_name: str = None) -> Flask:
    """Application factory for Customer Segmentation E-Commerce"""
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG") or os.environ.get("FLASK_ENV") or ("production" if os.environ.get("RENDER") else "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Support reverse proxy headers when running behind Render/production proxies
    if os.environ.get("RENDER") or config_name == "production":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Exclude API endpoints that use token or lightweight json from csrf if necessary,
    # or pass csrf token in fetch headers. Heartbeat can be exempted for seamless polling.
    from routes.api import api_bp
    csrf.exempt(api_bp)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.shop import shop_bp
    from routes.segmentation import segmentation_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(segmentation_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Context processors for global template access
    @app.context_processor
    def inject_globals():
        cart_count = 0
        wishlist_count = 0
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
                wishlist_count = WishlistItem.query.filter_by(user_id=current_user.id).count()
            except Exception:
                cart_count = 0
                wishlist_count = 0

        return {
            "current_year": datetime.utcnow().year,
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
        }

    # Security & Cache Control: Prevent stale authenticated pages from browser cache after logout
    @app.after_request
    def set_cache_control(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template("errors/csrf_error.html", reason=e.description), 400

    # Ensure DB tables exist on initial boot and schema migrations are applied additively
    with app.app_context():
        db.create_all()
        from models.product import ensure_product_schema
        ensure_product_schema()

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
