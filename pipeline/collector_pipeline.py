from pipeline.collector_adapter import CollectorAdapter


def run():

    adapter = CollectorAdapter()

    adapter.register(
        "Stocks Collector",
        "data_collectors/stocks.py"
    )

    adapter.register(
        "Indices Collector",
        "data_collectors/indices.py"
    )

    adapter.register(
        "Option Chain Collector",
        "data_collectors/option_chain_upstox.py"
    )

    adapter.register(
        "FII DII Collector",
        "data_collectors/fii_dii.py"
    )

    adapter.run()