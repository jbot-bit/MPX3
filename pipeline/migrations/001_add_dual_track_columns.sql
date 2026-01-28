-- Migration 001: Add Dual-Track Edge Metrics
-- Date: 2026-01-28
-- Purpose: Separate STRUCTURAL (ORB-anchored) from TRADEABLE (entry-anchored) metrics
--
-- This migration is APPEND-ONLY - existing columns remain unchanged
-- Adds 48 new columns (8 per ORB × 6 ORBs)

-- ============================================================================
-- 0900 ORB TRADEABLE COLUMNS
-- ============================================================================
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_entry_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_stop_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_risk_points DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_target_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_outcome VARCHAR;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_realized_rr DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_realized_risk_dollars DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0900_tradeable_realized_reward_dollars DOUBLE;

-- ============================================================================
-- 1000 ORB TRADEABLE COLUMNS
-- ============================================================================
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_entry_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_stop_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_risk_points DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_target_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_outcome VARCHAR;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_realized_rr DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_realized_risk_dollars DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1000_tradeable_realized_reward_dollars DOUBLE;

-- ============================================================================
-- 1100 ORB TRADEABLE COLUMNS
-- ============================================================================
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_entry_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_stop_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_risk_points DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_target_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_outcome VARCHAR;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_realized_rr DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_realized_risk_dollars DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1100_tradeable_realized_reward_dollars DOUBLE;

-- ============================================================================
-- 1800 ORB TRADEABLE COLUMNS
-- ============================================================================
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_entry_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_stop_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_risk_points DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_target_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_outcome VARCHAR;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_realized_rr DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_realized_risk_dollars DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_1800_tradeable_realized_reward_dollars DOUBLE;

-- ============================================================================
-- 2300 ORB TRADEABLE COLUMNS
-- ============================================================================
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_entry_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_stop_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_risk_points DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_target_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_outcome VARCHAR;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_realized_rr DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_realized_risk_dollars DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_2300_tradeable_realized_reward_dollars DOUBLE;

-- ============================================================================
-- 0030 ORB TRADEABLE COLUMNS
-- ============================================================================
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_entry_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_stop_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_risk_points DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_target_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_outcome VARCHAR;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_realized_rr DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_realized_risk_dollars DOUBLE;
ALTER TABLE daily_features ADD COLUMN IF NOT EXISTS orb_0030_tradeable_realized_reward_dollars DOUBLE;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these after migration to verify:
-- SELECT COUNT(*) FROM pragma_table_info('daily_features') WHERE name LIKE '%tradeable%';
-- Expected: 48 new columns

-- ROLLBACK PLAN (if needed):
-- ALTER TABLE daily_features DROP COLUMN orb_0900_tradeable_entry_price;
-- (repeat for all 48 columns)
