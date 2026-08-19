from research.v2_performance import load_v2_outcomes, analyze
from research.v2_statistical_validation import validate


def classify(sample_size, stats):
    if sample_size == 0:
        return "INSUFFICIENT DATA"
    if sample_size < 30:
        return "EARLY / EXPLORATORY"
    if sample_size < 100:
        return "DEVELOPING EVIDENCE"
    pearson_p = stats.get("pearson_p_value")
    spearman_p = stats.get("spearman_p_value")
    spread = stats.get("top10_vs_universe_spread")
    if (sample_size >= 200 and pearson_p is not None and spearman_p is not None
            and pearson_p < 0.05 and spearman_p < 0.05
            and spread is not None and spread > 0):
        return "STATISTICALLY SUPPORTIVE"
    if (pearson_p is not None and spearman_p is not None
            and pearson_p >= 0.05 and spearman_p >= 0.05
            and (spread is None or spread <= 0)):
        return "NO PREDICTIVE EVIDENCE"
    return "MIXED / INCONCLUSIVE"


def build_report(rows=None, permutations=5000, bootstrap_iterations=5000):
    if rows is None:
        rows = load_v2_outcomes()
    performance = analyze(rows)
    stats = validate(rows, permutations=permutations,
                     bootstrap_iterations=bootstrap_iterations)
    return {
        "classification": classify(len(rows), stats),
        "sample_size": len(rows),
        "performance": performance,
        "statistics": stats,
        "production_action": "NO CHANGE",
    }


def print_report(report):
    print("\n" + "=" * 78)
    print("MARKETBOT V2.2 PREDICTIVE VALIDITY REPORT")
    print("=" * 78)
    print(f"Evidence classification       : {report['classification']}")
    print(f"Completed genuine V2 outcomes : {report['sample_size']:,}")
    if report["sample_size"] == 0:
        print("\nNo predictive-validity conclusion is possible yet.")
        print("Continue collecting genuine live V2 outcomes.")
        print("Production action             : NO CHANGE")
        print("STATUS: SUCCESS")
        return
    performance = report["performance"]
    stats = report["statistics"]
    print(f"Mean 5-day return             : {performance['mean_return_5d']:.4f}%")
    print(f"Median 5-day return           : {performance['median_return_5d']:.4f}%")
    print(f"Positive-return hit rate      : {performance['positive_hit_rate']:.2%}")
    print(f"Pearson score/return           : {stats['pearson']:.4f}")
    print(f"Pearson permutation p-value   : {stats['pearson_p_value']:.4f}")
    print(f"Spearman score/return          : {stats['spearman']:.4f}")
    print(f"Spearman permutation p-value  : {stats['spearman_p_value']:.4f}")
    spread = stats["top10_vs_universe_spread"]
    print(f"Top-10 vs universe spread      : {spread:.4f}%" if spread is not None else "Top-10 vs universe spread      : N/A")
    print(f"Production action              : {report['production_action']}")
    if stats.get("warning"):
        print(f"Robustness warning             : {stats['warning']}")
    print("STATUS: SUCCESS")


def run_v2_validation_report(permutations=5000, bootstrap_iterations=5000):
    report = build_report(permutations=permutations,
                          bootstrap_iterations=bootstrap_iterations)
    print_report(report)
    return report


if __name__ == "__main__":
    run_v2_validation_report()
