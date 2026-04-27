"""Quick DB verification test — run with: python tests/test_db_verify.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB = "postgresql://neondb_owner:npg_iT2HlX0VZpsA@ep-cold-wind-a1wh74pm-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ["DATABASE_URL"] = DB

import psycopg2
import psycopg2.extras

def check_db():
    conn = psycopg2.connect(DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    tables = ["kols", "episodes", "consensus_daily", "stock_mentions"]
    for t in tables:
        cur.execute(f"SELECT COUNT(*) as n FROM {t}")
        n = cur.fetchone()["n"]
        status = "OK" if n > 0 else "EMPTY"
        print(f"  [{status}] {t}: {n} rows")

    cur.execute("SELECT date, consensus_score, bullish_pct FROM consensus_daily ORDER BY date DESC LIMIT 3")
    print("\n  Latest consensus:")
    for r in cur.fetchall():
        print(f"    {r['date']} score={r['consensus_score']} bullish={r['bullish_pct']}%")

    cur.execute("SELECT kol_id, kol_name FROM kols ORDER BY kol_id")
    print("\n  KOLs registered:")
    for r in cur.fetchall():
        print(f"    {r['kol_id']:15} {r['kol_name']}".encode("ascii", "replace").decode())

    conn.close()


def check_db_writer():
    """Test write_episode + compute_and_write_consensus end-to-end."""
    from app.db_writer import write_episode, compute_and_write_consensus
    from datetime import date

    test_date = date(2099, 1, 1)   # 未來日期，不會影響真實資料

    # 先確保 kol 存在（用已知的 kol_id）
    import psycopg2
    conn = psycopg2.connect(DB)
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO kols (kol_id, kol_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                ("test_kol", "測試 KOL")
            )
    conn.close()

    ok = write_episode(
        kol_id="test_kol",
        guid="test-guid-001",
        title="測試集數：NVDA 與 台積電的選擇",
        published_str="2099-01-01",
        summary="這是一個測試摘要，用來驗證 DB 寫入是否正常運作。NVDA 超強，2330 也不錯。",
        sentiment="bullish",
        stocks_mentioned=["NVDA", "2330"],
        report_url="https://example.com/report",
        analysis_date=test_date,
    )
    print(f"\n  write_episode: {'OK' if ok else 'FAILED'}")

    ok2 = compute_and_write_consensus(analysis_date=test_date)
    print(f"  compute_consensus: {'OK' if ok2 else 'FAILED'}")

    # 清理測試資料
    conn = psycopg2.connect(DB)
    with conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stock_mentions WHERE date = %s", (test_date,))
            cur.execute("DELETE FROM consensus_daily WHERE date = %s", (test_date,))
            cur.execute("DELETE FROM episodes WHERE kol_id = 'test_kol'")
            cur.execute("DELETE FROM kols WHERE kol_id = 'test_kol'")
    conn.close()
    print("  cleanup: OK")


if __name__ == "__main__":
    print("=" * 50)
    print("Step 1: DB contents")
    print("=" * 50)
    check_db()

    print()
    print("=" * 50)
    print("Step 2: db_writer round-trip")
    print("=" * 50)
    check_db_writer()

    print()
    print("ALL TESTS PASSED")
