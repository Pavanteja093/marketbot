"""MarketBot Track B - Conditional Score Candidate. Research-only."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"
FACTORS = ["relative_strength", "trend_score", "momentum_score", "volatility_score", "liquidity_score"]
TRAIN_DAYS, TEST_DAYS, WINDOWS, MAX_WEIGHT, MIN_IC_DAYS = 120, 20, 5, 0.45, 30
PROFILES = {"TREND": ("trend_score", "momentum_score"), "DEFENSIVE": ("relative_strength", "liquidity_score"), "VOLATILITY": ("volatility_score", "liquidity_score")}

def load_data(db_path=DEFAULT_DB):
    conn = sqlite3.connect(str(db_path))
    try:
        fcols={r[1] for r in conn.execute("PRAGMA table_info(factor_history)")}
        ocols={r[1] for r in conn.execute("PRAGMA table_info(prediction_outcomes)")}
        missing=[f for f in FACTORS if f not in fcols]
        missing += [f"prediction_outcomes.{c}" for c in ("prediction_date","index_name","return_5d") if c not in ocols]
        if missing: raise RuntimeError("Missing required database columns: " + ", ".join(missing))
        q=f'''SELECT DATE(f.trade_date) trade_date, f.index_name entity, {", ".join("f."+f for f in FACTORS)}, o.return_5d FROM factor_history f JOIN prediction_outcomes o ON DATE(f.trade_date)=DATE(o.prediction_date) AND f.index_name=o.index_name WHERE o.return_5d IS NOT NULL ORDER BY DATE(f.trade_date), f.index_name'''
        df=pd.read_sql_query(q,conn)
    finally: conn.close()
    df.trade_date=pd.to_datetime(df.trade_date,errors="coerce")
    for c in FACTORS+["return_5d"]: df[c]=pd.to_numeric(df[c],errors="coerce")
    return df.dropna(subset=["trade_date","entity"]+FACTORS+["return_5d"]).reset_index(drop=True)

def daily_ic(g,f):
    x,y=g[f],g.return_5d
    m=x.notna()&y.notna()
    if m.sum()<5 or x[m].nunique()<2 or y[m].nunique()<2:return np.nan
    return float(x[m].corr(y[m],method="spearman"))

def fit_weights(train):
    ic={f:0.0 for f in FACTORS}
    for f in FACTORS:
        d=train.groupby("trade_date").apply(lambda g:daily_ic(g,f),include_groups=False).dropna()
        if len(d)>=MIN_IC_DAYS: ic[f]=float(d.mean())
    pos={f:max(v,0.0) for f,v in ic.items()}; total=sum(pos.values())
    w={f:(pos[f]/total if total>0 else 1/len(FACTORS)) for f in FACTORS}
    # Cap with iterative redistribution.
    for _ in range(20):
        excess=sum(max(v-MAX_WEIGHT,0) for v in w.values())
        capped={f:min(v,MAX_WEIGHT) for f,v in w.items()}
        if excess<=1e-12: w=capped; break
        free=[f for f,v in capped.items() if v<MAX_WEIGHT-1e-12]
        if not free: w={f:1/len(FACTORS) for f in FACTORS}; break
        denom=sum(capped[f] for f in free)
        for f in free: capped[f]+=excess/len(free) if denom<=0 else excess*capped[f]/denom
        w=capped
    s=sum(w.values()); return {f:w[f]/s for f in FACTORS}

def profile_for_day(day, _train=None):
    # Current-day factor dispersion, not future returns, determines state.
    spread={f:float(day[f].quantile(.8)-day[f].quantile(.2)) for f in FACTORS}
    trend_signal=spread["trend_score"]+spread["momentum_score"]
    vol_signal=spread["volatility_score"]
    liq_signal=spread["liquidity_score"]
    scale=np.median(list(spread.values())) or 1.0
    if vol_signal >= 1.35*scale: return "VOLATILITY"
    if trend_signal >= 2.0*scale: return "TREND"
    return "DEFENSIVE" if liq_signal >= 1.15*scale else "TREND"

def profile_weights(base, profile):
    w=base.copy()
    for f in PROFILES[profile]: w[f]+=0.05
    s=sum(w.values()); return {f:w[f]/s for f in FACTORS}

def score_day(day, weights):
    score=pd.Series(0.0,index=day.index)
    for f in FACTORS: score += weights[f]*day[f].rank(method="average",pct=True)
    return score

def evaluate_day(day, score):
    if len(day)<10:return None
    x=day.copy(); x["score"]=score
    x["q"]=pd.qcut(x["score"].rank(method="first"),5,labels=False,duplicates="drop")
    q1=x.loc[x.q==0,"return_5d"]; q5=x.loc[x.q==4,"return_5d"]
    if q1.empty or q5.empty:return None
    return {"top_return":float(q5.mean()),"bottom_return":float(q1.mean()),"spread":float(q5.mean()-q1.mean()),"top_win_rate":float((q5>0).mean()*100),"bottom_win_rate":float((q1>0).mean()*100)}

def run(db_path=DEFAULT_DB):
    df=load_data(db_path); dates=sorted(df.trade_date.unique()); results=[]
    for i in range(WINDOWS):
        a=i*TEST_DAYS; train_dates=dates[a:a+TRAIN_DAYS]; test_dates=dates[a+TRAIN_DAYS:a+TRAIN_DAYS+TEST_DAYS]
        if len(test_dates)<TEST_DAYS: break
        train=df[df.trade_date.isin(train_dates)]; base=fit_weights(train)
        for date in test_dates:
            day=df[df.trade_date==date].copy(); profile=profile_for_day(day,train); r=evaluate_day(day,score_day(day,profile_weights(base,profile)))
            if r: r.update(window=i+1,test_date=date,profile=profile); results.append(r)
    return pd.DataFrame(results)

def summarize(r):
    if r.empty:return {"days":0,"average_spread":None,"median_spread":None,"positive_day_pct":None}
    return {"days":len(r),"average_spread":float(r.spread.mean()),"median_spread":float(r.spread.median()),"positive_day_pct":float((r.spread>0).mean()*100)}

def main():
    print("="*78); print("MARKETBOT TRACK B - CONDITIONAL SCORE CANDIDATE"); print("="*78)
    r=run(); print("\nWINDOW RESULTS"); print(r.groupby("window").spread.agg(["count","mean","median"]).round(4).to_string()); print("\nPROFILE DISTRIBUTION"); print(r.profile.value_counts().to_string()); print("\nOOS SUMMARY"); print(summarize(r)); print("\nResearch only: production scoring, weights, challenger logic, and live trading were NOT changed.")
if __name__=="__main__": main()
