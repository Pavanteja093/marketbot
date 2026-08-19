$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "=== MARKETBOT REPAIR VERIFICATION ==="

python -m py_compile `
  analytics\factor_builder.py `
  analytics\factor_history_builder.py `
  analytics\market_regime.py `
  analytics\capital_flow.py `
  analytics\live_market_collector.py `
  analytics\stock_scoring.py `
  analytics\sector_strength.py `
  research\alpha_signal_v2_backtest.py `
  research\volume_expansion_research.py `
  research\volume_position_combo.py `
  research\prediction_history.py `
  research\feature_importance.py `
  learning\learning_engine.py

Write-Host "`n=== COMPATIBILITY IMPORT TEST ==="
python -c "import analytics.stock_scoring; import analytics.market_regime; import analytics.sector_strength; import research.prediction_history; import research.feature_importance; import learning.learning_engine; print('IMPORT TEST: PASS')"

Write-Host "`n=== PREDICTION HISTORY STAGE ==="
python -m research.prediction_history

Write-Host "`n=== LEARNING STAGE ==="
python -m learning.learning_engine

Write-Host "`n=== FACTOR-LIBRARY QUERY TESTS ==="
python -c "import sqlite3; c=sqlite3.connect('market_intelligence.db'); print(c.execute(""PRAGMA table_info(factor_library)"").fetchall()); c.close()"

Write-Host "`n=== DONE ==="


