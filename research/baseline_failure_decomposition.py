from __future__ import annotations

"""MarketBot Track B - Baseline Failure Decomposition.

Research-only diagnostic. It does not modify production scoring, weights,
database records, challenger logic, or live trading.
"""
import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "market_intelligence.db"
FACTORS = ["relative_strength", "trend_score", "momentum_score", "volatility_score", "liquidity_score"]
MIN_DAILY_OBS = 10
MAX_FACTOR_WEIGHT = 0.45

@dataclass(frozen=True)
class Config:
    train_days: int = 120
    test_days: int = 20
    min_daily_obs: int = MIN_DAILY_OBS
    max_factor_weight: float = MAX_FACTOR_WEIGHT
    volatility_window: int = 20
    dispersion_window: int = 20

def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

def _resolve_entity(columns: set[str]) -> str:
    for name in ("index_name", "symbol", "ticker"):
        if name in columns:
            return name
    raise RuntimeError("No supported entity column found: index_name/symbol/ticker")

def load_matched_data(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    conn = sqlite3.connect(str(db_path))
    try:
        fcols = _table_columns(conn, "factor_history")
        ocols = _table_columns(conn, "prediction_outcomes")
        missing = [f for f in FACTORS if f not in fcols]
        missing += [f"prediction_outcomes.{c}" for c in ("prediction_date", "return_5d") if c not in ocols]
        if missing:
            raise RuntimeError("Missing required columns: " + ", ".join(missing))
        fe, oe = _resolve_entity(fcols), _resolve_entity(ocols)
        query = f"""
            SELECT DATE(f.trade_date) trade_date, f.{fe} entity,
                   {', '.join('f.' + f for f in FACTORS)}, o.return_5d
            FROM factor_history f
            INNER JOIN prediction_outcomes o
              ON DATE(f.trade_date)=DATE(o.prediction_date)
             AND f.{fe}=o.{oe}
            WHERE o.return_5d IS NOT NULL
            ORDER BY DATE(f.trade_date), f.{fe}
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    for col in FACTORS + ["return_5d"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["trade_date", "entity"] + FACTORS + ["return_5d"]).drop_duplicates(["trade_date", "entity"]).reset_index(drop=True)

def load_market_context(db_path: Path = DEFAULT_DB, dates: Iterable[pd.Timestamp] | None = None) -> pd.DataFrame:
    conn = sqlite3.connect(str(db_path))
    try:
        icols = _table_columns(conn, "indices_daily")
        if "trade_date" not in icols or "close" not in icols:
            raise RuntimeError("indices_daily requires trade_date and close")
        if "index_name" in icols:
            market = pd.read_sql_query("SELECT DATE(trade_date) trade_date, close FROM indices_daily WHERE index_name='NIFTY50' ORDER BY DATE(trade_date)", conn)
        else:
            market = pd.read_sql_query("SELECT DATE(trade_date) trade_date, close FROM indices_daily ORDER BY DATE(trade_date)", conn)
        scols = _table_columns(conn, "stocks_daily")
        stocks = pd.read_sql_query("SELECT DATE(trade_date) trade_date, symbol, change_pct FROM stocks_daily WHERE change_pct IS NOT NULL", conn) if {"trade_date","symbol","change_pct"}.issubset(scols) else pd.DataFrame()
    finally:
        conn.close()
    market["trade_date"] = pd.to_datetime(market["trade_date"], errors="coerce")
    market["close"] = pd.to_numeric(market["close"], errors="coerce")
    market = market.dropna(subset=["trade_date","close"]).drop_duplicates("trade_date").sort_values("trade_date").reset_index(drop=True)
    market["market_return_1d"] = market["close"].pct_change()
    market["market_vol_20"] = market["market_return_1d"].rolling(20, min_periods=10).std()
    market["vol_q25"] = market["market_vol_20"].expanding(min_periods=20).quantile(.25)
    market["vol_q75"] = market["market_vol_20"].expanding(min_periods=20).quantile(.75)
    market["direction_state"] = np.select([market.market_return_1d>0, market.market_return_1d<0], ["UP","DOWN"], default="FLAT")
    market["volatility_state"] = np.select([market.market_vol_20>=market.vol_q75, market.market_vol_20<=market.vol_q25], ["HIGH","LOW"], default="NORMAL")
    if not stocks.empty:
        stocks["trade_date"] = pd.to_datetime(stocks["trade_date"], errors="coerce")
        stocks["change_pct"] = pd.to_numeric(stocks["change_pct"], errors="coerce")
        b = stocks.dropna(subset=["trade_date","change_pct"]).groupby("trade_date").agg(advancers=("change_pct",lambda x: float((x>0).mean())), dispersion=("change_pct","std")).reset_index()
        b["breadth_state"] = np.select([b.advancers>=.60,b.advancers<=.40],["BULLISH_BREADTH","BEARISH_BREADTH"],default="MIXED_BREADTH")
        b["dispersion_q75"] = b.dispersion.expanding(min_periods=20).quantile(.75)
        b["dispersion_state"] = np.where(b.dispersion>=b.dispersion_q75,"HIGH_DISPERSION","NORMAL_DISPERSION")
        market = market.merge(b,on="trade_date",how="left")
    else:
        market["breadth_state"]="UNKNOWN_BREADTH"; market["dispersion_state"]="UNKNOWN_DISPERSION"; market["advancers"]=np.nan; market["dispersion"]=np.nan
    if dates is not None:
        market = market[market.trade_date.isin(pd.to_datetime(list(dates)))]
    return market.reset_index(drop=True)

def cross_sectional_ic(day: pd.DataFrame, column: str) -> float:
    x,y = pd.to_numeric(day[column],errors="coerce"),pd.to_numeric(day["return_5d"],errors="coerce")
    valid=x.notna()&y.notna()
    if valid.sum()<5 or x[valid].nunique()<2 or y[valid].nunique()<2: return np.nan
    return float(x[valid].corr(y[valid],method="spearman"))

def _cap_weights(weights: pd.Series, cap: float) -> pd.Series:
    w=pd.to_numeric(weights,errors="coerce").fillna(0).clip(lower=0)
    if w.sum()<=0: return pd.Series(1/len(w),index=w.index)
    w=w/w.sum(); result=pd.Series(0.,index=w.index); fixed=pd.Series(False,index=w.index); remaining=1.
    for _ in range(len(w)+2):
        active=(~fixed)&(w>0)
        if not active.any(): break
        raw=w[active]/w[active].sum()*remaining; over=raw>cap+1e-12
        if not over.any(): result.loc[active]=raw; remaining=0; break
        for idx in raw[over].index: result.loc[idx]=cap; fixed.loc[idx]=True; remaining-=cap
    if remaining>1e-10:
        active=(~fixed)&(result==0)
        if active.any(): result.loc[active]=remaining/active.sum()
    return result/result.sum()

def fit_baseline_weights(train: pd.DataFrame, config: Config) -> pd.Series:
    rows=[]
    for _,day in train.groupby("trade_date",sort=True): rows.append({f:cross_sectional_ic(day,f) for f in FACTORS})
    ic=pd.DataFrame(rows); return _cap_weights(ic.mean().fillna(0).abs(),config.max_factor_weight)

def add_baseline_score(day: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    out=day.copy(); score=np.zeros(len(out))
    for f in FACTORS:
        rank=pd.Series(pd.to_numeric(out[f],errors="coerce")).rank(pct=True).to_numpy(); score+=float(weights.get(f,0))*(np.nan_to_num(rank,nan=.5)-.5)
    out["baseline_score"]=score; return out

def evaluate_day(day: pd.DataFrame,min_obs: int=MIN_DAILY_OBS) -> dict|None:
    work=day.dropna(subset=["baseline_score","return_5d"]).copy()
    if len(work)<min_obs:return None
    work["quintile"]=pd.qcut(work["baseline_score"].rank(method="first"),5,labels=False)
    top=work.loc[work.quintile==4,"return_5d"]; bottom=work.loc[work.quintile==0,"return_5d"]
    if top.empty or bottom.empty:return None
    return {"trade_date":work.trade_date.iloc[0],"spread":float(top.mean()-bottom.mean()),"top_return":float(top.mean()),"bottom_return":float(bottom.mean()),"observations":int(len(work)),"baseline_ic":cross_sectional_ic(work,"baseline_score")}

def attach_factor_diagnostics(matched: pd.DataFrame, market_context: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for date,day in matched.groupby("trade_date",sort=True):
        row={"trade_date":date}; vals=[]
        for f in FACTORS:
            ic=cross_sectional_ic(day,f); row[f+"_ic"]=ic
            if pd.notna(ic): vals.append(np.sign(ic))
        row["factor_agreement"]=float(abs(np.mean(vals))) if vals else np.nan
        row["positive_factor_pct"]=float(np.mean(np.array(vals)>0)) if vals else np.nan; rows.append(row)
    return pd.DataFrame(rows).merge(market_context,on="trade_date",how="left")

def condition_summary(evaluated: pd.DataFrame, condition: str) -> pd.DataFrame:
    if evaluated.empty or condition not in evaluated:return pd.DataFrame()
    rows=[]
    for state,g in evaluated.groupby(condition,dropna=False,sort=True):
        s=pd.to_numeric(g.spread,errors="coerce").dropna()
        if s.empty:continue
        rows.append({"condition":condition,"state":str(state),"days":len(s),"mean_spread":float(s.mean()),"median_spread":float(s.median()),"positive_day_pct":float((s>0).mean()*100),"worst_day":float(s.min()),"best_day":float(s.max())})
    return pd.DataFrame(rows)

def build_failure_report(evaluated: pd.DataFrame) -> dict[str,pd.DataFrame]:
    reports={c:condition_summary(evaluated,c) for c in ("direction_state","volatility_state","breadth_state","dispersion_state","agreement_state")}
    reports["overall"]=pd.DataFrame() if evaluated.empty else pd.DataFrame([{"days":len(evaluated),"mean_spread":evaluated.spread.mean(),"median_spread":evaluated.spread.median(),"positive_day_pct":(evaluated.spread>0).mean()*100,"worst_day":evaluated.spread.min(),"best_day":evaluated.spread.max()}])
    return reports

def run_walk_forward(matched: pd.DataFrame, market_context: pd.DataFrame, config: Config=Config()) -> tuple[pd.DataFrame,dict[str,pd.DataFrame]]:
    matched=matched.copy(); matched["trade_date"]=pd.to_datetime(matched.trade_date); dates=sorted(matched.trade_date.drop_duplicates())
    if len(dates)<config.train_days+config.test_days:return pd.DataFrame(),{"overall":pd.DataFrame()}
    diagnostics=attach_factor_diagnostics(matched,market_context); rows=[]; start=config.train_days
    while start<len(dates):
        test_dates=dates[start:start+config.test_days]
        if len(test_dates)<config.test_days:break
        train=matched[matched.trade_date.isin(dates[start-config.train_days:start])]; test=matched[matched.trade_date.isin(test_dates)]; weights=fit_baseline_weights(train,config)
        for _,day in test.groupby("trade_date",sort=True):
            r=evaluate_day(add_baseline_score(day,weights),config.min_daily_obs)
            if r:rows.append(r)
        start+=config.test_days
    evaluated=pd.DataFrame(rows)
    if evaluated.empty:return evaluated,{"overall":pd.DataFrame()}
    evaluated=evaluated.merge(diagnostics,on="trade_date",how="left")
    evaluated["agreement_state"]=np.select([evaluated.factor_agreement>=.60,evaluated.factor_agreement<=.20],["HIGH_AGREEMENT","LOW_AGREEMENT"],default="MIXED_AGREEMENT")
    return evaluated,build_failure_report(evaluated)

def analyze(db_path: Path=DEFAULT_DB,config: Config=Config()) -> dict:
    print("\n"+"="*78); print("MARKETBOT TRACK B - BASELINE FAILURE DECOMPOSITION"); print("="*78)
    matched=load_matched_data(db_path)
    if matched.empty: print("\nNo matched factor/outcome observations."); return {"observations":0}
    context=load_market_context(db_path,matched.trade_date.unique()); evaluated,reports=run_walk_forward(matched,context,config)
    print(f"\nMatched observations : {len(matched):,}\nTrading dates        : {matched.trade_date.nunique():,}\nEntities             : {matched.entity.nunique():,}\nEvaluated OOS days   : {len(evaluated):,}")
    if reports["overall"].empty: print("\nNo evaluable OOS days."); return {"observations":len(matched),"evaluated_days":0,"reports":reports}
    print("\nOVERALL BASELINE OOS\n"+reports["overall"].round(4).to_string(index=False))
    for c in ("direction_state","volatility_state","breadth_state","dispersion_state","agreement_state"):
        print("\n"+c.upper()+"\n"+(reports[c].round(4).to_string(index=False) if not reports[c].empty else "No data."))
    print("\nResearch only: production scoring, weights, challenger logic, and live trading were NOT changed.")
    return {"observations":len(matched),"trading_dates":int(matched.trade_date.nunique()),"evaluated_days":len(evaluated),"evaluated":evaluated,"reports":reports}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",type=Path,default=DEFAULT_DB); p.add_argument("--train-days",type=int,default=120); p.add_argument("--test-days",type=int,default=20); a=p.parse_args(); analyze(a.db,Config(train_days=a.train_days,test_days=a.test_days))

if __name__=="__main__": main()
