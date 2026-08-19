# MarketBot Repair Bundle

This bundle contains source-level repairs grounded in the production output and
the supplied source snapshot.

Repairs included:
1. factor_library joins now use canonical `index_name` instead of `symbol`.
2. live_market_collector system_status writing adapts to the actual table columns.
3. analytics.stock_scoring compatibility shim delegates to Stock Scoring V2.
4. market_regime legacy `get_market_regime()` API restored.
5. sector_strength compatibility API added.
6. capital_flow `.resolvpythone()` typo fixed.
7. research.prediction_history compatibility stage added.
8. learning.learning_engine data-gated compatibility stage added.
9. research.feature_importance compatibility implementation added.
10. VERIFY_REPAIR.ps1 performs read-only syntax/import/stage checks.

IMPORTANT:
- Do not replace unrelated repository files with this bundle blindly.
- Back up the working tree/database before applying it.
- The compatibility stages deliberately do NOT fabricate learning or prediction
  outcomes. If the database is not ready, they report DATA_GATED.
- After verification, run the normal production command and inspect every
  FAILED/WARNING line before promoting anything to production.
