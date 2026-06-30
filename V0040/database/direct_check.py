import psycopg2

# Direct connection without pool
conn = psycopg2.connect(
    host="172.16.1.45",
    port=5432,
    database="ut_vfx",
    user="postgres",
    password="Tango$$",
    connect_timeout=5
)

cur = conn.cursor()

# Check active queries
cur.execute("""
    SELECT pid, state, query_start, query 
    FROM pg_stat_activity 
    WHERE datname = 'ut_vfx' 
    AND state = 'active'
    AND query NOT LIKE '%pg_stat_activity%'
""")

results = cur.fetchall()

print("=" * 70)
if results:
    print(f"✅ YES - Database is WORKING on {len(results)} active query(ies)!")
    print("=" * 70)
    for pid, state, start, query in results:
        print(f"\nPID: {pid}")
        print(f"Started: {start}")
        print(f"Query: {query[:300]}")
        print("-" * 70)
    print("\n✅ CONFIRMED: It's safe to wait. Progress is being made!")
else:
    print("⚠️ NO ACTIVE QUERIES - Script might be stuck")
    print("=" * 70)

# Check created indexes
cur.execute("""
    SELECT indexname FROM pg_indexes 
    WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
    ORDER BY indexname
""")

indexes = cur.fetchall()
print(f"\n📊 Indexes created so far: {len(indexes)}")
for (idx,) in indexes:
    print(f"  ✓ {idx}")

cur.close()
conn.close()
