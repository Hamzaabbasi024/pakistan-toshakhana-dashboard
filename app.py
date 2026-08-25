"""
=====================================================================================
  PAKISTAN TOSHAKHANA — INTELLIGENCE DASHBOARD
  A single-screen, no-scroll Streamlit dashboard built on top of the EDA performed
  in `pakistan-toshakhana.ipynb`.

  Run with:   streamlit run app.py
=====================================================================================
"""

import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Toshakhana Intelligence Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "Light"

# ─────────────────────────────────────────────────────────────────────────────────
#  DATA LOADING  (mirrors the cleaning pipeline in the notebook)
# ─────────────────────────────────────────────────────────────────────────────────
EXPECTED_COLS = [
    "Detail of Gifts", "Item Category", "Name of Recipient", "Affiliation",
    "Date", "Assessed Value", "Retention Cost", "Retained", "Remarks",
]

DEFAULT_PATHS = [
    "Refined_TK_data ver 2.csv",
    "data/Refined_TK_data ver 2.csv",
    "Refined_TK_data.csv",
    "toshakhana.csv",
    "pakistan_toshakhana.csv",
]


@st.cache_data(show_spinner=False)
def generate_demo_data(n=1200, seed=7):
    """Synthetic fallback so the dashboard is explorable even with no file yet."""
    rng = np.random.default_rng(seed)
    categories = ["Watch", "Decoration Pieces", "Carpet", "Pen", "Crockery",
                  "Jewellery/Accessories", "Phone", "Cigar/Cigarettes", "Weapons",
                  "Clothes", "Food", "Bags", "Tech", "Unknown"]
    affiliations = ["Military", "PPP Govt", "PMLN Govt", "PTI Govt", "Gen. Musharraf",
                     "Caretaker Govt", "PDM Govt", "Unknown"]
    recipients = [f"Recipient {i}" for i in range(1, 181)]
    retained = ["Yes", "No", "Auctioned", "Unknown"]
    dates = pd.date_range("2002-01-01", "2022-10-24", periods=n)
    df = pd.DataFrame({
        "Detail of Gifts": rng.choice(["Carpet", "Watch", "Silver Bowl", "Pen Set",
                                        "Decoration Piece", "Vase"], n),
        "Item Category": rng.choice(categories, n, p=None),
        "Name of Recipient": rng.choice(recipients, n),
        "Affiliation": rng.choice(affiliations, n),
        "Date": dates,
        "Assessed Value": np.round(rng.lognormal(8.5, 1.6, n), 0),
        "Retention Cost": np.round(rng.lognormal(6.5, 1.8, n) * rng.choice([0, 1], n, p=[0.35, 0.65]), 0),
        "Retained": rng.choice(retained, n, p=[0.85, 0.06, 0.06, 0.03]),
        "Remarks": "Yes",
    })
    return df


@st.cache_data(show_spinner=False)
def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [c.strip() for c in df.columns]
    df = df.drop_duplicates()

    for col in ["Item Category", "Affiliation", "Retained"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str).str.strip()
    if "Remarks" in df.columns:
        df["Remarks"] = df["Remarks"].fillna("No Remarks")
    if "Detail of Gifts" in df.columns:
        df["Detail of Gifts"] = df["Detail of Gifts"].fillna("Unknown")

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Year"] = df["Date"].dt.year

    for col in ["Assessed Value", "Retention Cost"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalize recipient whitespace (notebook shows multi-line/whitespace noise)
    if "Name of Recipient" in df.columns:
        df["Name of Recipient"] = (
            df["Name of Recipient"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        )
    if "Affiliation" in df.columns:
        df["Affiliation"] = df["Affiliation"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    # Collapse the very long tail of "Retained" free-text into clean buckets
    if "Retained" in df.columns:
        def bucket_retained(v):
            v = str(v).lower()
            if "yes" in v and "no" not in v:
                return "Yes"
            if v.strip() == "no":
                return "No"
            if "auction" in v:
                return "Auctioned"
            if "display" in v:
                return "Displayed"
            if "unknown" in v:
                return "Unknown"
            return "Other"
        df["Retained_Clean"] = df["Retained"].apply(bucket_retained)

    return df


def load_data():
    with st.sidebar:
        st.markdown("### 📁 Data Source")
        uploaded = st.file_uploader("Upload Toshakhana CSV", type=["csv"], label_visibility="collapsed")

    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        return clean_data(raw), "Uploaded file"

    for p in DEFAULT_PATHS:
        try:
            raw = pd.read_csv(p)
            return clean_data(raw), p
        except Exception:
            continue

    return clean_data(generate_demo_data()), "Demo / sample data (upload your CSV in the sidebar)"


df, source_label = load_data()

# ─────────────────────────────────────────────────────────────────────────────────
#  THEME  (light <-> dark, injected CSS + plotly template)
# ─────────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎨 Appearance")
    theme_choice = st.toggle("🌙 Dark mode", value=(st.session_state.theme == "Dark"))
    st.session_state.theme = "Dark" if theme_choice else "Light"

DARK = st.session_state.theme == "Dark"

if DARK:
    BG, BG2, CARD, TEXT, SUBTEXT, BORDER = "#0e1117", "#131722", "#1a1f2e", "#eef1f8", "#9aa4bf", "#2a3146"
    ACCENT, ACCENT2, ACCENT3 = "#7c9cff", "#4fd6c0", "#ff8ba0"
    PLOTLY_TEMPLATE = "plotly_dark"
    GRID = "#242b3d"
else:
    BG, BG2, CARD, TEXT, SUBTEXT, BORDER = "#f5f7fb", "#ffffff", "#ffffff", "#1a1f36", "#5c6485", "#e6e9f2"
    ACCENT, ACCENT2, ACCENT3 = "#3457d5", "#0ea394", "#d64566"
    PLOTLY_TEMPLATE = "plotly_white"
    GRID = "#eef1f8"

PALETTE = [ACCENT, ACCENT2, ACCENT3, "#f4a261", "#8e7cc3", "#57bcae", "#e0b04d", "#6d9dc5", "#c9727a", "#7fb069"]

st.markdown(f"""
<style>
    .stApp {{
        background: {BG};
        color: {TEXT};
    }}
    html, body, [class*="css"] {{
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }}
    /* kill vertical scroll on the main viewport */
    section.main > div.block-container {{
        padding-top: 0.6rem;
        padding-bottom: 0.2rem;
        padding-left: 1.4rem;
        padding-right: 1.4rem;
        max-width: 100%;
    }}
    div[data-testid="stAppViewContainer"] {{ overflow: hidden; }}
    div[data-testid="stVerticalBlock"] {{ gap: 0.5rem; }}

    /* header banner */
    .tk-header {{
        display:flex; align-items:center; justify-content:space-between;
        padding: 0.55rem 1.1rem; border-radius: 14px; margin-bottom: 0.55rem;
        background: linear-gradient(120deg, {ACCENT}22, {ACCENT2}11);
        border: 1px solid {BORDER};
    }}
    .tk-title {{ font-size: 1.35rem; font-weight: 800; color:{TEXT}; letter-spacing: -0.02em; margin:0; }}
    .tk-subtitle {{ font-size: 0.78rem; color:{SUBTEXT}; margin:0; }}
    .tk-badge {{
        font-size: 0.68rem; padding: 3px 10px; border-radius: 999px;
        background:{CARD}; border:1px solid {BORDER}; color:{SUBTEXT};
    }}

    /* KPI cards */
    .kpi-card {{
        background:{CARD}; border:1px solid {BORDER}; border-radius: 12px;
        padding: 0.55rem 0.8rem; text-align:left; height: 74px;
        display:flex; flex-direction:column; justify-content:center;
    }}
    .kpi-label {{ font-size: 0.68rem; color:{SUBTEXT}; text-transform:uppercase; letter-spacing:.04em; margin:0; }}
    .kpi-value {{ font-size: 1.28rem; font-weight:800; color:{TEXT}; margin:0; line-height:1.25; }}
    .kpi-sub {{ font-size: 0.66rem; color:{ACCENT2}; margin:0; }}

    /* tabs */
    button[data-baseweb="tab"] {{
        font-size: 0.86rem; font-weight: 600; color:{SUBTEXT};
        padding: 6px 14px !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color:{ACCENT} !important; }}
    div[data-baseweb="tab-highlight"] {{ background-color:{ACCENT} !important; }}
    div[data-baseweb="tab-border"] {{ display:none; }}

    .card {{
        background:{CARD}; border:1px solid {BORDER}; border-radius: 12px;
        padding: 0.4rem 0.65rem 0.1rem 0.65rem;
    }}
    .card-title {{ font-size: 0.78rem; font-weight:700; color:{TEXT}; margin: 2px 0 0 2px; }}

    footer, header[data-testid="stHeader"] {{ visibility:hidden; height:0; }}
    #MainMenu {{ visibility:hidden; }}
    .stDeployButton {{ display:none; }}

    ::-webkit-scrollbar {{ width:0px; height:0px; }}

    div[data-testid="stMetricValue"] {{ color:{TEXT}; }}
    section[data-testid="stSidebar"] {{ background:{BG2}; border-right:1px solid {BORDER}; }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig, height=250, legend=False, ml=6, mr=6, mt=28, mb=6):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        margin=dict(l=ml, r=mr, t=mt, b=mb),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        font=dict(size=11, color=TEXT, family="Inter, Segoe UI, sans-serif"),
        title_font=dict(size=12.5, color=TEXT),
        hoverlabel=dict(bgcolor=CARD, font_size=11, font_color=TEXT),
    )
    fig.update_xaxes(showgrid=False, color=SUBTEXT, tickfont=dict(size=10))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, color=SUBTEXT, tickfont=dict(size=10))
    return fig


def fmt_money(x):
    if pd.isna(x):
        return "—"
    if abs(x) >= 1e9:
        return f"₨{x/1e9:.2f}B"
    if abs(x) >= 1e6:
        return f"₨{x/1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"₨{x/1e3:.0f}K"
    return f"₨{x:.0f}"


# ─────────────────────────────────────────────────────────────────────────────────
#  SIDEBAR — FILTERS
# ─────────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔎 Filters")

    if "Year" in df.columns and df["Year"].notna().any():
        y_min, y_max = int(df["Year"].min()), int(df["Year"].max())
        year_range = st.slider("Year range", y_min, y_max, (y_min, y_max))
    else:
        year_range = None

    cats = sorted([c for c in df["Item Category"].dropna().unique()]) if "Item Category" in df.columns else []
    sel_cats = st.multiselect("Item category", cats, default=[])

    affs = sorted([a for a in df["Affiliation"].dropna().unique()]) if "Affiliation" in df.columns else []
    sel_affs = st.multiselect("Affiliation", affs, default=[])

    ret_opts = sorted(df["Retained_Clean"].dropna().unique()) if "Retained_Clean" in df.columns else []
    sel_ret = st.multiselect("Retention status", ret_opts, default=[])

    search_name = st.text_input("Search recipient")

    st.markdown("---")
    st.caption(f"**Source:** {source_label}")
    st.caption(f"**Rows loaded:** {len(df):,}")

# apply filters
fdf = df.copy()
if year_range:
    fdf = fdf[(fdf["Year"] >= year_range[0]) & (fdf["Year"] <= year_range[1])]
if sel_cats:
    fdf = fdf[fdf["Item Category"].isin(sel_cats)]
if sel_affs:
    fdf = fdf[fdf["Affiliation"].isin(sel_affs)]
if sel_ret:
    fdf = fdf[fdf["Retained_Clean"].isin(sel_ret)]
if search_name:
    fdf = fdf[fdf["Name of Recipient"].str.contains(search_name, case=False, na=False)]

if fdf.empty:
    st.warning("No records match the current filters — adjust filters in the sidebar.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────────
date_span = ""
if fdf["Date"].notna().any():
    date_span = f"{fdf['Date'].min().strftime('%b %Y')} – {fdf['Date'].max().strftime('%b %Y')}"

st.markdown(f"""
<div class="tk-header">
    <div>
        <p class="tk-title">🏛️ Pakistan Toshakhana — Intelligence Dashboard</p>
        <p class="tk-subtitle">Gifts received by state officials & the retention/auction trail · {date_span}</p>
    </div>
    <div class="tk-badge">{len(fdf):,} records · {st.session_state.theme} mode</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────────
#  KPI ROW
# ─────────────────────────────────────────────────────────────────────────────────
total_assessed = fdf["Assessed Value"].sum()
total_retention = fdf["Retention Cost"].sum()
avg_assessed = fdf["Assessed Value"].mean()
n_recipients = fdf["Name of Recipient"].nunique()
n_categories = fdf["Item Category"].nunique()
pct_retained = (fdf["Retained_Clean"] == "Yes").mean() * 100 if "Retained_Clean" in fdf else np.nan

k1, k2, k3, k4, k5, k6 = st.columns(6)
kpis = [
    (k1, "Total Gifts", f"{len(fdf):,}", "records"),
    (k2, "Total Assessed Value", fmt_money(total_assessed), "cumulative"),
    (k3, "Total Retention Cost", fmt_money(total_retention), "paid by recipients"),
    (k4, "Avg. Assessed Value", fmt_money(avg_assessed), "per gift"),
    (k5, "Unique Recipients", f"{n_recipients:,}", f"{n_categories} categories"),
    (k6, "% Gifts Retained", f"{pct_retained:.1f}%" if pd.notna(pct_retained) else "—", "vs auctioned/returned"),
]
for col, label, val, sub in kpis:
    col.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">{label}</p>
        <p class="kpi-value">{val}</p>
        <p class="kpi-sub">{sub}</p>
    </div>""", unsafe_allow_html=True)

st.write("")

# ─────────────────────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Overview", "📈 Trends Over Time", "🧑‍💼 Recipients", "💰 Value & Categories", "🧮 Outliers & Explorer"]
)

# ══════════════════════════════════════════ TAB 1 — OVERVIEW ══════════════════════
with tab1:
    c1, c2, c3 = st.columns([1.1, 1.1, 1])

    with c1:
        st.markdown('<div class="card"><p class="card-title">Top Gift Categories</p>', unsafe_allow_html=True)
        cat_counts = fdf["Item Category"].value_counts().head(8).sort_values()
        fig = px.bar(cat_counts, x=cat_counts.values, y=cat_counts.index, orientation="h",
                     color=cat_counts.values, color_continuous_scale=[ACCENT2, ACCENT])
        fig.update_traces(hovertemplate="%{y}: %{x} gifts<extra></extra>")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(style_fig(fig, height=252), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><p class="card-title">Gift Retention Status</p>', unsafe_allow_html=True)
        ret_counts = fdf["Retained_Clean"].value_counts()
        fig = px.pie(values=ret_counts.values, names=ret_counts.index, hole=0.58,
                     color_discrete_sequence=PALETTE)
        fig.update_traces(textinfo="percent", hovertemplate="%{label}: %{value}<extra></extra>")
        st.plotly_chart(style_fig(fig, height=252, legend=True), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="card"><p class="card-title">Top Affiliations</p>', unsafe_allow_html=True)
        aff_counts = fdf["Affiliation"].value_counts().head(6).sort_values()
        fig = px.bar(aff_counts, x=aff_counts.values, y=aff_counts.index, orientation="h",
                     color_discrete_sequence=[ACCENT3])
        fig.update_traces(hovertemplate="%{y}: %{x}<extra></extra>")
        st.plotly_chart(style_fig(fig, height=252), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    c4, c5 = st.columns([1.6, 1])
    with c4:
        st.markdown(
            '<div class="card"><p class="card-title">Gifts Recorded Per Year</p>',
            unsafe_allow_html=True
        )

        yearly = fdf.dropna(subset=["Year"]).groupby("Year").size()

        fig = go.Figure(
            go.Scatter(
                x=yearly.index,
                y=yearly.values,
                mode="lines+markers",
                line=dict(color=ACCENT, width=2.5),
                marker=dict(size=5),
                fill="tozeroy",
                fillcolor="rgba(124, 156, 255, 0.13)"
            )
        )

        fig.update_traces(
            hovertemplate="Year %{x}: %{y} gifts<extra></extra>"
        )

        st.plotly_chart(
            style_fig(fig, height=200),
            use_container_width=True,
            config={"displayModeBar": False}
        )

        st.markdown('</div>', unsafe_allow_html=True)

    with c5:
        st.markdown('<div class="card"><p class="card-title">Assessed vs Retention Cost</p>', unsafe_allow_html=True)
        corr = fdf[["Assessed Value", "Retention Cost"]].corr()
        fig = px.imshow(corr, text_auto=".2f", color_continuous_scale=[BG2, ACCENT],
                         zmin=-1, zmax=1)
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(style_fig(fig, height=200), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════ TAB 2 — TRENDS ════════════════════════
with tab2:
    yearly_gifts = fdf.dropna(subset=["Year"]).groupby("Year").size()
    yearly_avg = fdf.dropna(subset=["Year"]).groupby("Year")["Assessed Value"].mean()
    yearly_total = fdf.dropna(subset=["Year"]).groupby("Year")["Assessed Value"].sum()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card"><p class="card-title">Number of Gifts by Year</p>', unsafe_allow_html=True)
        fig = go.Figure(go.Scatter(x=yearly_gifts.index, y=yearly_gifts.values, mode="lines+markers",
                                    line=dict(color=ACCENT, width=2.5), marker=dict(size=6)))
        fig.update_traces(hovertemplate="Year %{x}: %{y} gifts<extra></extra>")
        st.plotly_chart(style_fig(fig, height=232), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><p class="card-title">Average Assessed Value by Year</p>', unsafe_allow_html=True)
        fig = go.Figure(go.Scatter(x=yearly_avg.index, y=yearly_avg.values, mode="lines+markers",
                                    line=dict(color=ACCENT2, width=2.5), marker=dict(size=6)))
        fig.update_traces(hovertemplate="Year %{x}: ₨%{y:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, height=232), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    c3, c4 = st.columns([1.6, 1])
    with c3:
        st.markdown('<div class="card"><p class="card-title">Total Assessed Value by Year</p>', unsafe_allow_html=True)
        fig = px.bar(x=yearly_total.index.astype(str), y=yearly_total.values,
                     color=yearly_total.values, color_continuous_scale=[ACCENT2, ACCENT3])
        fig.update_coloraxes(showscale=False)
        fig.update_traces(hovertemplate="%{x}: ₨%{y:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, height=220), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="card"><p class="card-title">Peak Years</p>', unsafe_allow_html=True)
        if len(yearly_gifts):
            py, pg = yearly_gifts.idxmax(), yearly_gifts.max()
            vy, vv = yearly_total.idxmax(), yearly_total.max()
            st.markdown(f"""
            <div style="padding:6px 4px;">
                <p style="font-size:0.72rem;color:{SUBTEXT};margin:2px 0;">Most gifts recorded</p>
                <p style="font-size:1.05rem;font-weight:800;color:{TEXT};margin:0 0 8px 0;">{int(py)} · {int(pg)} gifts</p>
                <p style="font-size:0.72rem;color:{SUBTEXT};margin:2px 0;">Highest total assessed value</p>
                <p style="font-size:1.05rem;font-weight:800;color:{TEXT};margin:0;">{int(vy)} · {fmt_money(vv)}</p>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════ TAB 3 — RECIPIENTS ════════════════════
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card"><p class="card-title">Top 10 Recipients by Number of Gifts</p>', unsafe_allow_html=True)
        top_r = fdf["Name of Recipient"].value_counts().head(10).sort_values()
        fig = px.bar(top_r, x=top_r.values, y=top_r.index, orientation="h",
                     color_discrete_sequence=[ACCENT])
        fig.update_traces(hovertemplate="%{y}: %{x} gifts<extra></extra>")
        st.plotly_chart(style_fig(fig, height=290), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><p class="card-title">Top 10 Recipients by Total Assessed Value</p>', unsafe_allow_html=True)
        top_v = fdf.groupby("Name of Recipient")["Assessed Value"].sum().sort_values(ascending=False).head(10).sort_values()
        fig = px.bar(top_v, x=top_v.values, y=top_v.index, orientation="h",
                     color_discrete_sequence=[ACCENT3])
        fig.update_traces(hovertemplate="%{y}: ₨%{x:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, height=290), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><p class="card-title">Recipient Summary Table</p>', unsafe_allow_html=True)
    recipient_summary = fdf.groupby("Name of Recipient").agg(
        Gifts=("Name of Recipient", "size"),
        Total_Assessed_Value=("Assessed Value", "sum"),
        Avg_Assessed_Value=("Assessed Value", "mean"),
    ).sort_values("Gifts", ascending=False).head(50).reset_index()
    st.dataframe(recipient_summary, use_container_width=True, height=150, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════ TAB 4 — VALUE & CATEGORIES ════════════
with tab4:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><p class="card-title">Top Categories by Total Value</p>', unsafe_allow_html=True)
        cat_val = fdf.groupby("Item Category")["Assessed Value"].sum().sort_values(ascending=False).head(8).sort_values()
        fig = px.bar(cat_val, x=cat_val.values, y=cat_val.index, orientation="h",
                     color_discrete_sequence=[ACCENT2])
        fig.update_traces(hovertemplate="%{y}: ₨%{x:,.0f}<extra></extra>")
        st.plotly_chart(style_fig(fig, height=250), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><p class="card-title">Assessed Value Distribution</p>', unsafe_allow_html=True)
        clipped = fdf["Assessed Value"].dropna()
        clipped = clipped[clipped <= clipped.quantile(0.95)]
        fig = px.histogram(clipped, nbins=35, color_discrete_sequence=[ACCENT])
        fig.update_traces(hovertemplate="₨%{x:,.0f}: %{y} gifts<extra></extra>")
        st.plotly_chart(style_fig(fig, height=250), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="card"><p class="card-title">Value Spread (Box Plot, 95th pct clip)</p>', unsafe_allow_html=True)
        av = fdf["Assessed Value"].dropna(); av = av[av <= av.quantile(0.95)]
        rc = fdf["Retention Cost"].dropna(); rc = rc[rc <= rc.quantile(0.95)]
        fig = go.Figure()
        fig.add_trace(go.Box(x=av, name="Assessed", marker_color=ACCENT, boxmean=True))
        fig.add_trace(go.Box(x=rc, name="Retention", marker_color=ACCENT3, boxmean=True))
        st.plotly_chart(style_fig(fig, height=250, legend=True), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><p class="card-title">Category × Retention Status (share of gifts)</p>', unsafe_allow_html=True)
    top_cats_list = fdf["Item Category"].value_counts().head(8).index
    heat_src = fdf[fdf["Item Category"].isin(top_cats_list)]
    heat = pd.crosstab(heat_src["Item Category"], heat_src["Retained_Clean"], normalize="index") * 100
    fig = px.imshow(heat.round(1), text_auto=True, color_continuous_scale=[BG2, ACCENT, ACCENT3], aspect="auto")
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(style_fig(fig, height=180), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════ TAB 5 — OUTLIERS & EXPLORER ═══════════
with tab5:
    q1, q3 = fdf["Assessed Value"].quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = fdf[(fdf["Assessed Value"] < lo) | (fdf["Assessed Value"] > hi)]

    c1, c2 = st.columns([1, 2.2])
    with c1:
        st.markdown('<div class="card"><p class="card-title">Outlier Summary (IQR method)</p>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="padding:4px 4px;">
            <p style="font-size:0.72rem;color:{SUBTEXT};margin:3px 0;">Outliers detected</p>
            <p style="font-size:1.3rem;font-weight:800;color:{TEXT};margin:0 0 8px 0;">{len(outliers):,} <span style="font-size:0.8rem;color:{SUBTEXT};font-weight:500;">({len(outliers)/max(len(fdf),1)*100:.1f}%)</span></p>
            <p style="font-size:0.72rem;color:{SUBTEXT};margin:3px 0;">Normal upper bound</p>
            <p style="font-size:1rem;font-weight:700;color:{TEXT};margin:0 0 8px 0;">{fmt_money(hi)}</p>
            <p style="font-size:0.72rem;color:{SUBTEXT};margin:3px 0;">Highest single gift value</p>
            <p style="font-size:1rem;font-weight:700;color:{ACCENT3};margin:0;">{fmt_money(fdf['Assessed Value'].max())}</p>
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><p class="card-title">Top 10 Highest-Valued Gifts</p>', unsafe_allow_html=True)
        top_gifts = fdf.sort_values("Assessed Value", ascending=False).head(10)[
            ["Name of Recipient", "Detail of Gifts", "Item Category", "Assessed Value", "Retention Cost"]
        ].reset_index(drop=True)
        top_gifts["Assessed Value"] = top_gifts["Assessed Value"].apply(fmt_money)
        top_gifts["Retention Cost"] = top_gifts["Retention Cost"].apply(fmt_money)
        st.dataframe(top_gifts, use_container_width=True, height=150, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><p class="card-title">Filtered Data Explorer</p>', unsafe_allow_html=True)
    show_cols = [c for c in ["Name of Recipient", "Detail of Gifts", "Item Category", "Affiliation",
                              "Date", "Assessed Value", "Retention Cost", "Retained_Clean"] if c in fdf.columns]
    st.dataframe(fdf[show_cols].sort_values("Date", ascending=False), use_container_width=True, height=155, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)