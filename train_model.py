"""
Model training pipeline for behavioral customer segmentation using KMeans.
Extracts features from SQLite database, scales features, fits KMeans, analyzes
cluster profiles, maps clusters to meaningful business labels, and saves artifacts.
"""
import sys
from pathlib import Path
from datetime import datetime
import joblib
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Ensure project root is in python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from models import db
from models.user import User
from ml.features import FEATURE_COLUMNS, extract_all_customer_features
from ml.segmenter import ARTIFACTS_DIR, MODEL_PATH, SCALER_PATH, METADATA_PATH, SegmentationEngine, recalculate_all_segments


def map_clusters_to_labels(df: pd.DataFrame, cluster_labels: np.ndarray, n_clusters: int) -> dict:
    """
    Intelligently analyzes cluster centers and behavioral statistics to map
    numeric cluster IDs to meaningful business labels:
    - HIGH VALUE CUSTOMER
    - REGULAR CUSTOMER
    - NEW CUSTOMER
    - DISCOUNT SEEKER
    - AT-RISK CUSTOMER
    """
    df_copy = df.copy()
    df_copy["cluster"] = cluster_labels
    
    profiles = {}
    for c in range(n_clusters):
        c_df = df_copy[df_copy["cluster"] == c]
        if len(c_df) == 0:
            profiles[c] = {col: 0.0 for col in FEATURE_COLUMNS}
            profiles[c]["size"] = 0
            continue
        means = c_df[FEATURE_COLUMNS].mean().to_dict()
        means["size"] = len(c_df)
        profiles[c] = means

    assigned_labels = {}
    remaining_clusters = list(range(n_clusters))

    # 1. HIGH VALUE CUSTOMER: Highest monetary spending
    if remaining_clusters:
        high_val_cluster = max(remaining_clusters, key=lambda c: profiles[c].get("monetary", 0.0))
        assigned_labels[high_val_cluster] = "HIGH VALUE CUSTOMER"
        remaining_clusters.remove(high_val_cluster)

    # 2. AT-RISK CUSTOMER: Highest recency_days (days since last purchase/activity)
    if remaining_clusters:
        at_risk_cluster = max(remaining_clusters, key=lambda c: profiles[c].get("recency_days", 0.0))
        assigned_labels[at_risk_cluster] = "AT-RISK CUSTOMER"
        remaining_clusters.remove(at_risk_cluster)

    # 3. DISCOUNT SEEKER: High views/cart/wishlist relative to monetary
    if remaining_clusters:
        def seeker_score(c):
            p = profiles[c]
            engagement = p.get("product_views", 0) + p.get("cart_additions", 0) * 2 + p.get("wishlist_count", 0) * 2
            monetary = max(1.0, p.get("monetary", 1.0))
            return engagement / monetary

        discount_cluster = max(remaining_clusters, key=seeker_score)
        assigned_labels[discount_cluster] = "DISCOUNT SEEKER"
        remaining_clusters.remove(discount_cluster)

    # 4. NEW CUSTOMER: Lowest frequency or smallest monetary among remaining
    if remaining_clusters:
        new_cluster = min(remaining_clusters, key=lambda c: profiles[c].get("frequency", 0))
        assigned_labels[new_cluster] = "NEW CUSTOMER"
        remaining_clusters.remove(new_cluster)

    # 5. REGULAR CUSTOMER: Any remaining clusters
    for c in remaining_clusters:
        assigned_labels[c] = "REGULAR CUSTOMER"

    return assigned_labels, profiles


def train_model(n_clusters: int = 5):
    print("==================================================")
    print("  CUSTOMER BEHAVIORAL SEGMENTATION MODEL TRAINING ")
    print("==================================================")

    app = create_app()
    with app.app_context():
        print("[1/5] Extracting customer behavioral features from database...")
        df = extract_all_customer_features()
        customer_count = len(df)
        print(f"      Found {customer_count} customer records.")

        if customer_count < 2:
            print(f"[*] {customer_count} real customer(s) found. Need at least 2 customers to fit KMeans clusters.")
            print("    Real-time behavioral classification will use the robust heuristic RFM segmenter.")
            updated = recalculate_all_segments()
            print(f"    Recalculated {updated} customer segment records.")
            return True

        if customer_count < n_clusters:
            print(f"[*] Adjusting KMeans clusters to k={customer_count} based on available real customer count.")
            n_clusters = customer_count

        # Prepare feature matrix X
        X = df[FEATURE_COLUMNS].values
        print(f"[2/5] Preprocessing and scaling {len(FEATURE_COLUMNS)} features...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        print(f"[3/5] Fitting KMeans model with k={n_clusters} clusters...")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_predictions = kmeans.fit_predict(X_scaled)

        print("[4/5] Analyzing cluster profiles and mapping to business labels...")
        label_map, profiles = map_clusters_to_labels(df, cluster_predictions, n_clusters)

        for c, label in label_map.items():
            p = profiles[c]
            print(f"      Cluster {c} -> [{label}] (size: {p['size']}) | "
                  f"Avg Spend: ₹{p.get('monetary', 0.0):.2f}, "
                  f"Avg Orders: {p.get('frequency', 0):.1f}, "
                  f"Avg Recency: {p.get('recency_days', 0.0):.1f}d, "
                  f"Avg Views: {p.get('product_views', 0):.1f}")

        # Save artifacts
        print("[5/5] Saving model, scaler, and metadata to ml/artifacts/...")
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(kmeans, MODEL_PATH)
        joblib.dump(scaler, SCALER_PATH)

        metadata = {
            "cluster_labels": label_map,
            "profiles": profiles,
            "feature_columns": FEATURE_COLUMNS,
            "trained_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "n_samples": customer_count,
            "n_clusters": n_clusters,
        }
        joblib.dump(metadata, METADATA_PATH)
        print("      Model artifacts saved successfully!")

        # Reload engine and update all customer records in DB
        print("      Updating customer segment records in database...")
        SegmentationEngine.get_instance().load()
        updated = recalculate_all_segments()
        print(f"      Successfully updated {updated} customer segment records!")

    print("==================================================")
    print("  TRAINING COMPLETED SUCCESSFULLY!                ")
    print("==================================================")
    return True


if __name__ == "__main__":
    train_model()
