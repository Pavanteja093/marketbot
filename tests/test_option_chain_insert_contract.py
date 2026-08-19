import importlib.util
import sqlite3
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def load_module():
    fake_upstox = types.ModuleType("upstox_client")
    class Configuration:
        def __init__(self): self.access_token = None
    class ApiClient:
        def __init__(self, configuration): pass
        def close(self): pass
    class OptionsApi:
        def __init__(self, client): pass
    fake_upstox.Configuration = Configuration
    fake_upstox.ApiClient = ApiClient
    fake_upstox.OptionsApi = OptionsApi

    fake_config = types.ModuleType("config.upstox_config")
    fake_config.ACCESS_TOKEN = "TEST"

    sys.modules["upstox_client"] = fake_upstox
    sys.modules["config.upstox_config"] = fake_config

    spec = importlib.util.spec_from_file_location(
        "option_chain_upstox_test_target",
        Path(__file__).with_name("option_chain_upstox.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OptionChainInsertContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def make_item(self):
        call_md = Obj(ltp=123.4, oi=1000, prev_oi=900, volume=500)
        put_md = Obj(ltp=98.7, oi=1200, prev_oi=1100, volume=600)
        call_g = Obj(iv=22.5, delta=0.51, gamma=0.001, theta=-2.1, vega=4.2, pop=68.0)
        put_g = Obj(iv=24.5, delta=-0.49, gamma=0.0012, theta=-2.4, vega=4.5, pop=64.0)
        return Obj(
            expiry=pd.Timestamp("2026-08-25"),
            strike_price=25000.0,
            call_options=Obj(market_data=call_md, option_greeks=call_g),
            put_options=Obj(market_data=put_md, option_greeks=put_g),
            pcr=1.2,
            underlying_spot_price=24950.0,
        )

    def test_row_matches_schema_contract(self):
        row = self.mod.build_option_row(
            self.make_item(), "NIFTY", "2026-08-18 14:00:00"
        )
        self.assertEqual(len(row), 26)
        self.assertEqual(len(self.mod.OPTION_CHAIN_COLUMNS), 26)
        self.assertEqual(self.mod.OPTION_CHAIN_INSERT_SQL.count("?"), 26)
        self.assertEqual(row[8], 100)
        self.assertEqual(row[9], 100)
        self.assertEqual(row[14], 22.5)
        self.assertEqual(row[25], 64.0)

    def test_row_inserts_into_real_option_chain_schema(self):
        real_db = Path("market_intelligence.db")
        conn = sqlite3.connect(":memory:")
        source = sqlite3.connect(real_db)
        schema = source.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='option_chain_history'"
        ).fetchone()[0]
        source.close()
        conn.execute(schema)

        row = self.mod.build_option_row(
            self.make_item(), "NIFTY", "2026-08-18 14:00:00"
        )
        conn.execute(self.mod.OPTION_CHAIN_INSERT_SQL, row)
        count = conn.execute("SELECT COUNT(*) FROM option_chain_history").fetchone()[0]
        self.assertEqual(count, 1)
        saved = conn.execute(
            "SELECT symbol, strike, call_iv, put_iv, call_theta, put_theta FROM option_chain_history"
        ).fetchone()
        self.assertEqual(saved, ("NIFTY", 25000.0, 22.5, 24.5, -2.1, -2.4))
        conn.close()

    def test_missing_greeks_are_allowed(self):
        item = self.make_item()
        item.call_options.option_greeks = None
        item.put_options.option_greeks = None
        row = self.mod.build_option_row(item, "NIFTY", "2026-08-18 14:00:00")
        self.assertEqual(len(row), 26)
        self.assertIsNone(row[14])
        self.assertIsNone(row[25])


if __name__ == "__main__":
    unittest.main(verbosity=2)
