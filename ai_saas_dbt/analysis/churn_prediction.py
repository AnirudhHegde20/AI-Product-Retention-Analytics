import psycopg2
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ── 1. Load data from marts ───────────────────────────────────────────────────
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
        total_reviews,
        avg_stars,
        avg_engagement_score,
        user_segment,
        -- Simulate churn: low engagement users = churned
        CASE 
            WHEN survival_days < 180 THEN 1  -- churned (survived less than 6 months)
            ELSE 0                           -- retained
        END AS churned
    FROM analytics_marts.fct_survival_inputs
    WHERE survival_days >= 0
    AND total_reviews >= 2
""", conn)
conn.close()
print(f"✅ Loaded {len(df):,} users for churn prediction\n")

# ── 2. Feature Engineering ────────────────────────────────────────────────────
# Encode user_segment as a number (ML models need numbers, not text)
le = LabelEncoder()
df['user_segment_encoded'] = le.fit_transform(df['user_segment'])

# Define features (X) and target (y)
FEATURES = [
    'total_reviews',
    'avg_stars',
    'avg_engagement_score',
    'user_segment_encoded'
]

X = df[FEATURES]
y = df['churned'].astype(int)

print(f"Features: {FEATURES}")
print(f"Target distribution: {y.value_counts().to_dict()}\n")

# ── 3. Train/Test Split ───────────────────────────────────────────────────────
# 80% training, 20% testing — standard split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"Training set: {len(X_train):,} users")
print(f"Testing set:  {len(X_test):,} users\n")

# ── 4. Train XGBoost Model ────────────────────────────────────────────────────
model = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    random_state=42,
    eval_metric='logloss'
)
model.fit(X_train, y_train)
print("✅ Model trained\n")

# ── 5. Evaluate Model ─────────────────────────────────────────────────────────
y_pred      = model.predict(X_test)
y_pred_prob = model.predict_proba(X_test)[:, 1]

print("📊 MODEL PERFORMANCE")
print("=" * 40)
print(classification_report(y_test, y_pred))
print(f"AUC-ROC Score: {roc_auc_score(y_test, y_pred_prob):.4f}")

# ── 6. Feature Importance Chart ───────────────────────────────────────────────
importance_df = pd.DataFrame({
    'feature':   FEATURES,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=True)

plt.figure(figsize=(10, 6))
plt.barh(importance_df['feature'], importance_df['importance'], color='#3498db')
plt.title('XGBoost Feature Importance — What Predicts Churn?', fontsize=14)
plt.xlabel('Importance Score')
plt.tight_layout()
plt.savefig('analysis/feature_importance.png', dpi=150)
plt.close()
print("\n✅ Saved: feature_importance.png")

# ── 7. Business Insight ───────────────────────────────────────────────────────
print("\n💡 BUSINESS INSIGHTS")
print("=" * 40)
top_feature = importance_df.iloc[-1]['feature']
print(f"Top predictor of churn: {top_feature}")
print(f"Users with 2+ reviews have avg survival: {df['survival_days'].mean():.0f} days")
print(f"Power Users avg survival: {df[df['user_segment']=='Power User']['survival_days'].mean():.0f} days")
print(f"New Users avg survival:   {df[df['user_segment']=='New User']['survival_days'].mean():.0f} days")