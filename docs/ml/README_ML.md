# ML/AI Trading System

## Overview

This ML system learns from historical trading data to predict directional bias, entry quality, and expected R-multiples for ORB-based trading strategies.

## Quick Start

### Installation

```bash
pip install -r requirements_ml.txt
```

### Training Your First Model

```bash
# Step 1: Prepare training data from database
python ml_training/prepare_training_data.py

# Step 2: Train the directional classifier
python ml_scripts/run_training.py --model directional

# Step 3: Evaluate model performance
python ml_scripts/evaluate_model.py --model directional_v1
```

### Using ML Predictions in the App

The ML system integrates automatically into the trading app when enabled in config:

```python
# trading_app/config.py
ML_ENABLED = True
ML_CONFIDENCE_THRESHOLD = 0.60
```

## Architecture

### Data Flow

```
DuckDB (gold.db)
  → prepare_training_data.py
  → historical_features.parquet
  → train_pipeline.py
  → ml_models/registry/
  → inference_engine.py
  → strategy_engine.py
  → Streamlit UI
```

### Models

1. **Directional Classifier** (`directional_v1/`)
   - Predicts: P(UP), P(DOWN), P(NONE)
   - Algorithm: LightGBM
   - Features: 50+ from daily_features_v2
   - Target: 55-60% accuracy

2. **Entry Quality Scorer** (`entry_quality_v1/`) - Phase 3
   - Predicts: P(WIN | break occurred)
   - Algorithm: XGBoost
   - Target: 60-65% accuracy

3. **R-Multiple Predictor** (`r_multiple_v1/`) - Phase 3
   - Predicts: Expected R-multiple
   - Algorithm: XGBoost Regressor
   - Target: MAE < 0.6R

## Directory Structure

```
ml_training/          # Training pipeline
ml_inference/         # Real-time inference
ml_monitoring/        # Performance monitoring
ml_models/registry/   # Versioned models
ml_data/             # Training datasets
ml_scripts/          # Utility scripts
tests/               # ML tests
```

## Features Used

### Time Features
- Day of week (cyclical encoding)
- Hour of day (cyclical encoding)
- Days since last high/low

### Session Features
- Asia/London/NY session high/low/range
- Pre-NY travel, pre-ORB travel
- Inter-session gaps

### ORB Features
- ORB size (all 6 ORBs: 0900, 1000, 1100, 1800, 2300, 0030)
- ORB size / ATR ratio
- Break direction (UP, DOWN, NONE)

### Technical Indicators
- RSI (14-period)
- ATR (14-period)
- Momentum indicators

### Pattern Features
- Consecutive win/loss streaks
- Last 3 days outcomes
- Similar setup frequency

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Directional Accuracy | 55-60% | In Progress |
| Entry Quality | 60-65% | Planned |
| R-Multiple MAE | < 0.6R | Planned |
| Inference Latency | < 100ms | In Progress |
| Model Size | < 100MB | In Progress |

## Safety & Deployment

### Deployment Phases

1. **Shadow Mode**: Log predictions, don't act (Weeks 3-4)
2. **Advisory Mode**: Show in UI, user decides (Weeks 5-6)
3. **Hybrid Mode**: ML adjusts sizing, rules gate entry (Weeks 7-8)
4. **Full Auto**: ML can override rules (Post-validation)

### Safety Checks

- Minimum accuracy thresholds
- Drift detection
- A/B testing before rollout
- Circuit breaker for failures
- Graceful fallback to rules-only

## Monitoring

### Daily Checks
- Prediction accuracy
- Win rate vs ML confidence
- Drift detection alerts

### Weekly Checks
- Feature importance changes
- Model calibration
- Outcome logging completeness

### Monthly Checks
- Full performance audit
- Hyperparameter tuning
- A/B test new models

## Automated Retraining

**Nightly (03:00)**: Incremental update (5 min)
**Weekly (Sunday 04:00)**: Full retrain (30 min)
**Monthly**: Hyperparameter tuning (1 hour)

## Configuration

Key settings in `trading_app/config.py`:

```python
ML_ENABLED = True
ML_CONFIDENCE_THRESHOLD = 0.60
ML_MIN_SAMPLES = 100
ML_CACHE_TTL = 300  # 5 minutes
ML_INFERENCE_TIMEOUT = 0.1  # 100ms
```

## Troubleshooting

### Model not loading
- Check `ml_models/registry/{model_name}/latest` symlink exists
- Verify model file permissions
- Check logs in `ml_training/logs/`

### Slow inference
- Enable prediction cache (default: 5 min TTL)
- Check feature store computation time
- Verify model size < 100MB

### Low accuracy
- Check for data quality issues
- Verify no lookahead bias in features
- Run drift detection
- Retrain with more recent data

## Development

### Adding New Features

1. Update `ml_training/feature_engineering.py`
2. Add feature to `FEATURE_COLUMNS` list
3. Retrain model with new features
4. Validate no lookahead bias

### Adding New Models

1. Create config in `ml_training/model_configs.py`
2. Add training logic to `train_pipeline.py`
3. Create inference method in `inference_engine.py`
4. Add tests in `tests/`

## References

- CLAUDE.md: Database schema and ORB definitions
- machinelearning.txt: Original requirements
- Implementation plan: This README

## Support

For issues or questions:
1. Check logs in `ml_training/logs/`
2. Run diagnostic: `python ml_scripts/diagnose.py`
3. Review monitoring dashboard in Streamlit app
