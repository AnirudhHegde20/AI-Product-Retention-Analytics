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

# ── 3. GraphQL query with pagination support ──────────────────────────────────
def build_query(after_cursor=None):
    after = f', after: "{after_cursor}"' if after_cursor else ""
    return f"""
    {{
      posts(first: 50, order: VOTES{after}) {{
        pageInfo {{
          hasNextPage
          endCursor
        }}
        edges {{
          node {{
            name
            tagline
            votesCount
            topics {{
              edges {{
                node {{
                  name
                }}
              }}
            }}
            thumbnail {{
              type
            }}
            createdAt
            website
          }}
        }}
      }}
    }}
    """

# ── 4. Fetch all pages ────────────────────────────────────────────────────────
headers   = {"Authorization": f"Bearer {TOKEN}"}
cursor    = None
inserted  = 0
skipped   = 0
page      = 1
MAX_PAGES = 10  # fetch up to 500 launches (10 pages x 50 each)

while page <= MAX_PAGES:
    print(f"Fetching page {page}...")

    response = requests.post(
        "https://api.producthunt.com/v2/api/graphql",
        json={"query": build_query(cursor)},
        headers=headers
    )
    data = response.json()

    # Check for API errors
    if "errors" in data:
        print(f"API error: {data['errors']}")
        break

    posts    = data["data"]["posts"]["edges"]
    pageInfo = data["data"]["posts"]["pageInfo"]

    # ── 5. Parse and insert rows ──────────────────────────────────────────────
    for edge in posts:
        node = edge["node"]

        name        = node.get("name")
        tagline     = node.get("tagline")
        upvotes     = node.get("votesCount")
        launch_date = node.get("createdAt", "")[:10]
        product_url = node.get("website") or f"https://www.producthunt.com/posts/{name}"

        topics      = node.get("topics", {}).get("edges", [])
        category    = topics[0]["node"]["name"] if topics else None

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
            print(f"  Skipped '{name}': {e}")
            skipped += 1

    conn.commit()
    print(f"  Page {page} done — {inserted} total inserted so far")

    # ── 6. Check if more pages exist ──────────────────────────────────────────
    if pageInfo["hasNextPage"]:
        cursor = pageInfo["endCursor"]
        page  += 1
    else:
        print("No more pages available.")
        break

# ── 7. Cleanup ────────────────────────────────────────────────────────────────
cur.close()
conn.close()
print(f"\n✅ Done — {inserted} rows inserted, {skipped} skipped.")