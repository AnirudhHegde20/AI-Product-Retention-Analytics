import os
import psycopg2
import requests
from dotenv import load_dotenv

# ── 1. Load credentials from .env ────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("PRODUCT_HUNT_TOKEN")

# ── 2. Connect to PostgreSQL ──────────────────────────────────────────────────
conn = psycopg2.connect(
    dbname="ai_saas_analytics",
    user="anirudhhegde",
    host="localhost",
    port=5432
)
cur = conn.cursor()

# ── 3. Define GraphQL query ───────────────────────────────────────────────────
# Product Hunt uses GraphQL — we ask for exactly the fields we want
QUERY = """
{
  posts(first: 50, order: VOTES) {
    edges {
      node {
        name
        tagline
        votesCount
        topics {
          edges {
            node {
              name
            }
          }
        }
        thumbnail {
          type
        }
        createdAt
        website
      }
    }
  }
}
"""

# ── 4. Call the API ───────────────────────────────────────────────────────────
headers = {"Authorization": f"Bearer {TOKEN}"}
response = requests.post(
    "https://api.producthunt.com/v2/api/graphql",
    json={"query": QUERY},
    headers=headers
)
data = response.json()

# ── 5. Parse and insert rows ──────────────────────────────────────────────────
posts = data["data"]["posts"]["edges"]
inserted = 0
skipped  = 0

for edge in posts:
    node = edge["node"]

    name         = node.get("name")
    tagline      = node.get("tagline")
    upvotes      = node.get("votesCount")
    launch_date  = node.get("createdAt", "")[:10]   # keep only YYYY-MM-DD
    product_url  = node.get("website") or f"https://www.producthunt.com/posts/{name}"

    # Extract first topic as category
    topics       = node.get("topics", {}).get("edges", [])
    category     = topics[0]["node"]["name"] if topics else None

    # Pricing type from thumbnail type (rough proxy)
    thumb_type   = node.get("thumbnail", {}).get("type", "")
    pricing_type = "Free" if "free" in thumb_type.lower() else "Unknown"

    try:
        cur.execute("""
            INSERT INTO raw.product_hunt_launches
                (name, tagline, upvotes, category, pricing_type, launch_date, product_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_url) DO NOTHING
        """, (name, tagline, upvotes, category, pricing_type, launch_date, product_url))
        inserted += 1
    except Exception as e:
        print(f"  ⚠️  Skipped '{name}': {e}")
        skipped += 1

# ── 6. Commit and report ──────────────────────────────────────────────────────
conn.commit()
cur.close()
conn.close()

print(f"✅ Done — {inserted} rows inserted, {skipped} skipped.")