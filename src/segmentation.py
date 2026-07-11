"""
Scores customers on R/F/M, clusters them with KMeans, auto-labels
each cluster based on its relative R/F/M profile, and writes the
result to both Postgres (rfm_scored) and data/processed/rfm_scored.csv.

Run from the src/ folder: python segmentation.py
"""

import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from db_connection import get_engine

N_CLUSTERS = 4
OUTPUT_CSV = "../data/processed/rfm_scored.csv"


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Add R/F/M quintile scores (1-5). Uses rank-based qcut to avoid
    'Bin edges must be unique' errors caused by repeated values."""
    rfm["R_score"] = pd.qcut(
        rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]
    ).astype(int)
    rfm["F_score"] = pd.qcut(
        rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    rfm["M_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    return rfm


def cluster_rfm(rfm: pd.DataFrame, n_clusters: int = N_CLUSTERS) -> pd.DataFrame:
    X = rfm[["recency_days", "frequency", "monetary"]]
    X_scaled = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    rfm["segment"] = kmeans.fit_predict(X_scaled)
    return rfm


def label_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Auto-names each cluster instead of requiring a hand-written dict.
    Ranks clusters on each dimension (recency ascending = better,
    frequency/monetary descending = better) and combines the ranks
    into a single composite score to order clusters from best to worst.
    """
    summary = rfm.groupby("segment")[["recency_days", "frequency", "monetary"]].mean()

    # Lower recency is better; higher frequency/monetary is better.
    summary["recency_rank"] = summary["recency_days"].rank(ascending=True)
    summary["frequency_rank"] = summary["frequency"].rank(ascending=False)
    summary["monetary_rank"] = summary["monetary"].rank(ascending=False)
    summary["composite_rank"] = (
        summary["recency_rank"] + summary["frequency_rank"] + summary["monetary_rank"]
    )
    summary = summary.sort_values("composite_rank")

    n = len(summary)
    label_pool = ["Champions", "Loyal Customers", "At Risk", "Lost / Churned"]
    # If N_CLUSTERS != 4, fall back to generic tier names.
    if n != len(label_pool):
        label_pool = [f"Tier {i+1}" for i in range(n)]

    segment_to_label = {
        seg_id: label_pool[i] for i, seg_id in enumerate(summary.index)
    }
    rfm["segment_label"] = rfm["segment"].map(segment_to_label)

    print("\nSegment profile (best to worst):")
    print(summary[["recency_days", "frequency", "monetary"]].round(1))
    print("\nLabel mapping:", segment_to_label)

    return rfm


def run_segmentation() -> None:
    engine = get_engine()
    rfm = pd.read_sql("SELECT * FROM rfm_table", engine)

    rfm = score_rfm(rfm)
    rfm = cluster_rfm(rfm)
    rfm = label_segments(rfm)

    rfm.to_sql("rfm_scored", engine, if_exists="replace", index=False)
    rfm.to_csv(OUTPUT_CSV, index=False)

    print(f"\nSaved {len(rfm)} scored customers to rfm_scored (DB) and {OUTPUT_CSV}")


if __name__ == "__main__":
    run_segmentation()
