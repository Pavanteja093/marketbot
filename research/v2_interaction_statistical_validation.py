from __future__ import annotations

from pathlib import Path
import argparse
import math
import random
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
EPISODES = BASE_DIR / 'research' / 'artifacts' / 'track_c_interaction_episode_stability_episodes.csv'
SUMMARY = BASE_DIR / 'research' / 'artifacts' / 'track_c_interaction_episode_stability.csv'
OUTPUT = BASE_DIR / 'research' / 'artifacts' / 'track_c_interaction_statistical_validation.csv'

GROUP = ['scenario','factor_a','factor_b','state_a','state_b']
CLASSES = ['DOWN','FLAT','UP']
MIN_EPISODES = 3
PERMUTATIONS = 10000
BOOTSTRAPS = 10000


def mean(values):
    return sum(values) / len(values) if values else None


def percentile(sorted_values, q):
    if not sorted_values:
        return None
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos); hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def bootstrap_ci(values, iterations=BOOTSTRAPS, seed=42):
    if len(values) < 2:
        return (None, None)
    rng = random.Random(seed)
    stats = []
    n = len(values)
    for _ in range(iterations):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        stats.append(mean(sample))
    stats.sort()
    return percentile(stats, .025), percentile(stats, .975)


def sign_flip_pvalue(values, iterations=PERMUTATIONS, seed=42):
    """Two-sided random sign-flip test of mean(value) == 0."""
    if len(values) < 2:
        return None
    observed = abs(mean(values))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(iterations):
        signed = [v if rng.random() < .5 else -v for v in values]
        if abs(mean(signed)) >= observed:
            extreme += 1
    return (extreme + 1) / (iterations + 1)


def bh_adjust(pvalues):
    """Benjamini-Hochberg FDR adjustment; None remains None."""
    valid = [(i, p) for i, p in enumerate(pvalues) if p is not None and math.isfinite(p)]
    out = [None] * len(pvalues)
    valid.sort(key=lambda x: x[1])
    m = len(valid)
    prev = 1.0
    for rank in range(m, 0, -1):
        i, p = valid[rank - 1]
        q = min(prev, p * m / rank)
        out[i] = q
        prev = q
    return out


def target_probability(row, target):
    return float(row[f'{target.lower()}_pct'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=Path, default=EPISODES)
    parser.add_argument('--summary', type=Path, default=SUMMARY)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print('\n' + '=' * 78)
    print('MARKETBOT TRACK C - INTERACTION STATISTICAL VALIDATION')
    print('=' * 78)
    print('UNIT OF INFERENCE : independent OOS episodes')
    print('TESTS              : sign-flip + bootstrap + BH-FDR')
    print('RESEARCH ONLY      : YES')

    episodes = pd.read_csv(args.episodes)
    summary = pd.read_csv(args.summary)

    required = set(GROUP) | {
        'episode_id','observations','dominant_outcome','dominant_probability_pct',
        'baseline_probability_pct','probability_uplift_pct','mean_return_5d',
        'down_pct','flat_pct','up_pct'
    }
    missing = sorted(required - set(episodes.columns))
    if missing:
        raise ValueError('Episode artifact missing columns: ' + ', '.join(missing))

    rows = []
    for keys, g in episodes.groupby(GROUP, sort=False):
        if len(g) < MIN_EPISODES:
            continue

        dominant = str(summary.set_index(GROUP).loc[keys, 'dominant_outcome']) if False else None
        # Use the majority target outcome across qualifying episodes. This avoids
        # treating an episode's own winning class as the target after the fact.
        counts = {c: 0 for c in CLASSES}
        for c in g['dominant_outcome'].astype(str):
            if c in counts:
                counts[c] += 1
        target = max(counts, key=counts.get)

        target_uplifts = []
        returns = []
        target_probs = []
        baseline_probs = []
        for _, r in g.iterrows():
            tp = target_probability(r, target)
            bp = float(r['baseline_probability_pct'])
            target_probs.append(tp)
            baseline_probs.append(bp)
            target_uplifts.append(tp - bp)
            returns.append(float(r['mean_return_5d']))

        uplift_ci = bootstrap_ci(target_uplifts)
        return_ci = bootstrap_ci(returns)
        uplift_p = sign_flip_pvalue(target_uplifts)
        return_p = sign_flip_pvalue(returns)

        rows.append({
            **dict(zip(GROUP, keys)),
            'target_outcome': target,
            'episodes': len(g),
            'total_observations': int(g['observations'].sum()),
            'target_dominant_episode_pct': 100.0 * counts[target] / len(g),
            'mean_target_probability_uplift_pct': mean(target_uplifts),
            'median_target_probability_uplift_pct': float(pd.Series(target_uplifts).median()),
            'uplift_ci95_low': uplift_ci[0],
            'uplift_ci95_high': uplift_ci[1],
            'uplift_signflip_p': uplift_p,
            'mean_return_5d': mean(returns),
            'median_return_5d': float(pd.Series(returns).median()),
            'return_ci95_low': return_ci[0],
            'return_ci95_high': return_ci[1],
            'return_signflip_p': return_p,
            'positive_uplift_episodes': sum(v > 0 for v in target_uplifts),
            'positive_return_episodes': sum(v > 0 for v in returns),
        })

    result = pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError('No interaction had at least 3 qualifying OOS episodes.')

    result['uplift_q_fdr'] = bh_adjust(result['uplift_signflip_p'].tolist())
    result['return_q_fdr'] = bh_adjust(result['return_signflip_p'].tolist())

    def decision(r):
        # Statistical candidate only. No production promotion.
        if r['episodes'] < 5:
            return 'INSUFFICIENT_EPISODES'
        if r['uplift_q_fdr'] is not None and r['uplift_q_fdr'] <= 0.10 and r['uplift_ci95_low'] > 0:
            return 'STATISTICAL_UPLIFT_CANDIDATE'
        if r['return_q_fdr'] is not None and r['return_q_fdr'] <= 0.10 and r['return_ci95_low'] > 0:
            return 'ECONOMIC_RETURN_CANDIDATE'
        return 'NOT_STATISTICALLY_CONFIRMED'

    result['decision'] = result.apply(decision, axis=1)
    result['research_status'] = 'RESEARCH_ONLY'
    result = result.sort_values(['decision','uplift_q_fdr','return_q_fdr','episodes'], na_position='last').reset_index(drop=True)

    print(f'Qualifying interactions : {len(result):,}')
    print(f'3+ episode candidates   : {(result.episodes >= 3).sum():,}')
    print(f'5+ episode candidates   : {(result.episodes >= 5).sum():,}')
    print('\nDECISION COUNTS')
    print(result['decision'].value_counts().to_string())
    print('\nTOP STATISTICAL CANDIDATES')
    cols = GROUP + ['target_outcome','episodes','total_observations','target_dominant_episode_pct',
                    'mean_target_probability_uplift_pct','uplift_ci95_low','uplift_ci95_high',
                    'uplift_q_fdr','mean_return_5d','return_ci95_low','return_ci95_high',
                    'return_q_fdr','decision']
    print(result[result['decision'].isin(['STATISTICAL_UPLIFT_CANDIDATE','ECONOMIC_RETURN_CANDIDATE'])].head(30)[cols].to_string(index=False, float_format=lambda x: f'{x:.4f}'))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f'\nSaved: {args.output}')
    print('\nPRODUCTION IMPACT : NONE')
    print('SQLITE WRITES     : NONE')
    print('WEIGHT CHANGES    : NONE')
    print('SIGNAL PROMOTION  : NONE')
    print('STATUS            : SUCCESS')

if __name__ == '__main__':
    main()
