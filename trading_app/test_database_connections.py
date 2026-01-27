"""
Test script to verify all database connections work correctly in cloud mode.
This ensures the APK build will work without database connection errors.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up cloud mode environment
os.environ['STREAMLIT_RUNTIME_ENV'] = 'cloud'

from trading_app.cloud_mode import get_database_path, _ensure_schema_initialized
from trading_app.strategy_discovery import StrategyDiscovery
from trading_app.directional_bias import DirectionalBiasDetector
from trading_app.setup_detector import SetupDetector
from trading_app.setup_scanner import SetupScanner

def test_cloud_mode_detection():
    """Test cloud mode detection"""
    print("=" * 60)
    print("TEST 1: Cloud Mode Detection")
    print("=" * 60)
    
    from trading_app.cloud_mode import is_cloud_deployment
    is_cloud = is_cloud_deployment()
    print(f"[OK] Cloud mode detected: {is_cloud}")
    assert is_cloud, "Should detect cloud mode when STREAMLIT_RUNTIME_ENV=cloud"
    print()

def test_database_path():
    """Test database path resolution"""
    print("=" * 60)
    print("TEST 2: Database Path Resolution")
    print("=" * 60)
    
    db_path = get_database_path()
    print(f"[OK] Database path: {db_path}")
    assert "trading_app.db" in db_path, "Should use trading_app.db in cloud mode"
    assert Path(db_path).parent.exists(), "Database directory should exist"
    print()

def test_schema_initialization():
    """Test schema initialization"""
    print("=" * 60)
    print("TEST 3: Schema Initialization")
    print("=" * 60)
    
    # Create a temporary database path (don't create file yet)
    tmp_db = os.path.join(tempfile.gettempdir(), f"test_db_{os.getpid()}.db")
    
    # Remove if exists
    if os.path.exists(tmp_db):
        os.unlink(tmp_db)
    
    try:
        # Initialize schema (will create database)
        _ensure_schema_initialized(tmp_db)
        
        # Verify tables exist
        import duckdb
        con = duckdb.connect(tmp_db)
        tables = con.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        
        table_names = [t[0] for t in tables]
        print(f"[OK] Tables created: {', '.join(table_names)}")
        
        assert 'daily_features' in table_names, "daily_features should exist"
        assert 'validated_setups' in table_names, "validated_setups should exist"
        
        con.close()
        print("[OK] Schema initialization successful")
    finally:
        # Clean up
        if os.path.exists(tmp_db):
            os.unlink(tmp_db)
    print()

def test_strategy_discovery():
    """Test StrategyDiscovery initialization"""
    print("=" * 60)
    print("TEST 4: StrategyDiscovery Initialization")
    print("=" * 60)
    
    # Should not fail even if database doesn't exist
    discovery = StrategyDiscovery()
    print(f"[OK] StrategyDiscovery initialized: {discovery.db_path}")
    
    # Connection should be None until needed
    assert discovery._con is None, "Connection should be lazy"
    print("[OK] Lazy connection verified")
    
    # Should handle missing database gracefully
    result = discovery.get_existing_setups("MGC", "0900")
    assert isinstance(result, list), "Should return empty list if database missing"
    print("[OK] Graceful handling of missing database")
    print()

def test_directional_bias():
    """Test DirectionalBiasDetector initialization"""
    print("=" * 60)
    print("TEST 5: DirectionalBiasDetector Initialization")
    print("=" * 60)
    
    detector = DirectionalBiasDetector(None)
    print(f"[OK] DirectionalBiasDetector initialized: {detector.db_path}")
    
    # Connection should be None until needed
    assert detector._con is None, "Connection should be lazy"
    print("[OK] Lazy connection verified")
    
    # Should handle missing database gracefully
    from datetime import datetime
    bias = detector.get_directional_bias("MGC", "1100", 2700.0, 2695.0, datetime.now())
    assert bias.confidence == "NEUTRAL", "Should return neutral if database missing"
    print("[OK] Graceful handling of missing database")
    print()

def test_setup_detector():
    """Test SetupDetector initialization"""
    print("=" * 60)
    print("TEST 6: SetupDetector Initialization")
    print("=" * 60)
    
    detector = SetupDetector(None)
    print(f"[OK] SetupDetector initialized: {detector.db_path}")
    
    # Connection should be None until needed
    assert detector._con is None, "Connection should be lazy"
    print("[OK] Lazy connection verified")
    
    # Should handle missing database gracefully
    setups = detector.get_all_validated_setups("MGC")
    assert isinstance(setups, list), "Should return empty list if database missing"
    print("[OK] Graceful handling of missing database")
    print()

def test_setup_scanner():
    """Test SetupScanner initialization"""
    print("=" * 60)
    print("TEST 7: SetupScanner Initialization")
    print("=" * 60)
    
    db_path = get_database_path()
    scanner = SetupScanner(db_path)
    print(f"[OK] SetupScanner initialized with: {db_path}")
    
    # Should not fail even if database doesn't exist
    assert scanner.detector._con is None, "Connection should be lazy"
    print("[OK] Lazy connection verified")
    print()

def test_all_components_together():
    """Test all components initialized together (like in app)"""
    print("=" * 60)
    print("TEST 8: All Components Together")
    print("=" * 60)
    
    # Simulate app initialization
    db_path = get_database_path()
    
    components = {
        'strategy_discovery': StrategyDiscovery(),
        'directional_bias': DirectionalBiasDetector(None),
        'setup_detector': SetupDetector(None),
        'setup_scanner': SetupScanner(db_path),
    }
    
    print("[OK] All components initialized successfully:")
    for name, component in components.items():
        if hasattr(component, 'db_path'):
            print(f"  - {name}: {component.db_path}")
        else:
            print(f"  - {name}: OK")
    
    # Verify all connections are lazy
    for name, component in components.items():
        if hasattr(component, '_con'):
            assert component._con is None, f"{name} should have lazy connection"
        elif hasattr(component, 'detector') and hasattr(component.detector, '_con'):
            assert component.detector._con is None, f"{name}.detector should have lazy connection"
    
    print("[OK] All connections are lazy (no database access at init)")
    print()

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DATABASE CONNECTION TESTS - Cloud Mode")
    print("=" * 60)
    print()
    
    try:
        test_cloud_mode_detection()
        test_database_path()
        test_schema_initialization()
        test_strategy_discovery()
        test_directional_bias()
        test_setup_detector()
        test_setup_scanner()
        test_all_components_together()
        
        print("=" * 60)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("The app should now work in cloud mode without database errors.")
        print("APK build should succeed!")
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print("[FAILED] TEST FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] UNEXPECTED ERROR!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
