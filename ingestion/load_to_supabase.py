import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# ── 1. Connect to local PostgreSQL ────────────────────────────────────────────
local_conn = psycopg2.connect(
    dbname="ai_saas_analytics",
    user="anirudhhegde",
    host="localhost",
    port=5432
)
local_cur = local_conn.cursor()

# ── 2. Connect to Supabase ────────────────────────────────────────────────────
supabase_conn = psycopg2.connect(
    host=os.getenv("SUPABASE_HOST"),
    dbname=os.getenv("SUPABASE_DB"),
    user=os.getenv("SUPABASE_USER"),
    password=os.getenv("SUPABASE_PASSWORD"),
    port=os.getenv("SUPABASE_PORT"),
    sslmode="require"
)
supabase_cur = supabase_conn.cursor()

CHUNK_SIZE = 5000

def migrate_table(table, insert_sql, select_sql):
    print(f"\nMigrating {table}...")
    local_cur.execute(select_sql)
    rows = local_cur.fetchmany(CHUNK_SIZE)
    total = 0
    while rows:
        supabase_cur.executemany(insert_sql, rows)
        supabase_conn.commit()
        total += len(rows)
        print(f"  {total:,} rows migrated")
        rows = local_cur.fetchmany(CHUNK_SIZE)
    print(f"✅ {table} done — {total:,} rows")

# ── 3. Migrate Product Hunt launches ─────────────────────────────────────────
migrate_table(
    "product_hunt_launches",
    """INSERT INTO raw.product_hunt_launches
       (name, tagline, upvotes, category, pricing_type, launch_date, product_url)
       VALUES (%s, %s, %s, %s, %s, %s, %s)
       ON CONFLICT (product_url) DO NOTHING""",
    "SELECT name, tagline, upvotes, category, pricing_type, launch_date, product_url FROM raw.product_hunt_launches"
)

# ── 4. Migrate Yelp reviews (100k subset for cloud) ──────────────────────────
migrate_table(
    "yelp_reviews",
    """INSERT INTO raw.yelp_reviews
       (review_id, user_id, business_id, stars, review_date, useful, funny, cool)
       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
       ON CONFLICT (review_id) DO NOTHING""",
    "SELECT review_id, user_id, business_id, stars, review_date, useful, funny, cool FROM raw.yelp_reviews LIMIT 100000"
)

# ── 5. Migrate Yelp users (100k subset for cloud) ────────────────────────────
migrate_table(
    "yelp_users",
    """INSERT INTO raw.yelp_users
       (user_id, name, review_count, yelping_since, fans, average_stars)
       VALUES (%s, %s, %s, %s, %s, %s)
       ON CONFLICT (user_id) DO NOTHING""",
    "SELECT user_id, name, review_count, yelping_since, fans, average_stars FROM raw.yelp_users LIMIT 100000"
)

# ── 6. Cleanup ────────────────────────────────────────────────────────────────
local_cur.close()
local_conn.close()
supabase_cur.close()
supabase_conn.close()
print("\n🎉 Migration to Supabase complete!")