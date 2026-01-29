# MPX3 Application File Inventory

**Generated:** 2026-01-29 12:35:00
**Purpose:** Complete listing of all files that touch the trading application

---

## Trading Apps (trading_app/)

### Core Applications
- `trading_app/app_canonical.py` - Main production trading app
- `trading_app/app_simple.py` - Simplified trading interface
- `trading_app/app_trading_terminal.py` - Advanced terminal interface
- `trading_app/app_cli.py` - Command-line interface
- `trading_app/app_mobile.py` - Mobile app interface
- `trading_app/app_research_lab.py` - Research and backtesting

### Configuration & Bootstrap
- `trading_app/config.py` - **CRITICAL** - Strategy configs, ORB filters
- `trading_app/db_bootstrap.py` - Database initialization
- `trading_app/db_health_check.py` - **CRITICAL** - WAL corruption auto-fix
- `trading_app/cloud_mode.py` - Cloud/local mode switching

### Data Layer
- `trading_app/data_loader.py` - **CRITICAL** - Loads bars_1m, daily_features
- `trading_app/data_bridge.py` - Data access abstraction
- `trading_app/data_quality_monitor.py` - Data validation

### Strategy & Execution
- `trading_app/setup_detector.py` - **CRITICAL** - Detects ORB setups
- `trading_app/strategy_engine.py` - **CRITICAL** - Strategy evaluation
- `trading_app/strategy_discovery.py` - New strategy discovery
- `trading_app/strategy_evaluation.py` - Strategy backtesting
- `trading_app/strategy_recommender.py` - AI recommendations
- `trading_app/risk_engine.py` - Position sizing
- `trading_app/risk_manager.py` - Risk limits
- `trading_app/rule_engine.py` - Trading rule enforcement
- `trading_app/directional_bias.py` - Market bias detection

### Scanning & Detection
- `trading_app/market_scanner.py` - Multi-setup scanner
- `trading_app/live_scanner.py` - Real-time scanning
- `trading_app/setup_scanner.py` - Setup detection
- `trading_app/experimental_scanner.py` - Experimental strategy scanner
- `trading_app/edge_pipeline.py` - Edge discovery pipeline

### UI Components
- `trading_app/professional_ui.py` - Professional UI components
- `trading_app/terminal_components.py` - Terminal UI widgets
- `trading_app/terminal_theme.py` - Theme configuration
- `trading_app/mobile_ui.py` - Mobile UI components
- `trading_app/enhanced_charting.py` - Advanced charts
- `trading_app/live_chart_builder.py` - Real-time chart generation
- `trading_app/orb_0030_visual.py` - Night session visualization
- `trading_app/csv_chart_analyzer.py` - CSV chart analysis

### AI & Intelligence
- `trading_app/ai_assistant.py` - AI trading assistant
- `trading_app/ai_chat.py` - Chat interface
- `trading_app/ai_guard.py` - AI safety checks
- `trading_app/ai_memory.py` - AI memory system
- `trading_app/memory.py` - Trading memory
- `trading_app/memory_integration.py` - Memory system integration
- `trading_app/market_intelligence.py` - Market analysis
- `trading_app/render_intelligence.py` - Intelligent rendering
- `trading_app/chart_analyzer.py` - Chart pattern analysis

### Monitoring & Tracking
- `trading_app/position_tracker.py` - Active position tracking
- `trading_app/edge_tracker.py` - Edge performance tracking
- `trading_app/drift_monitor.py` - Strategy drift detection
- `trading_app/market_hours_monitor.py` - Market hours tracking
- `trading_app/time_decay_engine.py` - Time decay analysis
- `trading_app/drawdown_engine.py` - Drawdown tracking
- `trading_app/alert_system.py` - Alert notifications
- `trading_app/experimental_alerts_ui.py` - Experimental alerts

### Edge Discovery & Research
- `trading_app/edge_candidates_ui.py` - Edge candidate display
- `trading_app/edge_candidate_utils.py` - Edge utilities
- `trading_app/edge_import.py` - Import edges from research
- `trading_app/edge_memory_bridge.py` - Edge memory integration
- `trading_app/edge_utils.py` - Edge helper functions
- `trading_app/research_runner.py` - Research execution
- `trading_app/research_workbench.py` - Research environment
- `trading_app/ml_dashboard.py` - Machine learning dashboard

### Integration & External
- `trading_app/tradovate_integration.py` - Tradovate broker integration
- `trading_app/scheduled_update.py` - Scheduled tasks
- `trading_app/session_timing_helper.py` - Session timing utilities
- `trading_app/utils.py` - General utilities
- `trading_app/canonical.py` - Canonical implementations
- `trading_app/error_logger.py` - Error logging

### Testing
- `trading_app/test_app_components.py` - Component tests
- `trading_app/test_database_connections.py` - DB connection tests
- `trading_app/test_dual_instruments.py` - Multi-instrument tests
- `trading_app/test_validation_comprehensive.py` - Validation tests

---

## Data Pipeline (pipeline/)

### Backfill Scripts
- `pipeline/backfill_databento_continuous.py` - **CRITICAL** - Databento backfill
- `pipeline/backfill_range.py` - **CRITICAL** - ProjectX backfill
- `pipeline/backfill_databento_continuous_mpl.py` - MPL backfill
- `pipeline/backfill_similarity_fingerprints.py` - Fingerprint backfill

### Feature Building
- `pipeline/build_daily_features.py` - **CRITICAL** - Builds daily_features table
- `pipeline/build_5m.py` - Builds 5-minute bars from 1-minute

### Database Management
- `pipeline/init_db.py` - **CRITICAL** - Initialize database schema
- `pipeline/check_db.py` - Database integrity checks
- `pipeline/validate_data.py` - Data validation
- `pipeline/wipe_mgc.py` - Wipe MGC data
- `pipeline/wipe_mpl.py` - Wipe MPL data
- `pipeline/delete_v2_table.py` - Delete obsolete tables
- `pipeline/fix_foreign_key.py` - Fix FK constraints

### Setup & Metrics
- `pipeline/load_validated_setups.py` - Load validated strategies
- `pipeline/populate_tradeable_metrics.py` - Calculate metrics
- `pipeline/populate_validated_trades.py` - Populate trade outcomes
- `pipeline/populate_validated_trades_with_filter.py` - Filtered trades
- `pipeline/create_edge_registry.py` - Edge registry creation

### Memory & Walk-Forward
- `pipeline/init_memory_tables.py` - Initialize memory tables
- `pipeline/walkforward_config.py` - Walk-forward configuration

### Migrations
- `pipeline/migrate_add_edge_candidates.py` - Edge candidates migration
- `pipeline/migrate_add_reproducibility_fields.py` - Reproducibility migration

### Cost Model
- `pipeline/cost_model.py` - **CRITICAL** - MGC cost specifications

### Inspection Tools
- `pipeline/inspect_dbn.py` - Inspect DBN files
- `pipeline/check_dbn_symbols.py` - Check symbols in DBN

---

## Strategy Engine (strategies/)

- `strategies/execution_engine.py` - **CRITICAL** - ORB execution engine
- `strategies/execution_modes.py` - Execution mode definitions
- `strategies/test_app_sync.py` - **CRITICAL** - Config/DB sync test
- `strategies/archive_strategy.py` - Strategy archiving
- `strategies/populate_realized_from_phase1.py` - Realized metrics
- `strategies/populate_realized_metrics.py` - Metrics population

---

## Maintenance Scripts (scripts/maintenance/)

- `scripts/maintenance/update_market_data_projectx.py` - **CRITICAL** - Auto-update (ProjectX)
- `scripts/maintenance/update_market_data.py` - Auto-update (Databento - broken)
- `scripts/maintenance/test_update_script.py` - Update script tests
- `scripts/maintenance/recover_wal.py` - WAL corruption recovery

---

## Critical File Dependencies

### Database-Dependent Files
**These files directly query data/db/gold.db:**
1. `trading_app/data_loader.py` - Loads bars_1m, daily_features
2. `trading_app/setup_detector.py` - Queries validated_setups
3. `trading_app/strategy_engine.py` - Reads validated_setups
4. `pipeline/build_daily_features.py` - Writes to daily_features
5. `pipeline/backfill_range.py` - Writes to bars_1m
6. `scripts/maintenance/update_market_data_projectx.py` - Queries MAX timestamps

### Config-Dependent Files
**These files import trading_app/config.py:**
1. `trading_app/app_canonical.py`
2. `trading_app/app_simple.py`
3. `trading_app/app_trading_terminal.py`
4. `trading_app/data_loader.py`
5. `trading_app/setup_detector.py`
6. `trading_app/strategy_engine.py`

### Health Check Dependencies
**These files use db_health_check.py:**
1. `trading_app/app_canonical.py` - Startup check
2. `scripts/maintenance/update_market_data_projectx.py` - Pre-update check

---

## Data Flow Summary

```
ProjectX API
    ↓
backfill_range.py → bars_1m (INSERT OR REPLACE)
    ↓
build_daily_features.py → daily_features (INSERT OR REPLACE)
    ↓
data_loader.py → trading apps
    ↓
setup_detector.py + strategy_engine.py → UI display
```

---

## Files Modified by updatre.txt Implementation

**Phase 2 (current):**
- `scripts/maintenance/update_market_data_projectx.py` (modify feature build logic)

**Phase 3 (planned):**
- `scripts/maintenance/update_market_data_projectx.py` (add verification checks)
- Possibly new: `scripts/maintenance/verify_data_integrity.py`

**Phase 4 (planned):**
- No file changes (verification only)

**Phase 5 (planned):**
- `scripts/maintenance/README.md` (update docs)
- Possibly: `scripts/maintenance/test_update_script.py` (add verification tests)

---

## Total File Count

- **Trading App:** 69 files
- **Pipeline:** 25 files
- **Strategies:** 6 files
- **Maintenance:** 4 files

**Total:** 104 Python files
