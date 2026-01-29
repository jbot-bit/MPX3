"""
Error Logger for Trading Apps

Captures all errors and writes them to app_errors.txt
File is cleared on each app startup.

Usage:
    from trading_app.error_logger import initialize_error_log, log_error

    # At app startup
    initialize_error_log()

    # In try/except blocks
    try:
        # your code
    except Exception as e:
        log_error(e, context="Loading market data")
        st.error(f"Error: {e}")
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

# Error log path (in project root)
ERROR_LOG_PATH = Path(__file__).parent.parent / "app_errors.txt"


def initialize_error_log():
    """Clear error log file on app startup."""
    try:
        with open(ERROR_LOG_PATH, 'w') as f:
            f.write(f"=== App Error Log ===\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"=" * 60 + "\n\n")
        print(f"[OK] Error log initialized: {ERROR_LOG_PATH}")
    except Exception as e:
        print(f"[WARNING]  Failed to initialize error log: {e}")


def log_error(error: Exception, context: str = None):
    """
    Log error to file with full traceback.

    Args:
        error: The exception object
        context: Optional context string (e.g., "Loading database", "Market scanner")
    """
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(ERROR_LOG_PATH, 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{timestamp}] ERROR\n")
            if context:
                f.write(f"Context: {context}\n")
            f.write(f"{'='*60}\n\n")

            # Error type and message
            f.write(f"Type: {type(error).__name__}\n")
            f.write(f"Message: {str(error)}\n\n")

            # Full traceback
            f.write("Traceback:\n")
            f.write(traceback.format_exc())
            f.write("\n")

        print(f"[ERROR] Error logged to {ERROR_LOG_PATH}")

    except Exception as e:
        print(f"[WARNING]  Failed to log error: {e}")
        print(f"Original error: {error}")


def log_message(message: str, level: str = "INFO"):
    """
    Log a message (non-error) to the error log file.

    Args:
        message: The message to log
        level: Log level (INFO, WARNING, DEBUG)
    """
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(ERROR_LOG_PATH, 'a') as f:
            f.write(f"[{timestamp}] {level}: {message}\n")

    except Exception as e:
        print(f"[WARNING]  Failed to log message: {e}")


class ErrorLoggerContext:
    """
    Context manager for automatic error logging.

    Usage:
        with ErrorLoggerContext("Loading database"):
            # your code here
            conn = duckdb.connect(db_path)
    """

    def __init__(self, context: str):
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            log_error(exc_value, context=self.context)
        return False  # Don't suppress the exception
