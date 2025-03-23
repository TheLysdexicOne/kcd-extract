import logging
from logging import Logger, Handler
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import List

# Ensure logs directory exists
LOG_DIR: Path = Path(__file__).resolve().parent.parent / "src/logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Define log files
timestamp: str = datetime.now().strftime('%Y%m%d_%H%M%S')
TIMED_LOG_FILE: Path = LOG_DIR / f"kcd-extract_{timestamp}.log"
STATIC_LOG_FILE: Path = LOG_DIR / "kcd-extract.log"

# Create logger
logger: Logger = logging.getLogger("kcd-extract")
logger.setLevel(logging.DEBUG)  # Set minimum log level

# Create rotating file handler for timestamped log file
unique_handler: RotatingFileHandler = RotatingFileHandler(
    TIMED_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
)
unique_handler.setLevel(logging.DEBUG)

# Create file handler for statically named log file
static_handler: logging.FileHandler = logging.FileHandler(
    STATIC_LOG_FILE, mode='w'  # 'w' mode to start with an empty file each run
)
static_handler.setLevel(logging.DEBUG)

# Create console handler
console_handler: logging.StreamHandler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Show only INFO+ logs in console

# Define log format
formatter: logging.Formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
unique_handler.setFormatter(formatter)
static_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(unique_handler)
logger.addHandler(static_handler)
logger.addHandler(console_handler)

# Keep only the latest 5 logs
MAX_LOGS: int = 5  # Keep only the latest 5 logs
log_files: List[Path] = sorted(
    LOG_DIR.glob("kcd-extract_*.log"), key=lambda f: f.stat().st_mtime, reverse=True
)
for old_log in log_files[MAX_LOGS:]:  # Delete logs beyond limit
    old_log.unlink()