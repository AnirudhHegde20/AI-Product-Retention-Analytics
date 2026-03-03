import json
import psycopg2
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
REVIEWS_FILE = "/Users/anirudhhegde/Desktop/Northeastern University/Let's Do it/Project/yelp_academic_dataset_review.json"
USERS_FILE   = "/Users/anirudhhegde/Desktop/Northeastern University/Let's Do it/Project/yelp_academic_dataset_user.json"

DB_CONFIG = {
    "dbname": "ai_saas_analytics",
    "user":   "anirudhhegde",
    "host":   "localhost",
    "port":   5432
}

CHUNK_SIZE  = 10_000   # rows per batch insert
MAX_ROWS    = 500_000  # load only first 500k rows (enough for big data demo)

# ── Connect to PostgreSQL ──────────────────────────────────────────────────────
conn = psycopg2.connect(**DB_CONFIG)
cur  = conn.cursor()

# ── Helper: batch insert ───────────────────────────────────────────────────────
def bulk_insert(query, batch):
    """Insert a batch of rows, skip duplicates silently."""
    try:
        cur.executemany(query, batch)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"  ⚠️  Batch error: {e}")

# ── 1. Load Reviews ────────────────────────────────────────────────────────────
print("Loading reviews...")
INSERT_REVIEW = """
    INSERT INTO raw.yelp_reviews
        (review_id, user_id, business_id, stars, review_date, useful, funny, cool)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (review_id) DO NOTHING
"""

batch   = []
total   = 0

with open(REVIEWS_FILE, "r") as f:
    for line in f:
        if total >= MAX_ROWS:
            break

        row = json.loads(line)
        batch.append((
            row["review_id"],
            row["user_id"],
            row["business_id"],
            float(row["stars"]),
            row["date"][:10],      # YYYY-MM-DD only
            int(row.get("useful", 0)),
            int(row.get("funny",  0)),
            int(row.get("cool",   0)),
        ))

        if len(batch) >= CHUNK_SIZE:
            bulk_insert(INSERT_REVIEW, batch)
            total += len(batch)
            batch  = []
            print(f"  ✅ Reviews loaded: {total:,}")

# Insert remaining rows
if batch:
    bulk_insert(INSERT_REVIEW, batch)
    total += len(batch)

print(f"✅ Reviews done — {total:,} rows loaded.\n")

# ── 2. Load Users ──────────────────────────────────────────────────────────────
print("Loading users...")
INSERT_USER = """
    INSERT INTO raw.yelp_users
        (user_id, name, review_count, yelping_since, fans, average_stars)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (user_id) DO NOTHING
"""

batch = []
total = 0

with open(USERS_FILE, "r") as f:
    for line in f:
        if total >= MAX_ROWS:
            break

        row = json.loads(line)
        batch.append((
            row["user_id"],
            row.get("name"),
            int(row.get("review_count", 0)),
            row.get("yelping_since", "2004-01-01")[:10],
            int(row.get("fans", 0)),
            float(row.get("average_stars", 0)),
        ))

        if len(batch) >= CHUNK_SIZE:
            bulk_insert(INSERT_USER, batch)
            total += len(batch)
            batch  = []
            print(f"  ✅ Users loaded: {total:,}")

# Insert remaining rows
if batch:
    bulk_insert(INSERT_USER, batch)
    total += len(batch)

print(f"✅ Users done — {total:,} rows loaded.\n")

# ── Cleanup ────────────────────────────────────────────────────────────────────
cur.close()
conn.close()
print("🎉 Yelp ingestion complete!")