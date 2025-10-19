"""Simple test script to verify EmberGuide POC setup."""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')  # Set to UTF-8


def test_imports():
    """Test that all required packages can be imported."""
    print("Testing package imports...")
    
    packages = [
        ('fastapi', 'FastAPI'),
        ('streamlit', 'Streamlit'),
        ('rasterio', 'Rasterio (GDAL)'),
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('xarray', 'xarray'),
        ('sklearn', 'scikit-learn'),
        ('folium', 'Folium'),
        ('yaml', 'PyYAML'),
        ('dotenv', 'python-dotenv'),
    ]
    
    failed = []
    for package, name in packages:
        try:
            __import__(package)
            print(f"  [OK] {name}")
        except ImportError as e:
            print(f"  [FAIL] {name}: {e}")
            failed.append(name)
    
    if failed:
        print(f"\n[FAIL] Failed to import: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("\n[OK] All packages imported successfully!")
        return True


def test_directory_structure():
    """Test that required directories exist."""
    print("\nTesting directory structure...")
    
    required_dirs = [
        'api',
        'ui',
        'pipeline',
        'ml',
        'configs',
        'data',
        'docs'
    ]
    
    missing = []
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"  [OK] {dir_name}/")
        else:
            print(f"  [FAIL] {dir_name}/ (missing)")
            missing.append(dir_name)
    
    if missing:
        print(f"\n[FAIL] Missing directories: {', '.join(missing)}")
        return False
    else:
        print("\n[OK] All directories present!")
        return True


def test_config_files():
    """Test that configuration files exist."""
    print("\nTesting configuration files...")
    
    config_files = [
        'configs/active.yml',
        'configs/ingest.yml',
        'configs/prep.yml',
        'configs/spread.yml',
        'configs/ml.yml'
    ]
    
    missing = []
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"  [OK] {config_file}")
        else:
            print(f"  [FAIL] {config_file} (missing)")
            missing.append(config_file)
    
    if missing:
        print(f"\n[FAIL] Missing config files: {', '.join(missing)}")
        return False
    else:
        print("\n[OK] All config files present!")
        return True


def test_module_imports():
    """Test that EmberGuide modules can be imported."""
    print("\nTesting EmberGuide modules...")
    
    modules = [
        'pipeline.utils',
        'pipeline.ingest',
        'pipeline.prep',
        'pipeline.spread',
        'ml.denoiser.simple',
        'ml.calibration.isotonic',
        'api.main',
        'ui.utils.api_client'
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except Exception as e:
            print(f"  [FAIL] {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n[FAIL] Failed to import modules: {', '.join(failed)}")
        return False
    else:
        print("\n[OK] All modules imported successfully!")
        return True


def main():
    """Run all tests."""
    print("="*60)
    print("EmberGuide POC Setup Test")
    print("="*60)
    print()
    
    tests = [
        test_imports,
        test_directory_structure,
        test_config_files,
        test_module_imports
    ]
    
    results = [test() for test in tests]
    
    print("\n" + "="*60)
    if all(results):
        print("[SUCCESS] All tests passed! Setup is complete.")
        print("\nNext steps:")
        print("1. Run pipeline: py -m pipeline.run")
        print("2. Start API: py -m uvicorn api.main:app --port 8000")
        print("3. Launch UI: py -m streamlit run ui/app.py")
    else:
        print("[FAIL] Some tests failed. Please fix the issues above.")
        sys.exit(1)
    print("="*60)


if __name__ == "__main__":
    main()

