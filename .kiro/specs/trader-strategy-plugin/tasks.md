# Implementation Plan: Trader Strategy Plugin System

## Overview

This implementation plan transforms the existing hardcoded MA cross trading system into a pluggable strategy architecture. The approach maintains backward compatibility while adding new strategies (BB Squeeze, Volume Breakout) and fixing critical go/no-go issues in paper mode. Each task builds incrementally, ensuring the system remains functional throughout development.

## Tasks

- [ ] 1. Create strategy plugin foundation
  - [x] 1.1 Implement Strategy Protocol interface and StrategyResult dataclass
    - Create trader/strategies/base.py with Strategy Protocol and StrategyResult
    - Define compute method signature and property requirements
    - Add type hints and documentation
    - _Requirements: 1.5, 1.6_

  - [ ] 1.2 Write property test for Strategy interface compliance
    - **Property 3: Strategy Interface Compliance**
    - **Validates: Requirements 1.5, 1.6**

  - [x] 1.3 Implement Strategy Registry core functionality
    - Create trader/strategies/registry.py with StrategyRegistry class
    - Implement get_strategy, list_strategies, resolve_strategy methods
    - Add StrategyInfo dataclass for metadata
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 1.4 Write property tests for Strategy Registry interface
    - **Property 1: Strategy Registry Interface Completeness**
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [ ] 2. Implement core trading strategies
  - [x] 2.1 Refactor existing MA cross strategy to use new interface
    - Update trader/strategies/ma_cross.py to implement Strategy Protocol
    - Convert calculate_ma_cross_signal to compute method
    - Add parameter schema and metadata properties
    - _Requirements: 2.3, 7.2_

  - [ ] 2.2 Write unit tests for MA cross strategy backward compatibility
    - Test that new implementation produces same results as legacy
    - Test parameter configuration and edge cases
    - _Requirements: 2.3, 7.2_

  - [x] 2.3 Implement BB Squeeze strategy
    - Create trader/strategies/bb_squeeze.py with Bollinger Band squeeze logic
    - Implement volatility expansion detection algorithm
    - Add configurable parameters (bb_period, bb_std, squeeze_threshold)
    - Ensure no volume data requirements
    - _Requirements: 2.1, 2.4_

  - [ ] 2.4 Write property test for BB Squeeze volume independence
    - **Property 5: Volume Independence for BB Squeeze**
    - **Validates: Requirements 2.4**

  - [x] 2.5 Implement Breakout Volume strategy
    - Create trader/strategies/breakout_volume.py with range breakout logic
    - Implement volume filter validation
    - Add configurable parameters (lookback_period, volume_threshold)
    - Mark as requiring volume data
    - _Requirements: 2.2_

  - [ ] 2.6 Write property test for volume fallback logic
    - **Property 2: Volume Fallback Consistency**
    - **Validates: Requirements 1.4, 2.5**

- [ ] 3. Checkpoint - Ensure strategy implementations work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Integrate strategies with registry system
  - [x] 4.1 Register all strategies in registry
    - Update trader/strategies/__init__.py to export registry
    - Register ma_cross, bb_squeeze, breakout_volume strategies
    - Set bb_squeeze as default strategy
    - _Requirements: 2.6, 6.6, 7.1_

  - [ ] 4.2 Write property test for strategy availability
    - **Property 4: Strategy Implementation Availability**
    - **Validates: Requirements 2.1, 2.2, 2.3, 7.2**

  - [x] 4.3 Implement volume fallback resolution logic
    - Add resolve_strategy method with DataFrame analysis
    - Implement automatic fallback to bb_squeeze when volume missing
    - Add logging for fallback events
    - _Requirements: 1.4, 2.5_

  - [ ] 4.4 Write property test for default strategy resolution
    - **Property 6: Default Strategy Resolution**
    - **Validates: Requirements 2.6, 3.4, 7.1**

- [ ] 5. Update entry points for strategy selection
  - [x] 5.1 Update run_paper_sim.py for strategy support
    - Add --strategy CLI argument parsing
    - Add TRADER_STRATEGY environment variable support
    - Integrate with strategy registry for strategy selection
    - Replace direct MA cross calls with registry-based strategy execution
    - _Requirements: 3.1_

  - [ ] 5.2 Update run_backtest_multi_assets.py for strategy support
    - Add --strategy CLI argument parsing
    - Add TRADER_STRATEGY environment variable support
    - Integrate with strategy registry for strategy selection
    - Replace direct MA cross calls with registry-based strategy execution
    - _Requirements: 3.2_

  - [ ] 5.3 Update run_live_trade.py for strategy support
    - Add --strategy CLI argument parsing
    - Add TRADER_STRATEGY environment variable support
    - Integrate with strategy registry for strategy selection
    - Replace direct MA cross calls with registry-based strategy execution
    - _Requirements: 3.3_

  - [ ] 5.4 Write property test for universal entry point strategy support
    - **Property 7: Universal Entry Point Strategy Support**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**

- [ ] 6. Enhance signal output with strategy metadata
  - [ ] 6.1 Extend signals_latest.json output format
    - Update trader/ml/pipeline.py to include strategy metadata
    - Add strategy_id, signal, reasons, entry, stop, confidence fields
    - Maintain backward compatibility with existing fields
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 7.5_

  - [ ] 6.2 Write property test for enhanced signal output completeness
    - **Property 8: Enhanced Signal Output Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 7.5**

  - [ ] 6.3 Update chart generation to display entry/stop levels
    - Modify trader/ml/viz.py to draw horizontal lines for entry/stop levels
    - Handle cases where entry/stop levels are None
    - _Requirements: 4.7_

- [ ] 7. Fix go/no-go risk guard for paper mode
  - [x] 7.1 Update go_nogo.py risk guard logic for paper mode
    - Modify risk_guard check to treat missing live_summary_latest.txt as PASS in paper mode
    - Handle risk_guard values of SKIP/missing as PASS in paper mode
    - Only FAIL when risk_guard explicitly contains FAIL in paper mode
    - Preserve existing logic for testnet/live modes
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 7.2 Write property tests for paper mode risk guard handling
    - **Property 9: Paper Mode Risk Guard Tolerance**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.5**

  - [ ] 7.3 Write property test for non-paper mode risk guard preservation
    - **Property 10: Non-Paper Mode Risk Guard Preservation**
    - **Validates: Requirements 5.4**

- [ ] 8. Implement configurable output directory support
  - [x] 8.1 Update configuration system for TRADER_REPORTS_DIR
    - Modify trader/config.py to handle TRADER_REPORTS_DIR environment variable
    - Update all file output paths to use configurable reports directory
    - Default to trader/reports when TRADER_REPORTS_DIR not specified
    - _Requirements: 6.1, 6.2_

  - [x] 8.2 Update all output file generation to use configurable directory
    - Update paper_trades_history.csv output path
    - Update signals_latest.json output path
    - Update signals_chart_latest.png output path
    - Update live_summary_latest.txt output path
    - _Requirements: 6.3, 6.4, 6.5, 6.6_

  - [ ] 8.3 Write property test for configurable output directory handling
    - **Property 11: Configurable Output Directory Handling**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**

- [ ] 9. Add strategy parameter configuration support
  - [ ] 9.1 Extend configuration system for strategy parameters
    - Add strategy_id and strategy_params fields to TraderConfig
    - Support TRADER_STRATEGY and TRADER_STRATEGY_PARAMS environment variables
    - Add parameter validation using strategy schemas
    - _Requirements: 8.4, 8.5_

  - [ ] 9.2 Update entry points to accept strategy parameters
    - Add CLI arguments for strategy parameters in all entry points
    - Parse and validate parameters against strategy schemas
    - Pass parameters to strategy compute methods
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

  - [ ] 9.3 Write property test for strategy parameter configuration
    - **Property 13: Strategy Parameter Configuration**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

- [ ] 10. Ensure backward compatibility
  - [ ] 10.1 Verify existing CLI interfaces work unchanged
    - Test all existing CLI commands without strategy parameters
    - Ensure default behavior matches previous system
    - Validate configuration file compatibility
    - _Requirements: 7.3, 7.4_

  - [ ] 10.2 Write property test for backward compatibility preservation
    - **Property 12: Backward Compatibility Preservation**
    - **Validates: Requirements 7.3, 7.4**

- [ ] 11. Final integration and testing
  - [ ] 11.1 Integration testing across all entry points
    - Test strategy switching across paper, backtest, and live modes
    - Verify signal output consistency
    - Test go/no-go system in all modes
    - _Requirements: 3.5_

  - [ ] 11.2 Write integration tests for end-to-end workflows
    - Test complete trading simulation with each strategy
    - Test cross-entry point consistency
    - Test file system integration and output generation

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive implementation with full testing coverage
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation maintains backward compatibility throughout development
- Strategy plugin system enables easy addition of new strategies in the future