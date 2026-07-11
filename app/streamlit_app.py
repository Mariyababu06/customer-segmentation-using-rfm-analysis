import streamlit as st
import pandas as pd

st.set_page_config(page_title="RFM Customer Segmentation", layout="wide")
st.title("Customer Segmentation — RFM Analysis")

DATA_PATH = "data/processed/rfm_scored.csv"


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


try:
    df = load_data(DATA_PATH)
except FileNotFoundError:
    st.error(
        f"Could not find {DATA_PATH}. Run `python src/segmentation.py` first "
        "to generate the scored dataset."
    )
    st.stop()

# --- Headline business insight -------------------------------------------------
total_revenue = df["monetary"].sum()
df_sorted = df.sort_values("monetary", ascending=False).reset_index(drop=True)
top_10pct_count = max(1, int(len(df_sorted) * 0.10))
top_10pct_revenue = df_sorted.loc[: top_10pct_count - 1, "monetary"].sum()
top_10pct_share = 100 * top_10pct_revenue / total_revenue if total_revenue else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total customers", f"{len(df):,}")
col2.metric("Total revenue", f"${total_revenue:,.0f}")
col3.metric("Revenue from top 10% of customers", f"{top_10pct_share:.1f}%")

st.divider()

# --- Segment charts -------------------------------------------------------------
label_col = "segment_label" if "segment_label" in df.columns else "segment"

c1, c2 = st.columns(2)
with c1:
    st.subheader("Customers per segment")
    st.bar_chart(df[label_col].value_counts())

with c2:
    st.subheader("Revenue by segment")
    st.bar_chart(df.groupby(label_col)["monetary"].sum())

st.subheader("Segment profile (averages)")
st.dataframe(
    df.groupby(label_col)[["recency_days", "frequency", "monetary"]]
    .mean()
    .round(1)
    .sort_values("monetary", ascending=False)
)

st.divider()

# --- Customer lookup -------------------------------------------------------------
st.subheader("Look up a customer")
cust_id_input = st.text_input("Customer ID (numeric)")

if cust_id_input:
    try:
        cust_id = int(float(cust_id_input))
        result = df[df["customer_id"] == cust_id]
        if result.empty:
            st.warning(f"No customer found with ID {cust_id}.")
        else:
            st.dataframe(result)
    except ValueError:
        st.warning("Please enter a valid numeric customer ID.")
