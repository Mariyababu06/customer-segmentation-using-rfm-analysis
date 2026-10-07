from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from db_connection import get_engine

K_RANGE = range(3, 7)
MIN_CLUSTER_SHARE = 0.02  # reject clusterings with a cluster under 2% of customers
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "data" / "processed" / "rfm_scored.csv"


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """1-5 quintile scores (5 = best)."""
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


def prepare_features(rfm: pd.DataFrame) -> np.ndarray:
    """Log-transform skewed R, F, M, then standardise."""
    X = rfm[["recency_days", "frequency", "monetary"]].clip(lower=0)
    return StandardScaler().fit_transform(np.log1p(X))


def choose_k(X_scaled: np.ndarray) -> int:
    """Pick k with the best silhouette, ignoring k that creates tiny clusters."""
    results = []
    for k in K_RANGE:
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_scaled)
        smallest_share = np.bincount(labels).min() / len(labels)
        sil = silhouette_score(X_scaled, labels, sample_size=3000, random_state=42)
        results.append((k, sil, smallest_share))
        print(f"k={k}  silhouette={sil:.3f}  smallest cluster={smallest_share:.1%}")

    valid = [r for r in results if r[2] >= MIN_CLUSTER_SHARE] or results
    best_k = max(valid, key=lambda r: r[1])[0]
    print(f"Chosen k = {best_k}")
    return best_k


def cluster_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    X_scaled = prepare_features(rfm)
    k = choose_k(X_scaled)
    rfm["segment"] = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_scaled)
    return rfm


def name_segment(r: float, f: float, m: float) -> str:
    """
    Name a cluster from its average 1-5 scores (5 = best).
    Recency decides first: only recent clusters can be Champions/Loyal.
    """
    value = (f + m) / 2          # how valuable the customer is
    recent = r >= 3.5            # bought recently
    gone_quiet = r < 3.0         # clearly past their usual buying rhythm

    if recent and f >= 4 and m >= 4:
        return "Champions"
    if recent and value >= 3:
        return "Loyal Customers"
    if recent:
        return "Potential Loyalists"   # recent but low frequency/spend
    if gone_quiet and value >= 3:
        return "At Risk"               # good buyers who have gone quiet
    if gone_quiet:
        return "Lost / Churned"        # quiet and low value
    return "Needs Attention"           # middle recency, low value


def label_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    """Labels follow behaviour, never rank order."""
    summary = rfm.groupby("segment").agg(
        customers=("segment", "size"),
        avg_recency_days=("recency_days", "mean"),
        avg_orders=("frequency", "mean"),
        avg_spend=("monetary", "mean"),
        R=("R_score", "mean"),
        F=("F_score", "mean"),
        M=("M_score", "mean"),
    )
    summary["label"] = [name_segment(r.R, r.F, r.M) for r in summary.itertuples()]
    rfm["segment_label"] = rfm["segment"].map(summary["label"])

    print("\nSegment profile:")
    print(summary.round(1).sort_values("avg_recency_days").to_string())

    # Sanity checks so a wrong label can't slip through silently
    if summary["label"].duplicated().any():
        print("\nWARNING: two clusters share a label. Review the profile above.")
    if "At Risk" not in set(summary["label"]):
        print("\nWARNING: no cluster is labelled 'At Risk'. Q3 and Q7 will be empty.")
    return rfm


def run_segmentation() -> None:
    engine = get_engine()
    rfm = pd.read_sql("SELECT * FROM rfm_table", engine)

    rfm = score_rfm(rfm)
    rfm = cluster_rfm(rfm)
    rfm = label_segments(rfm)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rfm.to_sql("rfm_scored", engine, if_exists="replace", index=False)
    rfm.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(rfm)} customers to rfm_scored (DB) and {OUTPUT_CSV}")


if __name__ == "__main__":
    run_segmentation()