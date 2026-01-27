# Documentation Index

**Last Updated:** January 17, 2026

Complete guide to all documentation in the MGC Trading System.

---

## 📱 Mobile App Documentation

### Primary Guides

**[MOBILE_APP_README.md](MOBILE_APP_README.md)** ⭐ START HERE
- Complete mobile app guide (newly created)
- All 5 cards explained (Dashboard, Chart, Trade, Positions, AI Chat)
- ML predictions, Market Intelligence, Safety Status
- Setup Scanner, Directional Bias features
- Technical architecture and troubleshooting
- **Status:** ✅ Fully updated (Jan 17, 2026)

**[MOBILE_APP_GUIDE.md](MOBILE_APP_GUIDE.md)**
- Original mobile app user guide
- Card-by-card walkthrough
- Design philosophy and UX
- **Note:** Predates ML integration, see MOBILE_APP_README.md for latest features

**[FINAL_STATUS_REPORT.md](FINAL_STATUS_REPORT.md)**
- Integration completion report (Jan 17, 2026)
- What was built and debugged
- Honest assessment of features
- Performance metrics and testing results
- **Status:** ✅ Current

---

## 🤖 ML/AI Documentation

**[ML_USER_GUIDE.md](ML_USER_GUIDE.md)**
- How ML predictions work
- Training methodology (740 days MGC data)
- Accuracy metrics (55-60% directional)
- When to trust predictions
- Integration with strategy engine
- **Status:** ✅ Current (Jan 17, 2026)

**[ML_FINAL_SUMMARY.md](ML_FINAL_SUMMARY.md)**
- ML project completion summary
- All 10 deliverables completed
- Model performance metrics
- Files created and modified
- **Status:** ✅ Complete (Jan 17, 2026)

**[ML_INTEGRATION_COMPLETE.md](ML_INTEGRATION_COMPLETE.md)**
- Technical integration details
- Phase-by-phase implementation
- Testing and verification results

**[README_ML.md](README_ML.md)**
- ML technical overview
- Model registry structure
- Training pipeline details
- Inference engine architecture

---

## 📊 Trading Strategy Documentation

**[TRADING_PLAYBOOK.md](TRADING_PLAYBOOK.md)** ⭐ STRATEGY GUIDE
- Zero-lookahead methodology (honest win rates)
- Top 3 tradeable setups (10:00 UP, correlations)
- Complete ORB performance (739 days analyzed)
- Risk management rules
- **NEW:** Mobile app + ML integration section (Jan 17, 2026)
- Daily workflow examples
- **Status:** ✅ Fully updated (Jan 17, 2026)

**[CHATGPT_TRADING_GUIDE.md](CHATGPT_TRADING_GUIDE.md)**
- Focused on 2300 and 0030 ORBs
- Complete entry rules and calculations
- Optimized for ChatGPT usage
- Session-specific strategies

---

## 🗄️ Data Pipeline Documentation

**[README.md](README.md)** - Main Project README
- Data pipeline overview (Databento + ProjectX)
- Complete tool reference (backfill, analysis, backtesting)
- Feature engineering (ORBs, sessions, indicators)
- AI query interface
- Trading journal
- 740 days of data coverage
- **Focus:** Data management and analysis tools

**[CLAUDE.md](CLAUDE.md)** - Developer Instructions
- Project overview and architecture
- Key commands (backfill, features, testing)
- Database schema (bars_1m, bars_5m, daily_features)
- Time and calendar model (trading day definition)
- Idempotency and resume behavior
- **CRITICAL:** Database/config synchronization rules
- **Must read** for developers working on the system

---

## 📁 Project Structure

**[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)**
- File organization (after Jan 15 cleanup)
- What's in root directory (29 Python files)
- What's in _archive (old/deprecated files)
- What's in trading_app folder
- Purpose of each major file

---

## 🚀 Deployment & Setup

**[DEPLOY_TO_CLOUD.md](DEPLOY_TO_CLOUD.md)**
- Streamlit Cloud deployment guide
- Requirements and configuration
- Environment variables
- Database handling

**[CLOUD_QUICK_START.md](CLOUD_QUICK_START.md)**
- Quick cloud deployment steps
- Troubleshooting common issues

**[ANDROID_APK_GUIDE.md](ANDROID_APK_GUIDE.md)**
- Building Android APK with Capacitor
- Mobile deployment process

**[BUILD_APK_INSTRUCTIONS.md](BUILD_APK_INSTRUCTIONS.md)**
- Detailed APK build steps
- Prerequisites and dependencies

---

## 🔧 System Status Reports

**[DEBUGGING_COMPLETE.md](DEBUGGING_COMPLETE.md)**
- All bugs fixed (Jan 17, 2026)
- ML inference crash resolution
- MarketIntelligence timezone fix
- Attribute access corrections
- **Status:** ✅ All issues resolved

**[APP_STATUS_VERIFIED.md](APP_STATUS_VERIFIED.md)**
- Verification checklist
- Current operational status
- Expected behaviors
- Performance metrics

**[MOBILE_APP_REAL_INTEGRATION.md](MOBILE_APP_REAL_INTEGRATION.md)**
- Honest assessment of integration work
- What was actually integrated vs claimed
- Files modified and line counts

---

## 📱 Other Mobile/App Docs

**[MOBILE_APP_COMPLETE.md](MOBILE_APP_COMPLETE.md)**
- Original mobile app completion report
- Basic features (pre-ML integration)

**[MOBILE_APP_IMPLEMENTATION_COMPLETE.md](MOBILE_APP_IMPLEMENTATION_COMPLETE.md)**
- Implementation details
- Pre-ML version

**[UPDATE_WORKFLOW.md](UPDATE_WORKFLOW.md)**
- Development workflow
- Update procedures

---

## 🖥️ Desktop App Documentation

**[trading_app/README.md](trading_app/README.md)**
- Desktop trading hub guide (`app_trading_hub.py`)
- Real-time decision support
- Strategy hierarchy (CASCADE, NIGHT_ORB, etc.)
- Live charting and position tracking
- **Note:** Desktop version, not mobile

---

## 🏗️ Architecture Reports

**[ARCHITECTURAL_IMPROVEMENTS_JAN16.md](ARCHITECTURAL_IMPROVEMENTS_JAN16.md)**
- System improvements (Jan 16, 2026)
- Performance optimizations
- Code quality enhancements

**[CLEANUP_COMPLETE_JAN16.md](CLEANUP_COMPLETE_JAN16.md)**
- Project cleanup (Jan 16, 2026)
- File organization
- Deprecated code removal

**[AI_DYNAMIC_LOADING_JAN16.md](AI_DYNAMIC_LOADING_JAN16.md)**
- AI assistant improvements
- Dynamic loading implementation

---

## 🎯 Quick Navigation

### I want to...

**Use the mobile app:**
→ [MOBILE_APP_README.md](MOBILE_APP_README.md)

**Understand ML predictions:**
→ [ML_USER_GUIDE.md](ML_USER_GUIDE.md)

**Learn trading strategies:**
→ [TRADING_PLAYBOOK.md](TRADING_PLAYBOOK.md)

**Backfill data or manage database:**
→ [CLAUDE.md](CLAUDE.md) or [README.md](README.md)

**Deploy to cloud:**
→ [DEPLOY_TO_CLOUD.md](DEPLOY_TO_CLOUD.md)

**Understand project structure:**
→ [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

**Fix issues or debug:**
→ [DEBUGGING_COMPLETE.md](DEBUGGING_COMPLETE.md)

**Use desktop trading hub:**
→ [trading_app/README.md](trading_app/README.md)

---

## 📚 Recommended Reading Order

### For New Users:
1. **README.md** - Understand what the system does
2. **TRADING_PLAYBOOK.md** - Learn the strategies
3. **MOBILE_APP_README.md** - Use the mobile interface
4. **ML_USER_GUIDE.md** - Understand ML predictions

### For Traders:
1. **TRADING_PLAYBOOK.md** - Core strategies
2. **MOBILE_APP_README.md** - Execution interface
3. **CHATGPT_TRADING_GUIDE.md** - Night ORB specifics
4. **ML_USER_GUIDE.md** - ML-enhanced decisions

### For Developers:
1. **CLAUDE.md** - Project instructions
2. **PROJECT_STRUCTURE.md** - File organization
3. **README.md** - Data pipeline
4. **trading_app/README.md** - App architecture
5. **DEBUGGING_COMPLETE.md** - Known issues

---

## 🔄 Recently Updated (Jan 17, 2026)

✅ **MOBILE_APP_README.md** - Created comprehensive mobile app guide
✅ **TRADING_PLAYBOOK.md** - Added mobile app + ML integration section
✅ **FINAL_STATUS_REPORT.md** - Integration completion report
✅ **DEBUGGING_COMPLETE.md** - All bugs documented and fixed
✅ **APP_STATUS_VERIFIED.md** - Verification checklist complete
✅ **ML_USER_GUIDE.md** - ML features documented
✅ **ML_FINAL_SUMMARY.md** - ML project summary

---

## 📝 Documentation Standards

All documentation follows these principles:

1. **Honesty Over Accuracy**: Real performance metrics, no inflated claims
2. **Zero Lookahead**: Only use data available at decision time
3. **Reproducible**: Everything documented can be executed
4. **Up-to-Date**: Last updated dates clearly marked
5. **User-Focused**: Written for practitioners, not just developers

---

## 🆘 Getting Help

**Can't find what you need?**

1. Check this index for the right guide
2. Use AI Chat in mobile app for quick questions
3. Check logs: `tail -f trading_app/trading_app.log`
4. Run diagnostics: `python check_db.py`, `python validate_data.py`
5. Review DEBUGGING_COMPLETE.md for known issues

**Common Questions:**

- "How do I use the mobile app?" → MOBILE_APP_README.md
- "What trades should I take?" → TRADING_PLAYBOOK.md
- "How accurate is the ML?" → ML_USER_GUIDE.md (55-60%)
- "How do I backfill data?" → CLAUDE.md or README.md
- "Is the app working?" → APP_STATUS_VERIFIED.md

---

**Project Status:** 🟢 Fully Operational
**Mobile App:** http://localhost:8501 (START_MOBILE_APP.bat)
**Last System Update:** January 17, 2026
**Total Documentation Files:** 30+

**All systems integrated, debugged, and production-ready.**
