from __future__ import annotations

import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from research.marketbot_health_monitor import (
    build_report,
    connect_read_only,
    run,
)


def create_db(path: Path) -> None:
    conn = sqlite3.connect(path)

    conn.executescript(
        """
        CREATE TABLE indices_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            index_name TEXT,
            open REAL,
            high REAL,
            low REAL,
            previous_close REAL,
            close REAL,
            price_change REAL,
            change_pct REAL
        );

        CREATE TABLE stocks_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            symbol TEXT,
            open REAL,
            high REAL,
            low REAL,
            previous_close REAL,
            close REAL,
            price_change REAL,
            change_pct REAL,
            volume INTEGER
        );

        CREATE TABLE fii_dii_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            fii_buy REAL,
            fii_sell REAL,
            fii_net REAL,
            dii_buy REAL,
            dii_sell REAL,
            dii_net REAL
        );

        CREATE TABLE factor_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            index_name TEXT,
            sector TEXT,
            change_pct REAL,
            sector_strength REAL,
            position_pct REAL,
            total_score REAL,
            intelligence_score REAL
        );

        CREATE TABLE signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            index_name TEXT,
            sector TEXT,
            score REAL,
            rank INTEGER
        );

        CREATE TABLE signal_history_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            index_name TEXT,
            sector TEXT,
            intelligence_score REAL,
            rank INTEGER
        );

        CREATE TABLE market_regime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            trend REAL,
            volatility REAL,
            breadth REAL,
            institutional_flow REAL,
            sector_rotation REAL,
            regime_score REAL,
            market_regime TEXT,
            confidence REAL
        );

        CREATE TABLE market_scenario_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE NOT NULL,
            index_name TEXT NOT NULL,
            primary_scenario TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL
        );

        CREATE TABLE options_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE,
            index_name TEXT,
            spot_price REAL,
            pcr REAL,
            max_pain INTEGER,
            atm_strike INTEGER,
            highest_call_oi INTEGER,
            highest_put_oi INTEGER,
            market_bias TEXT
        );

        CREATE TABLE indices_intraday (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            index_name TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL
        );

        CREATE TABLE option_chain_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_time DATETIME NOT NULL,
            symbol TEXT NOT NULL,
            expiry DATE NOT NULL,
            strike REAL NOT NULL
        );
        """
    )

    conn.execute(
        """
        INSERT INTO indices_daily
        (trade_date, index_name, close)
        VALUES ('2026-08-10', 'NIFTY50', 25000)
        """
    )

    conn.execute(
        """
        INSERT INTO stocks_daily
        (trade_date, symbol, close)
        VALUES ('2026-08-10', 'RELIANCE.NS', 1400)
        """
    )

    conn.commit()
    conn.close()


class MarketBotHealthMonitorTests(unittest.TestCase):

    def test_healthy_database(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "market.db"
            create_db(db)

            conn = sqlite3.connect(db)
            rows, reference, overall = build_report(conn)
            conn.close()

            self.assertEqual(reference, "2026-08-10")
            self.assertIn(
                overall,
                {"HEALTHY", "WARNING", "CRITICAL"},
            )
            self.assertTrue(rows)

    def test_missing_required_table_is_critical(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "market.db"
            create_db(db)

            conn = sqlite3.connect(db)
            conn.execute("DROP TABLE stocks_daily")
            conn.commit()

            rows, _, overall = build_report(conn)
            conn.close()

            stocks = next(
                row for row in rows
                if row.table_name == "stocks_daily"
            )

            self.assertFalse(stocks.exists)
            self.assertEqual(stocks.status, "CRITICAL")
            self.assertEqual(overall, "CRITICAL")

    def test_empty_required_table_is_critical(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "market.db"
            create_db(db)

            conn = sqlite3.connect(db)
            conn.execute("DELETE FROM stocks_daily")
            conn.commit()

            rows, _, overall = build_report(conn)
            conn.close()

            stocks = next(
                row for row in rows
                if row.table_name == "stocks_daily"
            )

            self.assertEqual(stocks.row_count, 0)
            self.assertEqual(stocks.status, "CRITICAL")
            self.assertEqual(overall, "CRITICAL")

    def test_duplicate_key_is_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "market.db"
            create_db(db)

            conn = sqlite3.connect(db)

            conn.execute(
                """
                INSERT INTO stocks_daily
                (trade_date, symbol, close)
                VALUES ('2026-08-10', 'RELIANCE.NS', 1410)
                """
            )

            conn.commit()

            rows, _, overall = build_report(conn)
            conn.close()

            stocks = next(
                row for row in rows
                if row.table_name == "stocks_daily"
            )

            self.assertGreater(stocks.duplicate_groups, 0)
            self.assertEqual(stocks.status, "WARNING")
            

    def test_reference_date_is_indices_daily(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "market.db"
            create_db(db)

            conn = sqlite3.connect(db)

            conn.execute(
                """
                INSERT INTO indices_daily
                (trade_date, index_name, close)
                VALUES ('2026-08-11', 'BANKNIFTY', 55000)
                """
            )

            conn.commit()

            _, reference, _ = build_report(conn)
            conn.close()

            self.assertEqual(reference, "2026-08-11")

    def test_stale_table_is_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "market.db"
            create_db(db)

            conn = sqlite3.connect(db)

            conn.execute(
                """
                INSERT INTO indices_daily
                (trade_date, index_name, close)
                VALUES ('2026-08-11', 'BANKNIFTY', 55000)
                """
            )

            conn.commit()

            rows, _, _ = build_report(conn)
            conn.close()

            stocks = next(
                row for row in rows
                if row.table_name == "stocks_daily"
            )

            self.assertEqual(stocks.status, "WARNING")

    def test_output_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)

            db = directory / "market.db"
            output = directory / "health.csv"

            create_db(db)

            result = run(
                db_path=db,
                output_path=output,
            )

            self.assertTrue(output.exists())
            self.assertEqual(
                result["output_path"],
                output,
            )

            with output.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))

            self.assertTrue(rows)
            self.assertIn("table_name", rows[0])
            self.assertIn("status", rows[0])

    def test_database_is_opened_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "market.db"
            create_db(db)

            conn = connect_read_only(db)

            with self.assertRaises(sqlite3.OperationalError):
                conn.execute(
                    "INSERT INTO indices_daily "
                    "(trade_date, index_name, close) "
                    "VALUES ('2026-08-11', 'TEST', 1)"
                )

            conn.close()


if __name__ == "__main__":
    unittest.main()