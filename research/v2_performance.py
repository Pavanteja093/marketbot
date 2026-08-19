import sqlite3
from pathlib import Path
from statistics import mean, median

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def _validate_tables(conn):
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    missing = sorted({"signal_history_v2", "prediction_outcomes"} - tables)
    if missing:
        raise RuntimeError(
            "V2.2 analysis requires missing tables: " + ", ".join(missing)
        )


def load_v2_outcomes(db_path=DB_PATH):
    """Load only genuine V2 signals with completed 5-day outcomes."""
    conn = sqlite3.connect(db_path)
    try:
        _validate_tables(conn)
        return conn.execute("""
            SELECT
                s.trade_date,
                s.index_name,
                s.sector,
                s.rank,
                s.intelligence_score,
                o.return_5d
            FROM signal_history_v2 AS s
            INNER JOIN prediction_outcomes AS o
                ON DATE(o.prediction_date) = DATE(s.trade_date)
               AND o.index_name = s.index_name
               AND o.rank = s.rank
            WHERE s.intelligence_score IS NOT NULL
              AND o.return_5d IS NOT NULL
            ORDER BY s.trade_date, s.rank
        """).fetchall()
    finally:
        conn.close()


def _pearson(xs, ys):
    if len(xs) < 2:
        return None
    xb, yb = mean(xs), mean(ys)
    numerator = sum((x - xb) * (y - yb) for x, y in zip(xs, ys))
    xss = sum((x - xb) ** 2 for x in xs)
    yss = sum((y - yb) ** 2 for y in ys)
    denominator = (xss * yss) ** 0.5
    return None if denominator == 0 else numerator / denominator


def _bucket(score):
    if score < 60:
        return "<60"
    if score < 70:
        return "60-70"
    if score < 80:
        return "70-80"
    return "80+"


def _summary(records):
    if not records:
        return {
            "n": 0,
            "mean_return_5d": None,
            "median_return_5d": None,
            "positive_hit_rate": None,
        }
    values = [r["return_5d"] for r in records]
    return {
        "n": len(values),
        "mean_return_5d": mean(values),
        "median_return_5d": median(values),
        "positive_hit_rate": sum(v > 0 for v in values) / len(values),
    }


def analyze(rows):
    """Return read-only predictive-validity statistics for V2 outcomes."""
    if not rows:
        return {
            "sample_size": 0,
            "mean_return_5d": None,
            "median_return_5d": None,
            "positive_hit_rate": None,
            "pearson_score_return": None,
            "top1": _summary([]),
            "top3": _summary([]),
            "top10": _summary([]),
            "score_buckets": {},
            "sector_performance": {},
        }

    records = [
        {
            "trade_date": r[0],
            "index_name": r[1],
            "sector": r[2] or "UNKNOWN",
            "rank": int(r[3]),
            "score": float(r[4]),
            "return_5d": float(r[5]),
        }
        for r in rows
    ]

    returns = [r["return_5d"] for r in records]
    scores = [r["score"] for r in records]

    buckets = {}
    sectors = {}
    for record in records:
        buckets.setdefault(_bucket(record["score"]), []).append(record)
        sectors.setdefault(record["sector"], []).append(record)

    return {
        "sample_size": len(records),
        "mean_return_5d": mean(returns),
        "median_return_5d": median(returns),
        "positive_hit_rate": sum(v > 0 for v in returns) / len(returns),
        "pearson_score_return": _pearson(scores, returns),
        "top1": _summary([r for r in records if r["rank"] == 1]),
        "top3": _summary([r for r in records if r["rank"] <= 3]),
        "top10": _summary([r for r in records if r["rank"] <= 10]),
        "score_buckets": {
            k: _summary(v) for k, v in sorted(buckets.items())
        },
        "sector_performance": {
            k: _summary(v) for k, v in sorted(sectors.items())
        },
    }


def run_v2_performance_analysis(db_path=DB_PATH):
    rows = load_v2_outcomes(db_path)
    result = analyze(rows)

    print("\n" + "=" * 78)
    print("MARKETBOT V2.2 PERFORMANCE & PREDICTIVE VALIDITY")
    print("=" * 78)
    print(f"Completed genuine V2 outcomes : {result['sample_size']:,}")

    if result["sample_size"] == 0:
        print("\nINSUFFICIENT DATA")
        print("No genuine V2 signal has a completed 5-day outcome yet.")
        print("No predictive-validity conclusion is made.")
        print("STATUS: SUCCESS")
        return result

    print(f"Mean 5-day return            : {result['mean_return_5d']:.4f}%")
    print(f"Median 5-day return          : {result['median_return_5d']:.4f}%")
    print(f"Positive-return hit rate     : {result['positive_hit_rate']:.2%}")
    corr = result["pearson_score_return"]
    print(f"Pearson score/return         : {corr:.4f}" if corr is not None else
          "Pearson score/return         : N/A")

    for label in ("top1", "top3", "top10"):
        s = result[label]
        if s["n"]:
            print(
                f"{label.upper():<28}: n={s['n']}, "
                f"mean={s['mean_return_5d']:.4f}%, "
                f"hit={s['positive_hit_rate']:.2%}"
            )
        else:
            print(f"{label.upper():<28}: n=0")

    print("\nSCORE BUCKETS")
    for bucket, s in result["score_buckets"].items():
        print(
            f"{bucket:<8} n={s['n']:<5} "
            f"mean={s['mean_return_5d']:.4f}% "
            f"hit={s['positive_hit_rate']:.2%}"
        )

    print("\nSECTOR PERFORMANCE")
    for sector, s in result["sector_performance"].items():
        print(
            f"{sector:<16} n={s['n']:<5} "
            f"mean={s['mean_return_5d']:.4f}% "
            f"hit={s['positive_hit_rate']:.2%}"
        )

    print("\nSTATUS: SUCCESS")
    return result


if __name__ == "__main__":
    run_v2_performance_analysis()
