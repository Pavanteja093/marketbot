# Track C2.1 Integration

Copy `research/regime_aware_walk_forward.py` and `research/candidate_gate.py`
into the MarketBot `research/` directory.

Copy the test into `tests/`.

Compile:

```powershell
python -m py_compile research/regime_aware_walk_forward.py
python -m py_compile research/candidate_gate.py
python -m py_compile tests/test_regime_aware_c21.py
```

Run tests:

```powershell
python -m tests.test_regime_aware_c21
```

Run the research:

```powershell
python -m research.regime_aware_walk_forward
```

Optional:

```powershell
python -m research.regime_aware_walk_forward --train-days 120 --test-days 20
```

Expected artifact files:

- `research/artifacts/regime_aware_c21_walk_forward.csv`
- `research/artifacts/regime_aware_c21_factor_fits.csv`
- `research/artifacts/regime_aware_c21_summary.json`

Do NOT modify production scoring.

## Leakage-control rule

The test-window regime is never selected by majority vote or by inspecting
future test dates.

For every test date:

1. NIFTY regime is derived from NIFTY data through that date.
2. The matching regime's weights are fitted using training data only.
3. The test day's stocks are scored.
4. Top/bottom quintile performance is measured for that day.

This is the required research protocol.
