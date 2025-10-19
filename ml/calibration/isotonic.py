"""Isotonic regression calibration for fire spread probabilities."""

from pathlib import Path

import numpy as np
import joblib
from sklearn.isotonic import IsotonicRegression

from pipeline.utils import setup_logger

logger = setup_logger(__name__)


def create_mock_calibrator(output_path: Path, n_samples: int = 100, seed: int = 42) -> Path:
    """
    Create a mock calibrator with synthetic training data for POC.
    
    In production, this would be trained on real historical fires.
    
    Args:
        output_path: Path to save calibrator model
        n_samples: Number of synthetic training samples
        seed: Random seed
    
    Returns:
        Path to saved model
    """
    logger.info(f"Creating mock calibrator with {n_samples} synthetic samples")
    
    np.random.seed(seed)
    
    # Generate synthetic data
    # Model: raw scores tend to overestimate, especially at high values
    raw_scores = np.random.uniform(0, 1, n_samples)
    
    # True probabilities are lower than raw scores (overconfident model)
    # Add noise
    true_probs = raw_scores * 0.7 + np.random.normal(0, 0.1, n_samples)
    true_probs = np.clip(true_probs, 0, 1)
    
    # Convert to binary outcomes (0 or 1)
    outcomes = (np.random.uniform(0, 1, n_samples) < true_probs).astype(int)
    
    # Fit isotonic regression
    calibrator = IsotonicRegression(out_of_bounds='clip')
    calibrator.fit(raw_scores, outcomes)
    
    # Save model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    model_artifact = {
        'model': calibrator,
        'method': 'isotonic',
        'n_samples': n_samples,
        'seed': seed,
        'version': 'poc_v1'
    }
    
    joblib.dump(model_artifact, output_path)
    
    logger.info(f"Mock calibrator saved to {output_path}")
    
    return output_path


def load_calibrator(model_path: Path) -> dict:
    """Load calibrator model from file."""
    return joblib.load(model_path)


def apply_calibration(
    probability_grid: np.ndarray,
    calibrator_path: Path
) -> np.ndarray:
    """
    Apply calibration to probability grid.
    
    Args:
        probability_grid: Raw probability values [0-1]
        calibrator_path: Path to calibrator model file
    
    Returns:
        Calibrated probability grid [0-1]
    """
    logger.info("Applying probability calibration")
    
    # Load calibrator
    artifact = load_calibrator(calibrator_path)
    calibrator = artifact['model']
    
    # Flatten grid for calibration
    original_shape = probability_grid.shape
    flat_probs = probability_grid.flatten()
    
    # Apply calibration
    calibrated_flat = calibrator.predict(flat_probs)
    calibrated_flat = np.clip(calibrated_flat, 0, 1)
    
    # Reshape
    calibrated_grid = calibrated_flat.reshape(original_shape).astype(np.float32)
    
    logger.info(f"Calibration applied. Mean shift: {(calibrated_grid - probability_grid).mean():.3f}")
    
    return calibrated_grid

