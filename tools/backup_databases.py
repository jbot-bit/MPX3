#!/usr/bin/env python3
"""
Backup all database files with checksums and manifest.
Part of MotherDuck migration safety protocol.
"""

import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path


def calculate_sha256(filepath):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in 64kb chunks for efficiency
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def format_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def backup_databases():
    """Create timestamped backup of all database files."""
    # Create backup folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_dir = Path("backups") / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating backup in: {backup_dir}")
    print("-" * 70)

    # Find all database files
    db_patterns = ["*.db", "*.wal", "*.wal.tmp"]
    db_files = []

    for pattern in db_patterns:
        db_files.extend(Path(".").glob(pattern))

    if not db_files:
        print("ERROR: No database files found!")
        return False

    print(f"Found {len(db_files)} database file(s) to backup:\n")

    # Backup each file and collect metadata
    manifest = []
    manifest.append("=" * 70)
    manifest.append(f"DATABASE BACKUP MANIFEST")
    manifest.append(f"Timestamp: {datetime.now().isoformat()}")
    manifest.append(f"Backup Directory: {backup_dir}")
    manifest.append("=" * 70)
    manifest.append("")

    total_size = 0

    for db_file in sorted(db_files):
        if not db_file.is_file():
            continue

        # Get file info
        file_size = db_file.stat().st_size
        total_size += file_size

        # Copy file
        dest_path = backup_dir / db_file.name
        print(f"Copying: {db_file.name} ({format_size(file_size)})")
        shutil.copy2(db_file, dest_path)

        # Calculate checksum
        print(f"  Calculating SHA256...")
        checksum = calculate_sha256(dest_path)

        # Verify copy
        original_checksum = calculate_sha256(db_file)
        if checksum != original_checksum:
            print(f"  ERROR: Checksum mismatch for {db_file.name}!")
            return False

        print(f"  SHA256: {checksum}")
        print(f"  Status: OK\n")

        # Add to manifest
        manifest.append(f"File: {db_file.name}")
        manifest.append(f"  Size: {file_size} bytes ({format_size(file_size)})")
        manifest.append(f"  SHA256: {checksum}")
        manifest.append(f"  Backed up: {datetime.now().isoformat()}")
        manifest.append("")

    # Write manifest
    manifest.append("=" * 70)
    manifest.append(f"SUMMARY")
    manifest.append("=" * 70)
    manifest.append(f"Total files: {len(db_files)}")
    manifest.append(f"Total size: {total_size} bytes ({format_size(total_size)})")
    manifest.append(f"Backup completed: {datetime.now().isoformat()}")
    manifest.append("=" * 70)

    manifest_path = backup_dir / "MANIFEST.txt"
    with open(manifest_path, "w") as f:
        f.write("\n".join(manifest))

    print("-" * 70)
    print(f"Backup completed successfully!")
    print(f"Location: {backup_dir.absolute()}")
    print(f"Total size: {format_size(total_size)}")
    print(f"Manifest: {manifest_path}")
    print("-" * 70)

    return True


if __name__ == "__main__":
    success = backup_databases()

    if success:
        print("\n✅ BACKUP SUCCESSFUL - Safe to proceed with migration")
        exit(0)
    else:
        print("\n❌ BACKUP FAILED - DO NOT PROCEED")
        exit(1)
