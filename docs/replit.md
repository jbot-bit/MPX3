# myprojectx Trading App

## Overview
A mobile-first trading application built with Streamlit for live trading decision support. Features swipeable cards, dark mode, and touch-optimized interface.

## Project Structure
- `trading_app/` - Main application code
  - `app_mobile.py` - Mobile app entry point
  - `app_trading_hub.py` - Desktop app entry point
  - `config.py` - Application configuration
  - `cloud_mode.py` - Cloud/MotherDuck database handling
  - `db_bootstrap.py` - Database table creation
- `config/.streamlit/` - Streamlit configuration
- `tools/` - Utility scripts
- `data/` - Data files (database gitignored)

## Running the App
The app runs on port 5000 via Streamlit:
```
streamlit run trading_app/app_mobile.py --server.port 5000 --server.address 0.0.0.0
```

## Environment Variables
Required secrets (stored in Replit Secrets):
- `MOTHERDUCK_TOKEN` - MotherDuck cloud database token
- `PROJECTX_USERNAME` - ProjectX API username
- `PROJECTX_API_KEY` - ProjectX API key
- `OPENAI_API_KEY` - OpenAI API key for AI chat

Environment variables:
- `CLOUD_MODE=1` - Enable cloud database mode
- `FORCE_LOCAL_DB=0` - Disable local database fallback
- `AI_PROVIDER=openai` - Use OpenAI for AI features

## Database
Uses DuckDB with MotherDuck for cloud hosting. The local 700MB database is not included in git - data is fetched from MotherDuck (`projectx_prod` database).

## Deployment
Configured for Replit autoscale deployment on port 5000.

## Research Workbench
Unified interface for strategy research and validation (`trading_app/research_workbench.py`):
- **Discovery Tab**: Scan for profitable ORB configurations with parameter sweeps
- **Pipeline Tab**: View and manage edge candidates through the workflow
- **Pipeline Dashboard**: Visual summary of candidates by status (Draft → Tested → Approved → Promoted)
- **One-click workflow**: Discover → Create Hypothesis → Run Backtest → Approve → Promote to Production

Key files:
- `trading_app/research_workbench.py` - Main unified UI
- `trading_app/strategy_discovery.py` - Discovery engine
- `trading_app/research_runner.py` - Automated backtesting
- `trading_app/edge_pipeline.py` - Candidate lifecycle management

## AI Provider Configuration
Supports both OpenAI and Anthropic. Set `AI_PROVIDER` environment variable:
- `AI_PROVIDER=openai` - Use OpenAI GPT-4o (default)
- `AI_PROVIDER=anthropic` - Use Claude

Files: `trading_app/ai_guard.py`, `trading_app/ai_assistant.py`

## Recent Changes (2026-01-24)
- **Replaced all stub/estimate logic with real data**:
  - ResearchRunner now uses orb_*_outcome (WIN/LOSS) and orb_*_r_multiple for actual R values
  - StrategyDiscovery now uses real outcomes from database
  - Removed all hardcoded win rate estimates
- Added Research Workbench with unified discovery/pipeline interface
- Added OpenAI support alongside Anthropic for AI chat
- Migrated from GitHub import
- Configured for Replit environment
- Set up MotherDuck cloud database connection
- Added db_bootstrap.py for table creation
- Configured Streamlit for port 5000 with CORS disabled
