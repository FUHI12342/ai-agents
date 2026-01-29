# Requirements Document

## Introduction

The Trader Strategy Plugin system transforms the existing trading system from a hardcoded MA cross strategy into a pluggable architecture that supports multiple trading strategies. The system maintains backward compatibility while adding new strategies (BB Squeeze, Volume Breakout) and fixing critical go/no-go risk guard issues in paper mode. The plugin system enables strategy switching across all trading modes (paper, backtest, live) through CLI/ENV configuration.

## Glossary

- **Strategy_Plugin**: A modular trading strategy implementation that follows the Strategy interface
- **Strategy_Registry**: Central registry that manages strategy discovery, instantiation, and fallback logic
- **Strategy_Interface**: Protocol defining the contract for all trading strategies (compute method, metadata)
- **Strategy_Result**: Data structure containing signal output (signal, entry, stop, confidence, reasons)
- **Signal_Output**: Enhanced JSON and chart output containing strategy metadata and trade levels
- **Risk_Guard**: System component that validates trading readiness and risk limits
- **Go_Nogo_System**: Automated checklist system for live trading readiness validation
- **Volume_Fallback**: Automatic strategy downgrade when required volume data is unavailable
- **Entry_Point**: CLI scripts that execute trading operations (paper, backtest, live)
- **Reports_Directory**: Configurable output directory for trading reports and artifacts

## Requirements

### Requirement 1: Strategy Plugin Architecture

**User Story:** As a trading system developer, I want a pluggable strategy architecture, so that I can add new trading strategies without modifying core system components.

#### Acceptance Criteria

1. THE Strategy_Registry SHALL provide get_strategy(strategy_id) method that returns Strategy instances
2. THE Strategy_Registry SHALL provide list_strategies() method that returns strategy metadata including id, name, recommended flag, volume requirements, and parameter schema
3. THE Strategy_Registry SHALL provide resolve_strategy(strategy_id, df) method that handles volume fallback logic
4. WHEN a strategy requires volume data and volume is unavailable, THE Strategy_Registry SHALL automatically fallback to bb_squeeze strategy
5. THE Strategy_Interface SHALL define compute(df, **params) method that returns StrategyResult objects
6. THE StrategyResult SHALL contain signal, entry, stop, confidence, and meta fields with reasons

### Requirement 2: Strategy Implementation Support

**User Story:** As a trader, I want access to multiple trading strategies including BB Squeeze and Volume Breakout, so that I can choose the most appropriate strategy for market conditions.

#### Acceptance Criteria

1. THE System SHALL implement bb_squeeze strategy using Bollinger Band squeeze and volatility expansion patterns
2. THE System SHALL implement breakout_volume strategy using range breakout with volume filter validation
3. THE System SHALL maintain existing ma_cross strategy with backward compatibility
4. THE bb_squeeze strategy SHALL work without volume data requirements
5. THE breakout_volume strategy SHALL require volume data and fallback to bb_squeeze when volume is missing
6. THE default strategy SHALL be bb_squeeze when no strategy_id is specified

### Requirement 3: Universal Strategy Selection

**User Story:** As a trading system operator, I want consistent strategy selection across all trading modes, so that I can use the same strategy configuration for paper trading, backtesting, and live trading.

#### Acceptance Criteria

1. THE run_paper_sim entry point SHALL accept --strategy CLI argument and TRADER_STRATEGY environment variable
2. THE run_backtest_multi_assets entry point SHALL accept --strategy CLI argument and TRADER_STRATEGY environment variable  
3. THE run_live_trade entry point SHALL accept --strategy CLI argument and TRADER_STRATEGY environment variable
4. WHEN no strategy is specified, THE System SHALL use bb_squeeze as the default strategy
5. THE strategy selection mechanism SHALL work identically across all three entry points

### Requirement 4: Enhanced Signal Output

**User Story:** As a trading analyst, I want detailed signal output with strategy metadata and trade levels, so that I can analyze strategy performance and decision reasoning.

#### Acceptance Criteria

1. THE signals_latest.json output SHALL include strategy_id field identifying the active strategy
2. THE signals_latest.json output SHALL include signal field with trade direction
3. THE signals_latest.json output SHALL include reasons field with strategy decision rationale
4. THE signals_latest.json output SHALL include entry field with recommended entry price
5. THE signals_latest.json output SHALL include stop field with stop loss level
6. THE signals_latest.json output SHALL include confidence field with signal strength rating
7. THE signals_chart_latest.png output SHALL display entry and stop levels as horizontal lines when available

### Requirement 5: Go/No-Go Risk Guard Fix

**User Story:** As a trading system operator, I want reliable go/no-go checks in paper mode, so that paper trading operations don't fail due to missing live summary files.

#### Acceptance Criteria

1. WHEN trader_mode is paper, THE Go_Nogo_System SHALL treat missing live_summary_latest.txt as PASS condition
2. WHEN trader_mode is paper, THE Go_Nogo_System SHALL treat risk_guard field as PASS when file exists but risk_guard is SKIP
3. WHEN trader_mode is paper, THE Go_Nogo_System SHALL treat risk_guard field as PASS when file exists but risk_guard is missing
4. WHEN trader_mode is testnet or live, THE Go_Nogo_System SHALL maintain existing risk_guard validation logic
5. THE risk_guard check SHALL only FAIL in paper mode when live_summary_latest.txt explicitly contains risk_guard: FAIL

### Requirement 6: Clean Repository Output

**User Story:** As a developer, I want trading execution artifacts stored outside the repository, so that git status remains clean during trading operations.

#### Acceptance Criteria

1. THE System SHALL use TRADER_REPORTS_DIR environment variable for output file location when specified
2. WHEN TRADER_REPORTS_DIR is not specified, THE System SHALL default to trader/reports directory
3. THE paper_trades_history.csv file SHALL be written to the configured reports directory
4. THE signals_latest.json file SHALL be written to the configured reports directory
5. THE signals_chart_latest.png file SHALL be written to the configured reports directory
6. THE live_summary_latest.txt file SHALL be written to the configured reports directory

### Requirement 7: Backward Compatibility

**User Story:** As an existing trading system user, I want the new plugin system to maintain existing functionality, so that current trading operations continue without disruption.

#### Acceptance Criteria

1. WHEN no strategy_id is specified, THE System SHALL execute bb_squeeze strategy maintaining equivalent behavior to previous default
2. THE existing MA cross strategy SHALL remain available through strategy_id "ma_cross"
3. THE existing CLI interfaces SHALL continue to work without modification for users not specifying strategy parameters
4. THE existing configuration files and environment variables SHALL continue to function unchanged
5. THE existing signal output format SHALL be extended but maintain backward compatibility with existing fields

### Requirement 8: Strategy Parameter Configuration

**User Story:** As a trading strategy developer, I want configurable strategy parameters, so that I can tune strategy behavior for different market conditions.

#### Acceptance Criteria

1. THE bb_squeeze strategy SHALL accept configurable Bollinger Band period and standard deviation parameters
2. THE breakout_volume strategy SHALL accept configurable lookback period and volume threshold parameters
3. THE ma_cross strategy SHALL accept configurable short and long moving average period parameters
4. THE Strategy_Registry SHALL provide parameter schema information for each strategy
5. THE entry points SHALL accept strategy parameters through CLI arguments or environment variables