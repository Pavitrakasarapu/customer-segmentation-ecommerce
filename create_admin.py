"""
Script to create or update an administrator account.
Can be executed via CLI with arguments or environment variables.
"""
import sys
import os
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from models import db
from models.user import User


def setup_admin(email: str = None, password: str = None, name: str = None):
    app = create_app()
    with app.app_context():
        email = (email or os.environ.get("ADMIN_EMAIL") or "pavitrakasarapu@gmail.com").strip().lower()
        password = password or os.environ.get("ADMIN_PASSWORD") or "Admin@123"
        name = name or os.environ.get("ADMIN_NAME") or "Administrator"

        user = User.query.filter_by(email=email).first()
        if user:
            user.role = "admin"
            user.name = name
            user.set_password(password)
            user.is_active_account = True
            db.session.commit()
            print(f"[+] Existing user '{email}' updated to Administrator successfully.")
        else:
            admin = User(
                name=name,
                email=email,
                phone="9876543210",
                role="admin",
                is_active_account=True
            )
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"[+] New Administrator created successfully with email: {email}")

        print("--------------------------------------------------")
        print(f"  Admin Email   : {email}")
        print(f"  Admin Password: {'*' * len(password)}")
        print("--------------------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update an admin user.")
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--password", help="Admin password")
    parser.add_argument("--name", help="Admin display name")
    args = parser.parse_args()

    setup_admin(args.email, args.password, args.name)
