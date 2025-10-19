"""Utility functions for the EmberGuide pipeline."""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_checksum(filepath: Path, checksum: Optional[str] = None) -> None:
    """Save checksum to .checksums file in same directory."""
    if checksum is None:
        checksum = compute_sha256(filepath)
    
    checksum_file = filepath.parent / '.checksums'
    with open(checksum_file, 'a') as f:
        f.write(f"sha256:{checksum} {filepath.name}\n")


def timestamp_filename(prefix: str, extension: str, timestamp: Optional[datetime] = None) -> str:
    """Create timestamped filename."""
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    ts_str = timestamp.strftime("%Y-%m-%dT%H%M%S")
    return f"{prefix}_{ts_str}.{extension}"


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path

