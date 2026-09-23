import os
from pathlib import Path
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from models import db
from models.user import User
from models.segment import CustomerSegment
from ml.features import FEATURE_COLUMNS, extract_single_customer_features, extract_all_customer_features

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "kmeans_model.joblib"
SCALER_PATH = ARTIFACTS_DIR / "scaler.joblib"
METADATA_PATH = ARTIFACTS_DIR / "metadata.joblib"


class SegmentationEngine:
    _instance = None

    def __init__(self):
        self.model: KMeans = None
        self.scaler: StandardScaler = None
        self.metadata: dict = {}
        self.cluster_labels: dict = {}
        self.load()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self):
        """Load trained model, scaler, and metadata from disk"""
        try:
            if MODEL_PATH.exists() and SCALER_PATH.exists() and METADATA_PATH.exists():
                self.model = joblib.load(MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
                self.metadata = joblib.load(METADATA_PATH)
                self.cluster_labels = self.metadata.get("cluster_labels", {})
            else:
                self.model = None
                self.scaler = None
                self.metadata = {}
                self.cluster_labels = {}
        except Exception as e:
            print(f"[SegmentationEngine] Error loading model: {e}")
            self.model = None
            self.scaler = None

    def is_trained(self) -> bool:
        return self.model is not None and self.scaler is not None

    def heuristic_classify(self, feats: dict) -> tuple[int, str]:
        """
        Robust heuristic fallback when KMeans artifacts are not yet saved.
        Maps behavior cleanly to the 5 business labels.
        """
        monetary = feats.get("monetary", 0.0)
        frequency = feats.get("frequency", 0)
        recency = feats.get("recency_days", 0.0)
        views = feats.get("product_views", 0)
        cart = feats.get("cart_additions", 0)
        wishlist = feats.get("wishlist_count", 0)

        # High Value: High monetary spend or high frequency
        if monetary >= 1500 or frequency >= 5:
            return 0, "HIGH VALUE CUSTOMER"
        
        # At Risk: Has bought before, but inactive for > 30 days
        if frequency >= 1 and recency > 30:
            return 1, "AT-RISK CUSTOMER"
            
        # Discount Seeker: Many views, cart or wishlist additions, but low/no orders
        if (views >= 5 or cart >= 3 or wishlist >= 3) and frequency <= 1:
            return 2, "DISCOUNT SEEKER"

        # Regular Customer: Moderate frequency and purchases
        if frequency >= 2 and monetary >= 400:
            return 3, "REGULAR CUSTOMER"

        # Default / New: Few or recent activities
        return 4, "NEW CUSTOMER"

    def predict_single(self, feats: dict) -> tuple[int, str]:
        """Predict cluster and business segment label for customer features"""
        if not self.is_trained():
            return self.heuristic_classify(feats)

        try:
            # Build feature vector matching FEATURE_COLUMNS
            x = np.array([[feats.get(col, 0.0) for col in FEATURE_COLUMNS]])
            x_scaled = self.scaler.transform(x)
            cluster_id = int(self.model.predict(x_scaled)[0])
            label = self.cluster_labels.get(cluster_id, "REGULAR CUSTOMER")
            return cluster_id, label
        except Exception as e:
            print(f"[SegmentationEngine] Prediction error: {e}. Falling back to heuristic.")
            return self.heuristic_classify(feats)


def recalculate_customer_segment(user_id: int) -> CustomerSegment:
    """Recalculate and persist the segment for a single customer"""
    feats = extract_single_customer_features(user_id)
    if not feats:
        return None

    engine = SegmentationEngine.get_instance()
    cluster_id, label = engine.predict_single(feats)

    seg = CustomerSegment.query.filter_by(user_id=user_id).first()
    if not seg:
        seg = CustomerSegment(user_id=user_id)
        db.session.add(seg)

    seg.cluster_id = cluster_id
    seg.segment_label = label
    seg.recency_days = feats["recency_days"]
    seg.frequency = feats["frequency"]
    seg.monetary = feats["monetary"]
    seg.avg_order_value = feats["avg_order_value"]
    seg.product_views = feats["product_views"]
    seg.searches = feats["searches"]
    seg.wishlist_count = feats["wishlist_count"]
    seg.cart_additions = feats["cart_additions"]
    seg.categories_bought = feats["categories_bought"]
    seg.last_updated = datetime.utcnow()

    db.session.commit()
    return seg


def recalculate_all_segments() -> int:
    """Recalculates segments for all registered customers"""
    customers = User.query.filter_by(role="customer").all()
    count = 0
    for customer in customers:
        recalculate_customer_segment(customer.id)
        count += 1
    return count
