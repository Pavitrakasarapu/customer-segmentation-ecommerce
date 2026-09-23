# Customer Segmentation E-Commerce Platform
### Real-Time Machine Learning Behavioral Clustering & Privacy-Preserving Analytics

A full-stack, production-grade e-commerce web application built with **Python**, **Flask**, **SQLAlchemy**, and **Scikit-Learn**. The platform automatically tracks real-time customer behavior (product views, category browsing, cart activity, wishlist toggles, search queries, and purchase transactions) and dynamically assigns users to ML-driven behavioral clusters using **K-Means** and **RFM (Recency, Frequency, Monetary)** modeling.

---

## Key Features

1. **E-Commerce Experience**:
   - Product catalog across 4 categories: **WOMEN**, **MEN**, **CHILDREN**, and **BEAUTY**.
   - Subcategories including Dresses, Sarees, Formal Shirts, Denim, Kurtis, Footwear, Toys, Skincare, etc.
   - Live search bar and category filter navigation.
   - Interactive Wishlist toggles and Shopping Cart.
   - Checkout with Cash on Delivery (COD) and automated stock management.
   - My Orders tracking and individual order confirmation summaries.

2. **Machine Learning Customer Segmentation**:
   - **K-Means Clustering** engine combined with **RFM Analysis** and behavioral features:
     - Recency (days since last purchase/activity)
     - Frequency (total orders placed)
     - Monetary (total order spend in USD)
     - Average Order Value (AOV)
     - Product Views count
     - Search queries count
     - Wishlist additions count
     - Cart additions count
     - Categories bought count
     - Recent 7-day activity velocity
   - Segment Labels:
     - `HIGH VALUE CUSTOMER`: Frequent orders and high monetary spend.
     - `REGULAR CUSTOMER`: Consistent repeat buyer with steady store engagement.
     - `NEW CUSTOMER`: Recently registered user exploring products.
     - `DISCOUNT SEEKER`: High browsing/wishlist/cart interest with few purchases.
     - `AT-RISK CUSTOMER`: Inactive customer whose last purchase was long ago.
   - **Real-Time Recalculation**: Customer segments update immediately upon placing orders, viewing products, or updating carts.
   - **Personal Behavioral Profile** (`/segmentation/my-segment`): Transparent plain-English breakdown of why the customer belongs to their segment with tailored product recommendations.

3. **Multi-User Live Segmentation Board & Privacy Protection**:
   - Live active customers board (`/segmentation`) polling sessions in real time.
   - **Strict Privacy Guarantee**: Other customers see **ONLY** the customer's **Name** and **Current Segment**.
   - Private customer data (email, phone, address, cart, order history, spending) is never exposed to other customers.

4. **Executive Administrator Dashboard**:
   - KPI metrics: Total Customers, Active Customers, Total Orders, Total Revenue.
   - Interactive **Chart.js** visualizations:
     - Customer Distribution by Segment
     - Revenue by Customer Segment
     - Orders by Customer Segment
     - 7-Day Activity Velocity
     - Category Popularity
   - Customer Directory with 360-degree customer intelligence drill-down.
   - Real-time Activity Audit Logs with type and customer filtering.
   - One-click ML model retraining trigger (`/admin/retrain`).

5. **Authentication & Security**:
   - Role-based access control (`customer` vs `admin`).
   - Werkzeug secure password hashing.
   - Cryptographically secure 6-digit OTP password reset workflow (with development fallback mode).
   - CSRF protection across all forms using Flask-WTF.
   - Heartbeat session tracking with automatic stale session cleanup.

---

## Demo Credentials

| Role | Email | Password | Segment / Notes |
| :--- | :--- | :--- | :--- |
| **Customer A** | `pavitra@example.com` | `Pavitra@123` | High Value Customer |
| **Customer B** | `anu@example.com` | `Anu@123` | Regular Customer |
| **Admin** | `pavitrakasarapu@gmail.com` | `Admin@123` | Store Administrator |

---

## Windows Setup Instructions

### Prerequisites
- **Python 3.11+** installed on Windows.
- Ensure `python` and `pip` are added to your system `PATH`.
- Check in PowerShell or Command Prompt:
  ```powershell
  python --version
  ```

---

### Option 1: One-Click Launch (Recommended)

Simply double-click or run:
```cmd
START_PROJECT.bat
```
This script will automatically:
1. Detect Python 3.11+.
2. Create the virtual environment `.venv` if not present.
3. Activate the virtual environment.
4. Install or verify all dependencies from `requirements.txt`.
5. Create the `instance/` directory and seed initial demo data (`seed.py`).
6. Train the ML K-Means model (`train_model.py`) and save artifacts.
7. Verify or create the Administrator account (`create_admin.py`).
8. Run automated tests (`pytest`).
9. Launch the Flask web server at `http://127.0.0.1:5000` and automatically open your default browser.

---

### Option 2: Run Automated Tests

To run the automated test suite at any time:
```cmd
TEST_PROJECT.bat
```
Or in PowerShell:
```powershell
.venv\Scripts\activate
pytest -v
```

---

### Option 3: Manual Step-by-Step Setup

If you prefer to configure manually via PowerShell or Command Prompt:

1. **Clone or Navigate to the Project Directory**:
   ```powershell
   cd customer_segment_ecommerce
   ```

2. **Create and Activate a Virtual Environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables (Optional)**:
   Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```

5. **Seed the Database**:
   ```powershell
   python seed.py
   ```

6. **Train the ML Segmentation Model**:
   ```powershell
   python train_model.py
   ```

7. **Create or Verify the Admin Account**:
   ```powershell
   python create_admin.py --email pavitrakasarapu@gmail.com --password Admin@123 --name "Administrator"
   ```

8. **Run the Application**:
   ```powershell
   python app.py
   ```
   Open your browser to: **`http://127.0.0.1:5000`**

---

## Testing Two Simultaneous Customers (Multi-User Verification)

To test simultaneous customer presence and verify privacy compliance:

1. **Open Customer A**:
   - Open standard browser window: `http://127.0.0.1:5000`
   - Log in as **Pavitra** (`pavitra@example.com` / `Pavitra@123`).
   - Navigate to **CUSTOMER SEGMENTATION** in the top navigation bar (`/segmentation`).
   - Notice Pavitra listed with segment badge: **`HIGH VALUE CUSTOMER`**.

2. **Open Customer B**:
   - Open an **Incognito / Private Window** (or a different browser such as Chrome, Edge, Firefox).
   - Navigate to: `http://127.0.0.1:5000`
   - Log in as **Anu** (`anu@example.com` / `Anu@123`).
   - Navigate to **CUSTOMER SEGMENTATION** (`/segmentation`).

3. **Verify Simultaneous Presence & Privacy**:
   - On **both** windows, the Live Active Customers board will display **2 CUSTOMERS ACTIVE**.
   - Both **Pavitra** and **Anu** are visible to each other.
   - **Customer Privacy Check**: Observe that ONLY the customer's **Name** and **Current Segment** are displayed.
   - Neither customer can view the other's email address, telephone number, order history, or cart items.

---

## Project Structure

```text
customer_segment_ecommerce/
│
├── app.py                     # Flask application factory and error handlers
├── config.py                  # Dev, Test, Prod configuration classes
├── requirements.txt           # Python dependencies
├── Procfile                   # Cloud / Render deployment entrypoint
├── runtime.txt                # Python runtime specification (3.11.9)
├── seed.py                    # Comprehensive demo database seeder
├── train_model.py             # K-Means clustering training and evaluation pipeline
├── create_admin.py            # CLI utility for managing admin accounts
├── START_PROJECT.bat          # One-click Windows application launcher
├── TEST_PROJECT.bat           # One-click Windows test suite runner
├── README.md                  # Complete documentation and setup guide
│
├── ml/                        # Machine Learning engine
│   ├── __init__.py
│   ├── features.py            # RFM + behavioral feature extractor
│   ├── segmenter.py           # SegmentationEngine & real-time recalculation
│   └── artifacts/             # Serialized KMeans model, scaler, metadata
│       ├── kmeans_model.joblib
│       ├── scaler.joblib
│       └── metadata.joblib
│
├── models/                    # SQLAlchemy database models
│   ├── __init__.py            # DB initialization & user_loader
│   ├── user.py                # User model (Customer & Admin)
│   ├── product.py             # Product & Category models
│   ├── order.py               # Order & OrderItem models
│   ├── cart.py                # CartItem & WishlistItem models
│   ├── activity.py            # CustomerActivity & LoginSession models
│   ├── segment.py             # CustomerSegment model & explanations
│   └── otp.py                 # OTPVerification model
│
├── routes/                    # Blueprint controllers
│   ├── __init__.py            # admin_required decorator
│   ├── auth.py                # Login, register, logout, OTP reset
│   ├── shop.py                # Catalog, search, wishlist, cart, checkout
│   ├── segmentation.py        # Segmentation board & personal analytics
│   ├── admin.py               # Admin dashboard, customers 360, logs, retrain
│   └── api.py                 # Heartbeat, active-customers, my-segment API
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Layout, navbar, footer, modals
│   ├── login.html             # Login form
│   ├── register.html          # Registration form
│   ├── forgot_password.html   # OTP request form
│   ├── reset_password.html    # OTP verification & password reset form
│   ├── shop/                  # Catalog, detail, cart, checkout, orders
│   ├── segmentation/          # Live active board, personal segment stats
│   ├── admin/                 # Dashboard, customers directory, activity logs
│   └── errors/                # 403, 404, 500, CSRF error pages
│
├── static/                    # CSS, JS, and assets
│   ├── css/style.css          # Modern custom design system
│   └── js/main.js             # Session heartbeat & real-time polling
│
└── tests/                     # Automated pytest suite
    ├── conftest.py            # Fixtures for test app and mock data
    ├── test_auth.py           # Authentication & OTP tests
    ├── test_shop.py           # Catalog, cart & checkout tests
    ├── test_segmentation_and_privacy.py # Multi-user & privacy tests
    └── test_admin.py          # Admin security & analytics tests
```

---

## Production Deployment to Render

This application is fully production-ready for deployment on [Render](https://render.com).

### Prerequisites
- A free [Render.com](https://render.com) account.
- Your project pushed to a GitHub or GitLab repository.

### Recommended Configuration
- **Runtime**: Python 3 (`runtime.txt`: `python-3.11.9`)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python seed.py && gunicorn --bind 0.0.0.0:$PORT "app:create_app()"`
- **Web Concurrency**: Gunicorn with multi-threaded workers (configured via `gunicorn.conf.py`).

---

### Method A: 1-Click Blueprint Deployment (Recommended)

1. Push this repository to your GitHub/GitLab.
2. In the Render Dashboard, click **New +** -> **Blueprint**.
3. Connect your repository.
4. Render will read [`render.yaml`](render.yaml) and automatically configure:
   - **Web Service**: `customer-segmentation-ecommerce` (Free Python Web Service)
   - **Database**: `customer-segmentation-db` (Free Managed PostgreSQL)
   - All required environment variables and auto-generated `SECRET_KEY`.
5. Click **Apply**. Render will provision PostgreSQL, install dependencies, run `seed.py`, and launch Gunicorn.

---

### Method B: Manual Web Service Deployment

#### Step 1: Create a PostgreSQL Database (Optional but Recommended for Production)
1. In Render Dashboard, click **New +** -> **PostgreSQL**.
2. Set Name: `customer-segmentation-db`.
3. Set Database Name: `customer_segmentation`.
4. Set User: `cs_user`.
5. Select the **Free** tier and click **Create Database**.
6. Once provisioned, copy the **Internal Database URL** (e.g., `postgresql://...`).

> **Note on SQLite vs PostgreSQL**:
> If you do not configure a PostgreSQL database, the app will automatically use local SQLite (`instance/customer_segmentation.db`). However, Render's free web service containers use ephemeral disks, so any data written to SQLite will reset on redeployment. Using Render's managed PostgreSQL guarantees persistent data.

#### Step 2: Create the Web Service
1. Click **New +** -> **Web Service**.
2. Select your repository.
3. Configure the settings:
   - **Name**: `customer-segmentation-ecommerce`
   - **Region**: Same region as your database (e.g., Oregon)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python seed.py && gunicorn --bind 0.0.0.0:$PORT "app:create_app()"`
   - **Plan**: `Free`

#### Step 3: Add Environment Variables
Under **Environment Variables**, add:

| Key | Value | Notes |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | Matches `runtime.txt` |
| `FLASK_ENV` | `production` | Enables secure cookies and production mode |
| `SECRET_KEY` | *(Click Generate or paste random 32+ char hex)* | Session & CSRF encryption |
| `DATABASE_URL` | *(Paste Internal PostgreSQL URL from Step 1)* | Leave blank to use local SQLite |
| `ADMIN_NAME` | `Administrator` | Display name for administrator |
| `ADMIN_EMAIL` | `pavitrakasarapu@gmail.com` | Sole administrator email |
| `ADMIN_PASSWORD` | `Admin@123` | Administrator password |
| `MAIL_SERVER` | `smtp.gmail.com` | Optional: for Password Reset OTP emails |
| `MAIL_PORT` | `587` | Optional |
| `MAIL_USE_TLS` | `True` | Optional |

4. Click **Deploy Web Service**.
5. Once deployment completes, your live store will be accessible at `https://your-service-name.onrender.com`.

---

### Local Testing with Production Configuration
To test the production-style Gunicorn setup locally:

```bash
# Set environment variables
export FLASK_ENV=production
export SECRET_KEY=local-dev-secret-key-test
export SESSION_COOKIE_SECURE=false   # Set to false when testing locally over HTTP
export PORT=5000

# Seed database and start with Gunicorn
python seed.py
gunicorn --bind 0.0.0.0:5000 "app:create_app()"
```

