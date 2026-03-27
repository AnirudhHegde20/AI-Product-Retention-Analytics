import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from lifelines import KaplanMeierFitter

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI SaaS Retention Analytics",
    page_icon="📊",
    layout="wide"
)

# ── Database Connection ───────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=st.secrets["SUPABASE_HOST"],
        dbname=st.secrets["SUPABASE_DB"],
        user=st.secrets["SUPABASE_USER"],
        password=st.secrets["SUPABASE_PASSWORD"],
        port=int(st.secrets["SUPABASE_PORT"]),
        sslmode="require"
    )

@st.cache_data
def load_data(query):
    conn = get_connection()
    return pd.read_sql(query, conn)

# ── Sidebar Navigation ────────────────────────────────────────────────────────
st.sidebar.title("📊 Analytics Platform")
st.sidebar.markdown("AI SaaS Retention & Competitive Intelligence")

page = st.sidebar.radio(
    "Navigate to:",
    ["🏠 Overview", "📉 Retention Analysis", "📈 Survival Analysis", "🔍 Competitive Intelligence"]
)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1: OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
if page == "🏠 Overview":
    st.title("AI SaaS Retention & Competitive Intelligence")
    st.markdown("#### End-to-end analytics platform built with PostgreSQL, dbt, and Python")
    st.divider()

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)

    survival_df = load_data("SELECT * FROM analytics_marts.fct_survival_inputs")
    retention_df = load_data("SELECT * FROM analytics_marts.fct_retention_cohorts")
    launch_df = load_data("SELECT * FROM analytics_marts.fct_launch_performance")

    with col1:
        st.metric("Total Users Analyzed", f"{len(survival_df):,}")
    with col2:
        churn_rate = survival_df['churned'].mean() * 100
        st.metric("Overall Churn Rate", f"{churn_rate:.1f}%")
    with col3:
        avg_survival = survival_df['survival_days'].mean()
        st.metric("Avg Survival (days)", f"{avg_survival:.0f}")
    with col4:
        st.metric("AI Tools Tracked", f"{len(launch_df):,}")

    st.divider()
    st.markdown("### 🔑 Key Findings")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**70% of users** churn within their first month of activity")
    with col2:
        st.success("**Power Users** survive 3x longer than New Users on average")
    with col3:
        st.warning("**Total reviews** is the #1 predictor of long-term retention")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2: RETENTION ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📉 Retention Analysis":
    st.title("📉 Cohort Retention Analysis")
    st.markdown("How many users return each month after their first activity?")
    st.divider()

    df = load_data("""
        SELECT
            cohort_month::date,
            months_since_joining,
            retention_rate
        FROM analytics_marts.fct_retention_cohorts
        WHERE months_since_joining <= 12
        AND cohort_month >= '2015-01-01'
        AND cohort_month < '2020-01-01'
    """)

    # Cohort selector
    cohorts = sorted(df['cohort_month'].unique())
    selected = st.multiselect(
        "Select cohorts to compare:",
        options=[str(c) for c in cohorts],
        default=[str(cohorts[0]), str(cohorts[6])] if len(cohorts) > 6 else [str(cohorts[0])]
    )

    if selected:
        filtered = df[df['cohort_month'].astype(str).isin(selected)]
        fig = px.line(
            filtered,
            x='months_since_joining',
            y='retention_rate',
            color='cohort_month',
            title='Monthly Retention Rate by Cohort',
            labels={
                'months_since_joining': 'Months Since Joining',
                'retention_rate': 'Retention Rate (%)',
                'cohort_month': 'Cohort'
            }
        )
        fig.add_hline(y=20, line_dash="dash", line_color="red",
                      annotation_text="20% threshold")
        st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    st.divider()
    st.markdown("### Month-1 Retention by Cohort Year")
    month1 = load_data("""
        SELECT
            EXTRACT(YEAR FROM cohort_month)::int AS cohort_year,
            ROUND(AVG(retention_rate), 1) AS avg_month1_retention
        FROM analytics_marts.fct_retention_cohorts
        WHERE months_since_joining = 1
        GROUP BY 1
        ORDER BY 1
    """)
    fig2 = px.bar(
        month1,
        x='cohort_year',
        y='avg_month1_retention',
        title='Average Month-1 Retention Rate by Year',
        labels={'cohort_year': 'Year', 'avg_month1_retention': 'Avg Retention (%)'},
        color='avg_month1_retention',
        color_continuous_scale='RdYlGn'
    )
    st.plotly_chart(fig2, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3: SURVIVAL ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📈 Survival Analysis":
    st.title("📈 Survival Analysis")
    st.markdown("How long do users stay active before churning?")
    st.divider()

    df = load_data("""
        SELECT survival_days, churned, user_segment
        FROM analytics_marts.fct_survival_inputs
        WHERE survival_days >= 0
        AND total_reviews >= 2
    """)

    # Overall survival curve
    kmf = KaplanMeierFitter()
    kmf.fit(df['survival_days'], df['churned'])

    timeline = kmf.survival_function_.index.tolist()
    survival  = kmf.survival_function_['KM_estimate'].tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timeline, y=[s * 100 for s in survival],
        mode='lines', name='All Users',
        line=dict(color='#3498db', width=2)
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="red",
                  annotation_text="50% survival")
    fig.update_layout(
        title='Overall User Survival Curve',
        xaxis_title='Days Since First Activity',
        yaxis_title='Survival Probability (%)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Survival by segment
    st.divider()
    st.markdown("### Survival by User Segment")

    segments = ['Power User', 'Regular User', 'Casual User', 'New User']
    colors   = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
    fig2 = go.Figure()

    col1, col2 = st.columns(2)
    segment_stats = []

    for segment, color in zip(segments, colors):
        mask = df['user_segment'] == segment
        if mask.sum() < 10:
            continue
        kmf_seg = KaplanMeierFitter()
        kmf_seg.fit(df[mask]['survival_days'], df[mask]['churned'])
        t = kmf_seg.survival_function_.index.tolist()
        s = kmf_seg.survival_function_['KM_estimate'].tolist()
        fig2.add_trace(go.Scatter(
            x=t, y=[v * 100 for v in s],
            mode='lines', name=segment,
            line=dict(color=color, width=2)
        ))
        segment_stats.append({
            'Segment': segment,
            'Users': f"{mask.sum():,}",
            'Median Survival (days)': f"{kmf_seg.median_survival_time_:.0f}"
        })

    fig2.update_layout(
        title='Survival Curves by User Segment',
        xaxis_title='Days Since First Activity',
        yaxis_title='Survival Probability (%)'
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(pd.DataFrame(segment_stats), use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4: COMPETITIVE INTELLIGENCE
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Competitive Intelligence":
    st.title("🔍 Competitive Intelligence")
    st.markdown("How are AI tools performing on Product Hunt?")
    st.divider()

    df = load_data("SELECT * FROM analytics_marts.fct_category_performance")
    launch_df = load_data("""
        SELECT name, upvotes, category, traction_tier,
               success_score, days_since_launch, launch_month
        FROM analytics_marts.fct_launch_performance
        ORDER BY upvotes DESC
    """)

    # Category performance
    fig = px.bar(
        df.sort_values('avg_success_score', ascending=True),
        x='avg_success_score',
        y='category',
        orientation='h',
        title='Average Success Score by Category',
        labels={'avg_success_score': 'Avg Success Score', 'category': 'Category'},
        color='avg_success_score',
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig2 = px.scatter(
            launch_df,
            x='days_since_launch',
            y='upvotes',
            color='traction_tier',
            hover_name='name',
            title='Upvotes vs Days Since Launch',
            labels={
                'days_since_launch': 'Days Since Launch',
                'upvotes': 'Upvotes',
                'traction_tier': 'Traction Tier'
            }
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        fig3 = px.pie(
            df,
            values='total_launches',
            names='category',
            title='Launch Distribution by Category'
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()
    st.markdown("### 🏆 Top Performing Launches")
    st.dataframe(
        launch_df[['name', 'upvotes', 'category', 'traction_tier', 'success_score']].head(10),
        use_container_width=True
    )