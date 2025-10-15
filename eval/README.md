# EmberGuide Evaluation

Framework for evaluating wildfire nowcast quality using historical fires and standardized metrics.

---

## Overview

EmberGuide evaluation ensures the system produces **scientifically valid, calibrated predictions**. We measure:
- **Spatial accuracy**: Does the predicted high-probability area overlap with observed growth?
- **Directional accuracy**: Does spread direction match observations?
- **Calibration**: Do probabilities reflect real-world frequencies?
- **Comparison**: Does our model beat simple baselines?

**Key principles**:
- **Reproducible**: Fixed snapshots with golden fixtures
- **No leakage**: Strict temporal and spatial splits
- **Transparent**: All metrics and code open-source

---

## Quick Start

### Offline Evaluation (No Network)

Test the system on 2 fixed historical fires:

```bash
# Run full evaluation pipeline
make eval

# View results
open eval/snapshot/reports/summary.html
```

**What it does**:
1. Loads pre-downloaded data from `eval/snapshot/`
2. Runs pipeline (ingest → prep → model → tiles)
3. Compares outputs to `eval/snapshot/expected/`
4. Computes metrics (CSI, directional error, calibration)
5. Generates HTML report with plots

**Expected runtime**: ~2 minutes on laptop (no downloads)

---

## Directory Structure

```
eval/
├── snapshot/                    # Fixed test cases (versioned)
│   ├── fire_A/                 # 2020 California fire
│   │   ├── firms_detections.csv
│   │   ├── era5_weather.grib
│   │   ├── srtm_dem.tif
│   │   └── observed_growth.geojson  # Ground truth
│   ├── fire_B/                 # 2023 Canada fire
│   │   └── ...
│   └── expected/               # Golden outputs
│       ├── fire_A_nowcast_24h.tif
│       ├── fire_A_metrics.json
│       └── ...
├── historical/                  # Full historical dataset (gitignored)
│   ├── 2018/
│   ├── 2019/
│   └── ...
├── scripts/
│   ├── run_eval.py             # Main evaluation script
│   ├── compute_metrics.py      # Metrics calculation
│   └── generate_report.py      # HTML report generator
└── results/                     # Evaluation outputs
    ├── 2024-01-15_eval/
    │   ├── metrics.json
    │   ├── plots/
    │   │   ├── reliability_curve.png
    │   │   ├── spatial_iou.png
    │   │   └── directional_error.png
    │   └── summary.html
    └── ...
```

---

## Evaluation Metrics

### 1. Spatial Accuracy (CSI / IoU)

**Critical Success Index (CSI)**:
$$
\text{CSI} = \frac{\text{hits}}{\text{hits} + \text{false alarms} + \text{misses}}
$$

**Intersection over Union (IoU)**:
$$
\text{IoU} = \frac{\text{predicted} \cap \text{observed}}{\text{predicted} \cup \text{observed}}
$$

**Interpretation**:
- CSI/IoU = 1.0: Perfect overlap
- CSI/IoU = 0.5: Decent (50% overlap)
- CSI/IoU < 0.3: Poor

**Threshold**: Typically evaluate at p≥0.5 (predicted high-risk area).

**Code**:
```python
def compute_csi(predicted: np.ndarray, observed: np.ndarray, threshold: float = 0.5):
    pred_binary = predicted >= threshold
    hits = np.sum(pred_binary & observed)
    false_alarms = np.sum(pred_binary & ~observed)
    misses = np.sum(~pred_binary & observed)
    return hits / (hits + false_alarms + misses)
```

---

### 2. Directional Accuracy

**Mean Absolute Error (MAE)**:
$$
\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |\theta_{\text{pred}} - \theta_{\text{obs}}|
$$

Where θ is spread direction in degrees (0–360°).

**Interpretation**:
- MAE < 30°: Good alignment
- MAE 30–60°: Moderate
- MAE > 60°: Poor

**Note**: Use circular distance (wrap around 360°).

**Code**:
```python
def circular_distance(angle1, angle2):
    diff = np.abs(angle1 - angle2)
    return np.minimum(diff, 360 - diff)

def directional_mae(pred_dirs, obs_dirs):
    distances = circular_distance(pred_dirs, obs_dirs)
    return np.mean(distances)
```

---

### 3. Calibration (Reliability)

**Reliability Curve**:
- Bin predicted probabilities (e.g., 0–0.1, 0.1–0.2, ..., 0.9–1.0)
- For each bin, compute observed frequency (fraction that actually burned)
- Plot: predicted (x-axis) vs observed (y-axis)
- Ideal: diagonal line (predicted = observed)

**Expected Calibration Error (ECE)**:
$$
\text{ECE} = \sum_{b=1}^{B} \frac{|n_b|}{N} |\text{acc}_b - \text{conf}_b|
$$

Where:
- \( n_b \) = samples in bin b
- \( \text{acc}_b \) = observed frequency in bin b
- \( \text{conf}_b \) = mean predicted probability in bin b

**Interpretation**:
- ECE < 0.05: Well-calibrated
- ECE 0.05–0.15: Acceptable
- ECE > 0.15: Poorly calibrated

**Code**:
```python
from sklearn.calibration import calibration_curve

def plot_reliability_curve(y_true, y_pred, n_bins=10):
    prob_true, prob_pred = calibration_curve(y_true, y_pred, n_bins=n_bins)
    plt.plot(prob_pred, prob_true, marker='o', label='Model')
    plt.plot([0, 1], [0, 1], 'k--', label='Perfect')
    plt.xlabel('Predicted Probability')
    plt.ylabel('Observed Frequency')
    plt.legend()
    plt.title('Reliability Curve')
    plt.savefig('reliability_curve.png')
```

---

### 4. Brier Score

**Measures** squared difference between predicted probabilities and outcomes:
$$
\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (p_i - o_i)^2
$$

Where:
- \( p_i \) = predicted probability for pixel i
- \( o_i \) = observed outcome (0 or 1)

**Interpretation**:
- Brier = 0: Perfect
- Brier < 0.1: Good
- Brier > 0.25: Poor (worse than random)

**Code**:
```python
from sklearn.metrics import brier_score_loss

brier = brier_score_loss(y_true, y_pred)
```

---

### 5. Distance-to-Perimeter

**Measure** how far the predicted front is from the observed perimeter:
```python
def distance_to_perimeter(pred_perimeter, obs_perimeter):
    # Convert to shapely geometries
    from shapely.geometry import LineString
    pred_line = LineString(pred_perimeter)
    obs_line = LineString(obs_perimeter)
    return pred_line.hausdorff_distance(obs_line)
```

**Interpretation** (in meters):
- < 500 m: Excellent
- 500–2000 m: Good
- > 2000 m: Poor

---

## Baselines to Beat

### 1. Persistence (No Growth)

Assume fire doesn't spread (tomorrow = today).

**Expected performance**: CSI ~0.2 for active fires.

### 2. Wind-Only Advection

Simple model: spread only in wind direction, ignore slope/dryness.

**Expected performance**: CSI ~0.3–0.4, directional MAE ~40°.

### 3. EmberGuide Baseline (Physics-Based)

Our baseline spread model (no ML).

**Target**: CSI ≥0.4, directional MAE ≤30°, ECE ≤0.1.

### 4. EmberGuide + ML

With denoiser + calibrator.

**Target**: Beat baseline by ≥5% on CSI and ECE.

---

## Evaluation Workflow

### 1. Prepare Test Set

```bash
# Download historical fires (2018–2023)
python -m eval.scripts.download_historical \
  --years 2018,2019,2020,2021,2022,2023 \
  --regions CA,OR,WA,MT,CO \
  --output eval/historical/

# Generate train/test splits
python -m eval.scripts.create_splits \
  --historical eval/historical/ \
  --output eval/splits.json
```

**Splits** (by fire complex/year):
- Train: 2018–2021 (60 fires)
- Validation: 2022 (20 fires)
- Test: 2023 (30 fires)

---

### 2. Run Pipeline on Test Fires

```bash
# For each test fire
for fire_id in $(cat eval/splits.json | jq '.test[]'); do
  python -m pipeline.run \
    --fire-id $fire_id \
    --config configs/active.yml \
    --output eval/results/test_runs/$fire_id/
done
```

---

### 3. Compute Metrics

```bash
python -m eval.scripts.compute_metrics \
  --predictions eval/results/test_runs/ \
  --ground-truth eval/historical/observed/ \
  --output eval/results/metrics.json
```

**Output** (`metrics.json`):
```json
{
  "summary": {
    "csi_mean": 0.42,
    "csi_std": 0.08,
    "directional_mae_mean": 28.5,
    "directional_mae_std": 12.3,
    "ece": 0.08,
    "brier": 0.12
  },
  "per_fire": {
    "fire_001": {"csi": 0.45, "directional_mae": 22.0, "brier": 0.10},
    "fire_002": {"csi": 0.39, "directional_mae": 35.0, "brier": 0.14}
  }
}
```

---

### 4. Generate Report

```bash
python -m eval.scripts.generate_report \
  --metrics eval/results/metrics.json \
  --output eval/results/summary.html
```

**Report includes**:
- Summary table (mean/std metrics)
- Reliability curve
- Spatial IoU distribution (histogram)
- Directional error distribution
- Per-fire performance (sortable table)
- Before/after toggles for ML modules

---

## Snapshot Evaluation (Fast)

For CI/CD and quick checks, use fixed snapshots:

```bash
make eval  # Runs on eval/snapshot/fire_A and fire_B
```

**Checks**:
- GeoTIFF outputs match expected (checksum or pixel RMSE < threshold)
- Metrics within tolerance:
  - CSI: 0.40 ± 0.05
  - Directional MAE: 30° ± 5°
  - ECE: 0.10 ± 0.02

**CI integration**:
```yaml
# .github/workflows/test.yml
- name: Run evaluation
  run: make eval
- name: Check metrics
  run: python -m eval.scripts.check_metrics --expected eval/snapshot/expected/metrics.json
```

---

## Golden Fixtures

### Creating Golden Outputs

When baseline model changes (intentionally), regenerate golden fixtures:

```bash
# Run pipeline on snapshot fires
python -m pipeline.run --fire-id fire_A --output eval/snapshot/expected/

# Verify manually (visual inspection, metrics check)
# If satisfied, commit new golden files
git add eval/snapshot/expected/
git commit -m "Update golden fixtures for v2.0 baseline"
```

### Tolerance for Floating-Point Differences

GeoTIFF outputs may have small numerical differences (e.g., Monte Carlo randomness even with fixed seed on different CPUs).

**Solution**: Check RMSE instead of exact match:
```python
def check_geotiff_match(actual, expected, rmse_threshold=1e-5):
    import rasterio
    with rasterio.open(actual) as a, rasterio.open(expected) as e:
        a_data = a.read(1)
        e_data = e.read(1)
        rmse = np.sqrt(np.mean((a_data - e_data)**2))
        assert rmse < rmse_threshold, f"RMSE {rmse} exceeds threshold {rmse_threshold}"
```

---

## Stratified Evaluation

### By Region

Compare performance across different regions:
```python
metrics_by_region = {
    "CA": {"csi": 0.45, "mae": 25.0},
    "OR": {"csi": 0.38, "mae": 32.0},
    "MT": {"csi": 0.40, "mae": 28.0}
}
```

**Insight**: Model may perform better in California (more training data) than Montana.

### By Fire Size

Stratify by burned area:
- Small (< 1000 ha): CSI may be lower (less signal)
- Medium (1000–10,000 ha): Best performance
- Large (> 10,000 ha): CSI may drop (complex dynamics)

### By Weather Conditions

Stratify by wind speed, RH:
- High wind (> 10 m/s): Directional MAE should be lower (stronger signal)
- Low RH (< 20%): CSI should be higher (more aggressive spread)

---

## Evaluation Best Practices

### 1. Never Test on Training Data

**Bad**: Train calibrator on 2020 fires, test on same 2020 fires.  
**Good**: Train on 2018–2021, test on 2023.

### 2. Temporal Holdout

If you can't split by fire, at least split by time:
- Train: First 70% of fire timeline
- Test: Last 30%

(But spatial split by fire complex is better!)

### 3. Report Uncertainty

Always report mean ± std or confidence intervals:
- CSI: 0.42 ± 0.08 (mean ± std over 30 test fires)
- Use bootstrap resampling for robust CI estimation

### 4. Visualize Failures

Inspect worst-performing fires:
```bash
python -m eval.scripts.visualize_failures \
  --metrics eval/results/metrics.json \
  --top-n 5 \
  --output eval/results/failure_analysis/
```

**Look for**:
- Systematic biases (e.g., always over-predict in high RH)
- Data issues (e.g., missing weather grids)
- Edge cases (e.g., fires crossing water bodies)

---

## ML Module Evaluation

### Denoiser Impact

**Compare**:
- Baseline (no denoiser)
- With denoiser (threshold = 0.5)

**Metrics**:
- Nowcast CSI (does removing false hotspots help?)
- False positive rate (do we remove too many real fires?)

**Expected**: Denoiser should improve CSI by 2–5% and reduce false alarms by 20–30%.

### Calibrator Impact

**Compare**:
- Baseline (raw scores)
- With calibrator (isotonic regression)

**Metrics**:
- ECE (should decrease)
- Brier score (should decrease)
- Reliability curve (should be closer to diagonal)

**Expected**: Calibrator should reduce ECE from ~0.15 to ~0.08.

---

## Troubleshooting

### "CSI is 0 for all test fires"

**Solution**:
- Check ground truth labels (are observed perimeters empty?)
- Verify prediction threshold (p≥0.5 may be too high; try p≥0.3)
- Inspect predictions visually (are they all zeros?)

### "Directional MAE is random (~90°)"

**Solution**:
- Check wind data (is it valid?)
- Verify direction calculation (0° = north, 90° = east?)
- Ensure circular distance is used (not linear)

### "Reliability curve is flat"

**Solution**:
- Model may not be discriminative (all predictions near 0.5)
- Check baseline spread model (is it working?)
- Try different calibration method (logistic instead of isotonic)

---

## Next Steps

- **Pipeline**: See [pipeline/README.md](../pipeline/README.md) for generating nowcasts
- **ML Modules**: See [ml/README.md](../ml/README.md) for training calibrators
- **Deployment**: See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for production monitoring

---

## References

- [WILDFIRE_101.md](../WILDFIRE_101.md) — Domain background and metrics explainer
- [Scikit-learn Metrics](https://scikit-learn.org/stable/modules/model_evaluation.html)
- Jolliff et al. (2009). "Summary diagrams for coupled hydrodynamic-ecosystem model skill assessment." JGR Oceans.
- DeGroot & Fienberg (1983). "The comparison and evaluation of forecasters." The Statistician, 32(1-2): 12-22.

