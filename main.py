import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Toshakhana Dashboard",
    page_icon="🇵🇰",
    layout="wide"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

    /* Main background */
    .stApp {
        background-color: #f5f7fa;
    }

    /* Main title */
    .main-title {
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #6b7280;
        font-size: 16px;
        margin-bottom: 25px;
    }

    /* KPI cards */
    .metric-card {
        background-color: white;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        text-align: center;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.04);
    }

    .metric-title {
        color: #6b7280;
        font-size: 14px;
        margin-bottom: 5px;
    }

    .metric-value {
        font-size: 25px;
        font-weight: 700;
    }

    /* Section headings */
    .section-title {
        font-size: 20px;
        font-weight: 600;
        margin-top: 15px;
        margin-bottom: 10px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# LOAD DATA
# =========================================================

df = pd.read_csv("Refined_TK_data ver 2.csv")

# Convert date
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Create Year
df["Year"] = df["Date"].dt.year


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🇵🇰 Pakistan Toshakhana Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Interactive overview of Toshakhana gift records'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR FILTERS
# =========================================================

st.sidebar.title("🔎 Filters")

st.sidebar.markdown("Filter the dashboard data.")

# Category filter
categories = sorted(
    df["Item Category"].dropna().unique().tolist()
)

selected_category = st.sidebar.selectbox(
    "Item Category",
    ["All Categories"] + categories
)

# Year filter
years = sorted(
    df["Year"].dropna().astype(int).unique().tolist()
)

selected_year = st.sidebar.selectbox(
    "Year",
    ["All Years"] + years
)


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_df = df.copy()

if selected_category != "All Categories":
    filtered_df = filtered_df[
        filtered_df["Item Category"] == selected_category
    ]

if selected_year != "All Years":
    filtered_df = filtered_df[
        filtered_df["Year"] == selected_year
    ]


# =========================================================
# KPI CALCULATIONS
# =========================================================

total_gifts = len(filtered_df)

total_categories = filtered_df["Item Category"].nunique()

total_recipients = filtered_df["Name of Recipient"].nunique()

total_value = filtered_df["Assessed Value"].sum()


# =========================================================
# KPI CARDS
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Gifts</div>
            <div class="metric-value">{total_gifts:,}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Item Categories</div>
            <div class="metric-value">{total_categories:,}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Recipients</div>
            <div class="metric-value">{total_recipients:,}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Assessed Value</div>
            <div class="metric-value">{total_value:,.0f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# CHARTS
# =========================================================

chart_col1, chart_col2 = st.columns(2)


# ---------------------------------------------------------
# Gifts by Year
# ---------------------------------------------------------

with chart_col1:

    st.markdown(
        '<div class="section-title">📈 Gifts by Year</div>',
        unsafe_allow_html=True
    )

    year_data = (
        filtered_df["Year"]
        .dropna()
        .value_counts()
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(7, 4))

    ax.plot(
        year_data.index,
        year_data.values,
        marker="o"
    )

    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Gifts")

    ax.grid(alpha=0.2)

    plt.tight_layout()

    st.pyplot(fig, use_container_width=True)


# ---------------------------------------------------------
# Top Item Categories
# ---------------------------------------------------------

with chart_col2:

    st.markdown(
        '<div class="section-title">🎁 Top Item Categories</div>',
        unsafe_allow_html=True
    )

    category_data = (
        filtered_df["Item Category"]
        .dropna()
        .value_counts()
        .head(8)
        .sort_values()
    )

    fig, ax = plt.subplots(figsize=(7, 4))

    ax.barh(
        category_data.index,
        category_data.values
    )

    ax.set_xlabel("Number of Gifts")

    plt.tight_layout()

    st.pyplot(fig, use_container_width=True)


# =========================================================
# DATA TABLE
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    '<div class="section-title">📋 Gift Records</div>',
    unsafe_allow_html=True
)

display_columns = [
    "Detail of Gifts",
    "Item Category",
    "Name of Recipient",
    "Affiliation",
    "Assessed Value",
    "Retention Cost",
    "Retained",
    "Year"
]

available_columns = [
    col for col in display_columns
    if col in filtered_df.columns
]

st.dataframe(
    filtered_df[available_columns],
    use_container_width=True,
    height=300
)


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div style="
        text-align:center;
        color:#6b7280;
        padding:15px;
        font-size:13px;
    ">
        Pakistan Toshakhana Data Analysis Project
    </div>
    """,
    unsafe_allow_html=True
)