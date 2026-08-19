import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.market_scenario_registry import (
    STANDARD_SCENARIOS,
    assign_scenario_ids,
    build_scenarios,
    classify_scenario,
    make_fingerprint,
    run,
)


class MarketScenarioRegistryTests(unittest.TestCase):

    def test_standard_scenarios_are_small_and_explicit(self):
        self.assertEqual(
            set(STANDARD_SCENARIOS),
            {
                "TREND_UP",
                "TREND_DOWN",
                "HIGH_VOL",
                "LOW_VOL",
                "FLAT",
                "CHOPPY",
            },
        )

    def test_trend_up_classification(self):
        self.assertEqual(
            classify_scenario(
                0.01,
                0.005,
                0.008,
                0.01,
            ),
            "TREND_UP",
        )

    def test_trend_down_classification(self):
        self.assertEqual(
            classify_scenario(
                -0.01,
                0.005,
                -0.008,
                0.01,
            ),
            "TREND_DOWN",
        )

    def test_high_vol_takes_priority(self):
        self.assertEqual(
            classify_scenario(
                0.01,
                0.02,
                0.01,
                0.02,
            ),
            "HIGH_VOL",
        )

    def test_flat_classification(self):
        self.assertEqual(
            classify_scenario(
                0.001,
                0.005,
                0.001,
                0.004,
            ),
            "FLAT",
        )

    def test_low_vol_classification(self):
        self.assertEqual(
            classify_scenario(
                0.003,
                0.004,
                0.003,
                0.007,
            ),
            "LOW_VOL",
        )

    def test_choppy_classification(self):
        self.assertEqual(
            classify_scenario(
                0.003,
                0.005,
                0.004,
                0.010,
            ),
            "CHOPPY",
        )

    def test_fingerprint_is_repeatable(self):
        a = make_fingerprint(
            "TREND_UP",
            "HIGH",
            "NORMAL",
            "HIGH",
            "NORMAL",
        )

        b = make_fingerprint(
            "TREND_UP",
            "HIGH",
            "NORMAL",
            "HIGH",
            "NORMAL",
        )

        self.assertEqual(a, b)

    def test_different_market_states_have_different_fingerprints(self):
        a = make_fingerprint(
            "TREND_UP",
            "HIGH",
            "NORMAL",
            "HIGH",
            "NORMAL",
        )

        b = make_fingerprint(
            "TREND_DOWN",
            "LOW",
            "HIGH",
            "HIGH",
            "HIGH",
        )

        self.assertNotEqual(a, b)

    def test_scenario_builder_creates_rows(self):
        dates = pd.date_range(
            "2025-01-01",
            periods=80,
            freq="D",
        )

        close = [
            100 + i * 0.5
            for i in range(80)
        ]

        df = pd.DataFrame(
            {
                "trade_date": dates,
                "index_name": "NIFTY50",
                "open": close,
                "high": [x + 1 for x in close],
                "low": [x - 1 for x in close],
                "close": close,
                "change_pct": 0.5,
            }
        )

        result = build_scenarios(df)

        self.assertEqual(
            len(result),
            80,
        )

        self.assertIn(
            "primary_scenario",
            result.columns,
        )

        self.assertIn(
            "fingerprint",
            result.columns,
        )

    def test_new_fingerprint_gets_unexplored_id(self):
        conn = sqlite3.connect(":memory:")

        conn.execute(
            """
            CREATE TABLE market_scenario_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date DATE,
                index_name TEXT,
                primary_scenario TEXT,
                scenario_id TEXT,
                fingerprint TEXT,
                trend REAL,
                volatility REAL,
                daily_return REAL,
                range_pct REAL
            )
            """
        )

        frame = pd.DataFrame(
            [
                {
                    "trade_date": pd.Timestamp("2025-01-01"),
                    "index_name": "NIFTY50",
                    "primary_scenario": "TREND_UP",
                    "fingerprint": "abc123",
                    "trend": 0.01,
                    "volatility": 0.01,
                    "daily_return": 0.01,
                    "range_pct": 0.01,
                }
            ]
        )

        result = assign_scenario_ids(
            conn,
            frame,
        )

        self.assertEqual(
            result.iloc[0]["scenario_id"],
            "UNEXPLORED_1",
        )

        conn.close()

    def test_same_fingerprint_reuses_id(self):
        conn = sqlite3.connect(":memory:")

        conn.execute(
            """
            CREATE TABLE market_scenario_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date DATE,
                index_name TEXT,
                primary_scenario TEXT,
                scenario_id TEXT,
                fingerprint TEXT
            )
            """
        )

        conn.execute(
            """
            INSERT INTO market_scenario_history
            (trade_date,index_name,primary_scenario,scenario_id,fingerprint)
            VALUES ('2025-01-01','NIFTY50','TREND_UP',
                    'UNEXPLORED_7','abc123')
            """
        )

        frame = pd.DataFrame(
            [
                {
                    "trade_date": pd.Timestamp("2025-01-02"),
                    "index_name": "NIFTY50",
                    "primary_scenario": "TREND_UP",
                    "fingerprint": "abc123",
                }
            ]
        )

        result = assign_scenario_ids(
            conn,
            frame,
        )

        self.assertEqual(
            result.iloc[0]["scenario_id"],
            "UNEXPLORED_7",
        )

        conn.close()

    def test_real_db_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"

            conn = sqlite3.connect(db)

            conn.execute(
                """
                CREATE TABLE indices_daily (
                    id INTEGER PRIMARY KEY,
                    trade_date DATE,
                    index_name TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    previous_close REAL,
                    close REAL,
                    price_change REAL,
                    change_pct REAL
                )
                """
            )

            dates = pd.date_range(
                "2025-01-01",
                periods=80,
                freq="D",
            )

            for i, date in enumerate(dates):
                close = 100 + i * 0.5

                conn.execute(
                    """
                    INSERT INTO indices_daily
                    (trade_date,index_name,open,high,low,
                     previous_close,close,price_change,change_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        date.strftime("%Y-%m-%d"),
                        "NIFTY50",
                        close,
                        close + 1,
                        close - 1,
                        close - 0.5,
                        close,
                        0.5,
                        0.5,
                    ),
                )

            conn.commit()
            conn.close()

            first = run(db)
            second = run(db)

            self.assertGreater(
                first["rows_inserted"],
                0,
            )

            self.assertEqual(
                second["rows_inserted"],
                0,
            )


if __name__ == "__main__":
    unittest.main()