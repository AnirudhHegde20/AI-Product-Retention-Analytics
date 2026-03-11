import psycopg2
import pandas as pd
from lifelines import KaplanMeierFitter
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ── 1. Load survival inputs from marts ───────────────────────────────────────
conn = psycopg2.connect(
    dbname="ai_saas_analytics",
    user="anirudhhegde",
    host="localhost",
    port=5432
)

df = pd.read_sql("""
    SELECT
        user_id,
        survival_days,
        churned,
        user_segment,
        total_reviews,
        avg_engagement_score
    FROM analytics_marts.fct_survival_inputs
    WHERE survival_days >= 0
    AND total_reviews >= 2
""", conn)

conn.close()
print(f"✅ Loaded {len(df):,} users for survival analysis")
print(f"   Churned: {df['churned'].sum():,} ({df['churned'].mean()*100:.1f}%)")
print(f"   Avg survival: {df['survival_days'].mean():.0f} days\n")

# ── 2. Overall Kaplan-Meier Survival Curve ────────────────────────────────────
kmf = KaplanMeierFitter()
kmf.fit(
    durations  = df['survival_days'],
    event_observed = df['churned'],
    label      = "All Users"
)

plt.figure(figsize=(12, 6))
kmf.plot_survival_function(ci_show=True)

plt.title("User Survival Curve — How Long Do Users Stay Active?", fontsize=14)
plt.xlabel("Days Since First Review")
plt.ylabel("Survival Probability")
plt.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='50% survival')
plt.legend()
plt.tight_layout()
plt.savefig("analysis/survival_curve_overall.png", dpi=150)
plt.close()
print("✅ Saved: survival_curve_overall.png")

# ── 3. Survival by User Segment ───────────────────────────────────────────────
plt.figure(figsize=(12, 6))

segments = ['Power User', 'Regular User', 'Casual User', 'New User']
colors   = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']

for segment, color in zip(segments, colors):
    mask = df['user_segment'] == segment
    if mask.sum() < 10:
        continue
    kmf_seg = KaplanMeierFitter()
    kmf_seg.fit(
        durations      = df[mask]['survival_days'],
        event_observed = df[mask]['churned'],
        label          = f"{segment} (n={mask.sum():,})"
    )
    kmf_seg.plot_survival_function(ci_show=False, color=color)

plt.title("Survival by User Segment — Do Power Users Survive Longer?", fontsize=14)
plt.xlabel("Days Since First Review")
plt.ylabel("Survival Probability")
plt.axhline(y=0.5, color='black', linestyle='--', alpha=0.3, label='50% survival')
plt.legend()
plt.tight_layout()
plt.savefig("analysis/survival_curve_by_segment.png", dpi=150)
plt.close()
print("✅ Saved: survival_curve_by_segment.png")

# ── 4. Print Key Insights ─────────────────────────────────────────────────────
print("\n📊 KEY SURVIVAL INSIGHTS")
print("=" * 40)

# Median survival time
median = kmf.median_survival_time_
print(f"Median survival time: {median:.0f} days ({median/30:.1f} months)")

# Survival at key milestones
for days, label in [(30, '1 month'), (90, '3 months'), (180, '6 months'), (365, '1 year')]:
    prob = kmf.predict(days)
    print(f"Survival at {label}: {prob*100:.1f}%")

print("\n👥 SURVIVAL BY SEGMENT")
print("=" * 40)
for segment in segments:
    mask = df['user_segment'] == segment
    if mask.sum() < 10:
        continue
    kmf_seg = KaplanMeierFitter()
    kmf_seg.fit(df[mask]['survival_days'], df[mask]['churned'])
    median_seg = kmf_seg.median_survival_time_
    print(f"{segment}: median survival = {median_seg:.0f} days ({median_seg/30:.1f} months)")