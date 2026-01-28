# Design
- trader/strategies/registry.py : name->strategy factory
- trader/strategies/*.py        : concrete strategies
- trader/patterns/*.py          : shared indicators (bb width, volume surge)
- config: TRADER_STRATEGY, TRADER_STRATEGY_PARAMS_JSON (optional)
- CLI: --strategy added to run_paper_sim/run_live_trade/run_backtest_multi_assets
