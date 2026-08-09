# MarketBot Architecture

## 1. Overview

MarketBot is an automated quantitative research platform for the Indian stock market.

The workflow is:

Market Data
↓

Database

↓

Feature Engineering

↓

Analytics

↓

Research

↓

Learning

↓

Decision Engine

↓

Reporting

↓

Automation

---

## 2. Data Collection Layer

### Stocks Collector

Downloads OHLCV data.

Stores into:

- stocks_daily

Runs:

- Daily

---

### Indices Collector

Downloads NIFTY, SENSEX, BANKNIFTY, FINNIFTY.

Stores into:

- indices_daily

---

### Option Chain Collector

Downloads

- Option Chain
- PCR
- OI
- IV
- Max Pain

Stores into:

- option_chain_history

---

### FII/DII Collector

Downloads institutional flow.

Stores into:

- fii_dii_daily

---

## 3. Database Layer

Main database

market_intelligence.db

Main tables

- stocks_daily
- indices_daily
- option_chain_history
- factor_history
- prediction_history
- signal_history
- signal_history_v2
- factor_library
- forward_returns

---

## 4. Analytics Layer

Responsible for

- feature engineering
- scoring
- confidence
- risk
- explainability
- portfolio
- recommendations

---

## 5. Research Layer

Responsible for

- factor validation
- walk-forward testing
- feature importance
- calibration
- regime analysis
- model comparison
- challenger evaluation

---

## 6. Learning Layer

Responsible for

- prediction validation
- adaptive weights
- model evolution
- learning statistics
- memory engine

---

## 7. Decision Layer

Combines

- Market Regime
- Confidence
- Risk
- Strategy
- Recommendation

into one final trading decision.

---

## 8. Automation Layer

Runs

run_daily_update.py

Responsibilities

- Data collection
- Synchronization
- Self repair
- Health checks
- Research
- Learning
- Reports

---

## 9. Reporting Layer

Generates

- Morning Report
- Daily Report
- Telegram Reports
- Power BI CSV

---

## 10. Future Roadmap

- Ensemble Models
- Reinforcement Learning
- Portfolio Optimizer
- Live Execution
- Broker Integration
- AI Market Commentary