"""Check what symbols are in DBN files"""
import databento as db
from pathlib import Path

dbn_folder = Path("dbn")
dbn_files = sorted(dbn_folder.glob("*.dbn.zst"))

print(f"Found {len(dbn_files)} DBN files")
print("\nChecking first file for available symbols...")

# Check first file
first_file = dbn_files[0]
print(f"\nFile: {first_file.name}")

store = db.DBNStore.from_file(str(first_file))
df = store.to_df()

print(f"Dataset: {store.dataset}")
print(f"Schema: {store.schema}")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

if 'symbol' in df.columns:
    symbols = sorted(df['symbol'].unique())
    print(f"\nFound {len(symbols)} unique symbols")
    print(f"Sample: {symbols[:20]}")

    # Check for platinum
    platinum = [s for s in symbols if 'MPL' in str(s) or str(s).startswith('PL')]
    print(f"\nPlatinum symbols: {platinum if platinum else 'NONE FOUND'}")
else:
    print("\nNo 'symbol' column found in DataFrame")
    print(f"Index: {df.index.names}")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

if 'symbol' in df.columns:
    symbols = sorted(df['symbol'].unique())
    platinum = [s for s in symbols if 'MPL' in str(s) or str(s).startswith('PL')]

    if platinum:
        print("✅ PLATINUM DATA FOUND!")
        print(f"   Platinum symbols: {platinum}")
        print("\n   Run: python scripts/ingest_databento_dbn_mpl.py dbn")
    else:
        print("❌ NO PLATINUM DATA")
        print("   These DBN files contain MGC (gold) only")
        print("   You need separate platinum DBN files or API access")
else:
    print("⚠️  Cannot determine - unusual DBN format")
