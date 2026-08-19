from __future__ import annotations
import sqlite3
from math import comb
from pathlib import Path
from typing import Iterable
import numpy as np
import pandas as pd

BASE_DIR=Path(__file__).resolve().parents[1]
DATASET=BASE_DIR/'research/artifacts/historical_probability_dataset.csv'
DB_PATH=BASE_DIR/'market_intelligence.db'
OUTPUT=BASE_DIR/'research/artifacts/track_d_phase2_1_global_wf_conditional_regime.csv'
RUN_LOG=BASE_DIR/'research/artifacts/track_d_phase2_1_global_wf_conditional_regime_run.log'
FACTORS=('intelligence_score','volatility_score','trend_score')
REGIMES=('CHOPPY','FLAT','HIGH_VOL','LOW_VOL','TREND_DOWN','TREND_UP')
HORIZONS=(1,5,10,20)
MIN_TRAIN_DAYS=80; TEST_DAYS=20; MIN_IC_OBS=3; MIN_TRAIN_Q=20; MIN_TEST_Q=10; BOOTSTRAPS=2000; SEED=20260813
REQ_DATA={'trade_date','index_name','scenario',*FACTORS}
REQ_FWD={'trade_date','index_name',*(f'return_{h}d' for h in HORIZONS)}

def validate_columns(df, required, name):
    missing=sorted(required-set(df.columns))
    if missing: raise ValueError(f'{name} missing required columns: {", ".join(missing)}')

def read_forward_returns(db_path=DB_PATH):
    if not db_path.exists(): raise FileNotFoundError(f'SQLite database not found: {db_path}')
    uri=f'file:{db_path.resolve().as_posix()}?mode=ro'
    conn=sqlite3.connect(uri, uri=True)
    try:
        cols={r[1] for r in conn.execute('PRAGMA table_info(forward_returns)').fetchall()}
        if not cols: raise ValueError('SQLite table forward_returns not found')
        miss=sorted(REQ_FWD-cols)
        if miss: raise ValueError('forward_returns missing required columns: '+', '.join(miss))
        return pd.read_sql_query('SELECT trade_date,index_name,return_1d,return_5d,return_10d,return_20d FROM forward_returns',conn)
    finally: conn.close()

def load_dataset(dataset_path=DATASET, db_path=DB_PATH):
    factors=pd.read_csv(dataset_path); validate_columns(factors,REQ_DATA,'historical_probability_dataset')
    forward=read_forward_returns(db_path)
    factors=factors.copy(deep=True); forward=forward.copy(deep=True)
    factors['trade_date']=pd.to_datetime(factors['trade_date'],errors='coerce'); forward['trade_date']=pd.to_datetime(forward['trade_date'],errors='coerce')
    factors['index_name']=factors['index_name'].astype(str); forward['index_name']=forward['index_name'].astype(str)
    factors=factors[['trade_date','index_name','scenario',*FACTORS]]
    out=factors.merge(forward,on=['trade_date','index_name'],how='inner',validate='many_to_one')
    for c in FACTORS: out[c]=pd.to_numeric(out[c],errors='coerce')
    for h in HORIZONS: out[f'return_{h}d']=pd.to_numeric(out[f'return_{h}d'],errors='coerce')
    return out.dropna(subset=['trade_date','index_name','scenario']).sort_values(['trade_date','index_name'],kind='mergesort').reset_index(drop=True)

def make_global_oos_folds(dates:Iterable[pd.Timestamp],min_train_days=MIN_TRAIN_DAYS,test_days=TEST_DAYS):
    if min_train_days<1 or test_days<1: raise ValueError('fold parameters must be positive')
    u=pd.DatetimeIndex(sorted(pd.Series(list(dates)).dropna().unique()))
    if len(u)<min_train_days+test_days: return []
    folds=[]; p=min_train_days-1
    while p+test_days<len(u):
        folds.append((u[0],u[p],u[p+1],u[p+test_days])); p+=test_days
    return folds

def spearman(x,y):
    a=pd.to_numeric(x,errors='coerce'); b=pd.to_numeric(y,errors='coerce'); mask=a.notna()&b.notna()
    if int(mask.sum())<MIN_IC_OBS: return np.nan
    return float(a[mask].rank(method='average').corr(b[mask].rank(method='average')))

def _edges(train):
    v=pd.to_numeric(train,errors='coerce').dropna().to_numpy(float)
    if len(v)<MIN_TRAIN_Q: return None
    e=np.quantile(v,[.2,.4,.6,.8])
    return None if len(np.unique(e))<4 or not np.all(np.isfinite(e)) else e

def quintile_spread(train,test,factor,return_col):
    e=_edges(train[factor]);
    if e is None: return np.nan
    x=pd.to_numeric(test[factor],errors='coerce'); y=pd.to_numeric(test[return_col],errors='coerce'); mask=x.notna()&y.notna()
    if int(mask.sum())<MIN_TEST_Q: return np.nan
    g=np.digitize(x[mask].to_numpy(float),e,right=True)+1; r=y[mask].to_numpy(float)
    q1=r[g==1]; q5=r[g==5]
    return np.nan if len(q1)==0 or len(q5)==0 else float(q5.mean()-q1.mean())

def sign_test_pvalue(values):
    a=[float(v) for v in values if pd.notna(v) and float(v)!=0]
    n=len(a)
    if not n:return np.nan
    k=sum(v>0 for v in a)
    tail=sum(comb(n,i) for i in range(k,n+1)) if k>=n/2 else sum(comb(n,i) for i in range(k+1))
    return min(1.0,2.0*tail/(2**n))

def benjamini_hochberg(p_values):
    v=np.asarray(list(p_values),float); out=np.full(len(v),np.nan); idx=np.flatnonzero(np.isfinite(v))
    if len(idx)==0:return out.tolist()
    order=idx[np.argsort(v[idx],kind='mergesort')]; m=len(order); run=1.0
    for rank in range(m,0,-1):
        i=order[rank-1]; run=min(run,v[i]*m/rank); out[i]=min(1.0,run)
    return out.tolist()

def bootstrap_mean_ci(values,seed=SEED,n_bootstrap=BOOTSTRAPS):
    a=np.asarray([float(v) for v in values if pd.notna(v)],float)
    if len(a)==0:return np.nan,np.nan
    if len(a)==1:return float(a[0]),float(a[0])
    rng=np.random.default_rng(seed); s=rng.choice(a,size=(n_bootstrap,len(a)),replace=True).mean(axis=1)
    return float(np.quantile(s,.025)),float(np.quantile(s,.975))

def classify_evidence(regime_total_dates,regime_oos_dates,oos_fold_count,finite_ic_folds,positive_ic_pct,positive_spread_pct,adjusted_p_value):
    if regime_total_dates<2 or regime_oos_dates<2 or oos_fold_count<2 or finite_ic_folds<2:return 'INSUFFICIENT_TEMPORAL_COVERAGE'
    if not np.isfinite(adjusted_p_value):return 'WEAK_OOS_EVIDENCE'
    if positive_ic_pct<=25 or positive_spread_pct<=25:return 'INCONSISTENT_OOS_EVIDENCE'
    if positive_ic_pct>=75 and positive_spread_pct>=75 and adjusted_p_value<.05 and finite_ic_folds>=3:return 'REPEATABLE_PREDICTIVE_EVIDENCE'
    return 'WEAK_OOS_EVIDENCE'

def validate(data,regimes=REGIMES,factors=FACTORS,horizons=HORIZONS,min_train_days=MIN_TRAIN_DAYS,test_days=TEST_DAYS):
    req=REQ_DATA|{f'return_{h}d' for h in horizons}; validate_columns(data,req,'dataset'); original=data.copy(deep=True); w=original.copy(deep=True)
    w['trade_date']=pd.to_datetime(w['trade_date'],errors='coerce'); w['scenario']=w['scenario'].astype(str)
    for c in factors: w[c]=pd.to_numeric(w[c],errors='coerce')
    for h in horizons: w[f'return_{h}d']=pd.to_numeric(w[f'return_{h}d'],errors='coerce')
    folds=make_global_oos_folds(w.trade_date.dropna().unique(),min_train_days,test_days); rows=[]
    for regime in regimes:
        rd=w[w.scenario.eq(regime)].copy(); rdates=pd.DatetimeIndex(rd.trade_date.dropna().unique()); roos=set()
        for _,_,ts,te in folds: roos.update(rdates[(rdates>=ts)&(rdates<=te)].tolist())
        for factor in factors:
            for h in horizons:
                rc=f'return_{h}d'; ics=[]; spreads=[]; fold_count=0
                for _,(tr_s,tr_e,te_s,te_e) in enumerate(folds,1):
                    train=w[(w.trade_date>=tr_s)&(w.trade_date<=tr_e)].copy(); test=rd[(rd.trade_date>=te_s)&(rd.trade_date<=te_e)].copy()
                    if test.empty: continue
                    fold_count+=1; ic=spearman(test[factor],test[rc]); sp=quintile_spread(train,test,factor,rc)
                    if pd.notna(ic):ics.append(float(ic))
                    if pd.notna(sp):spreads.append(float(sp))
                ia=np.asarray(ics,float); sa=np.asarray(spreads,float); mean_ic=float(ia.mean()) if len(ia) else np.nan; ic_std=float(ia.std(ddof=1)) if len(ia)>1 else np.nan; icir=float(mean_ic/ic_std) if np.isfinite(mean_ic) and np.isfinite(ic_std) and ic_std>0 else np.nan
                pic=float((ia>0).mean()*100) if len(ia) else np.nan; msp=float(sa.mean()) if len(sa) else np.nan; psp=float((sa>0).mean()*100) if len(sa) else np.nan; lo,hi=bootstrap_mean_ci(sa); raw=sign_test_pvalue(sa)
                rows.append(dict(scenario=regime,factor=factor,horizon_days=h,global_oos_fold_count=len(folds),oos_fold_count=fold_count,oos_finite_ic_folds=len(ia),regime_total_dates=len(rdates),regime_oos_dates=len(roos),oos_mean_ic=mean_ic,oos_ic_std=ic_std,oos_icir=icir,oos_positive_ic_fold_pct=pic,mean_quintile_spread=msp,positive_spread_fold_pct=psp,bootstrap_95ci_low=lo,bootstrap_95ci_high=hi,raw_sign_test_p_value=raw,adjusted_p_value=np.nan,evidence_classification='PENDING_BH'))
    out=pd.DataFrame(rows); out['adjusted_p_value']=benjamini_hochberg(out.raw_sign_test_p_value.tolist())
    out['evidence_classification']=[classify_evidence(int(r.regime_total_dates),int(r.regime_oos_dates),int(r.oos_fold_count),int(r.oos_finite_ic_folds),float(r.oos_positive_ic_fold_pct) if pd.notna(r.oos_positive_ic_fold_pct) else np.nan,float(r.positive_spread_fold_pct) if pd.notna(r.positive_spread_fold_pct) else np.nan,float(r.adjusted_p_value) if pd.notna(r.adjusted_p_value) else np.nan) for r in out.itertuples()]
    out=out.sort_values(['scenario','factor','horizon_days'],kind='mergesort').reset_index(drop=True); pd.testing.assert_frame_equal(data,original); return out

def run():
    data=load_dataset(); result=validate(data); OUTPUT.parent.mkdir(parents=True,exist_ok=True); result.to_csv(OUTPUT,index=False)
    log='\n'.join(['TRACK D PHASE 2.1 - GLOBAL WF CONDITIONAL REGIME VALIDATOR','READ-ONLY','SQLite writes: NONE','Production changes: NONE','Weight changes: NONE','Candidate promotion: NONE',f'Rows written: {len(result)}',f'CSV: {OUTPUT}'])+'\n'; RUN_LOG.write_text(log,encoding='utf-8'); print(log); print(result.to_string(index=False)); return result

if __name__=='__main__': run()
