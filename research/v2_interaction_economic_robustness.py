from __future__ import annotations

from pathlib import Path
import argparse
import pandas as pd

GROUP = ['scenario','factor_a','factor_b','state_a','state_b']
CLASSES = ['DOWN','FLAT','UP']
MIN_EPISODES = 5


def target_prob(row, target):
    return float(row[f'{target.lower()}_pct'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    print('\n' + '=' * 78)
    print('MARKETBOT TRACK C - INTERACTION ECONOMIC ROBUSTNESS')
    print('=' * 78)
    print('UNIT OF ANALYSIS : independent OOS episodes')
    print('MIN EPISODES     : 5')
    print('RESEARCH ONLY    : YES')

    df = pd.read_csv(args.episodes)
    required = set(GROUP) | {'dominant_outcome','observations','down_pct','flat_pct','up_pct','baseline_probability_pct','mean_return_5d','median_return_5d'}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(missing))

    rows=[]
    for keys,g in df.groupby(GROUP, sort=False):
        if len(g) < MIN_EPISODES:
            continue
        counts = g['dominant_outcome'].value_counts().reindex(CLASSES, fill_value=0)
        target = counts.idxmax()
        target_probs = g.apply(lambda r: target_prob(r,target), axis=1)
        uplift = target_probs - g['baseline_probability_pct'].astype(float)
        returns = g['mean_return_5d'].astype(float)
        rows.append({
            **dict(zip(GROUP,keys)),
            'target_outcome': target,
            'episodes': len(g),
            'total_observations': int(g['observations'].sum()),
            'target_consistency_pct': float(counts[target]/len(g)*100),
            'positive_uplift_pct': float((uplift>0).mean()*100),
            'positive_return_pct': float((returns>0).mean()*100),
            'mean_target_uplift_pct': float(uplift.mean()),
            'median_target_uplift_pct': float(uplift.median()),
            'worst_target_uplift_pct': float(uplift.min()),
            'mean_return_5d': float(returns.mean()),
            'median_return_5d': float(returns.median()),
            'worst_episode_mean_return_5d': float(returns.min()),
            'best_episode_mean_return_5d': float(returns.max()),
            'return_positive_minus_negative_balance': float((returns>0).sum()-(returns<=0).sum()),
        })
    result=pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError('No interaction has at least 5 OOS episodes.')

    def decision(r):
        if (r['target_consistency_pct'] >= 70 and r['positive_uplift_pct'] >= 70 and r['positive_return_pct'] >= 70 and r['mean_return_5d'] > 0):
            return 'ECONOMIC_ROBUSTNESS_CANDIDATE'
        return 'NOT_ECONOMICALLY_ROBUST'
    result['decision']=result.apply(decision,axis=1)
    result['research_status']='RESEARCH_ONLY'
    result=result.sort_values(['decision','mean_return_5d','mean_target_uplift_pct','positive_return_pct'],ascending=[True,False,False,False]).reset_index(drop=True)

    print(f'Qualifying interactions : {len(result):,}')
    print('\nDECISION COUNTS')
    print(result['decision'].value_counts().to_string())
    print('\nTOP ECONOMIC ROBUSTNESS CANDIDATES')
    cols=GROUP+['target_outcome','episodes','total_observations','target_consistency_pct','positive_uplift_pct','positive_return_pct','mean_target_uplift_pct','worst_target_uplift_pct','mean_return_5d','median_return_5d','worst_episode_mean_return_5d','decision']
    print(result[result.decision=='ECONOMIC_ROBUSTNESS_CANDIDATE'].head(30)[cols].to_string(index=False,float_format=lambda x:f'{x:.4f}'))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result.to_csv(args.output,index=False)
    print(f'\nSaved: {args.output}')
    print('\nPRODUCTION IMPACT : NONE')
    print('SQLITE WRITES     : NONE')
    print('WEIGHT CHANGES    : NONE')
    print('SIGNAL PROMOTION  : NONE')
    print('STATUS            : SUCCESS')

if __name__=='__main__': main()
