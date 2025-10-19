"""
EmberGuide POC Demo Script

This script demonstrates the complete EmberGuide workflow:
1. Runs the pipeline to generate nowcasts
2. Provides instructions for starting API and UI

For production use, you'd run these components separately as services.
"""

import sys
import subprocess
from pathlib import Path


def print_banner(text):
    """Print a formatted banner."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def check_setup():
    """Check if setup is complete."""
    print_banner("Checking Setup")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check required directories
    required_dirs = ['api', 'ui', 'pipeline', 'ml', 'configs', 'data']
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            print(f"❌ Missing directory: {dir_name}/")
            return False
    print("✓ All directories present")
    
    # Check config files
    config_files = [
        'configs/active.yml',
        'configs/ingest.yml',
        'configs/prep.yml',
        'configs/spread.yml',
        'configs/ml.yml'
    ]
    for config_file in config_files:
        if not Path(config_file).exists():
            print(f"❌ Missing config: {config_file}")
            return False
    print("✓ All config files present")
    
    return True


def run_pipeline():
    """Run the pipeline to generate nowcast data."""
    print_banner("Running Pipeline")
    
    print("This will:")
    print("  1. Generate/fetch hotspot data (FIRMS)")
    print("  2. Generate/fetch weather data (ERA5)")
    print("  3. Create terrain model (SRTM)")
    print("  4. Cluster fires and align grids")
    print("  5. Run fire spread model (20 ensemble members)")
    print("  6. Apply ML calibration")
    print("  7. Save products to data/products/")
    print()
    print("Expected runtime: 2-5 minutes")
    print()
    
    input("Press Enter to start pipeline...")
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pipeline.run', '--config', 'configs/active.yml'],
            check=True,
            capture_output=False
        )
        
        print("\n✅ Pipeline completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Pipeline failed with error code {e.returncode}")
        print("Check the error messages above for details.")
        return False
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        return False


def show_next_steps():
    """Show instructions for starting API and UI."""
    print_banner("Next Steps")
    
    print("Pipeline complete! Now start the API and UI:\n")
    
    print("📡 STEP 1: Start the API (in a new terminal)")
    print("-" * 70)
    print("  Windows:")
    print("    venv\\Scripts\\activate")
    print("    uvicorn api.main:app --host 0.0.0.0 --port 8000")
    print()
    print("  Mac/Linux:")
    print("    source venv/bin/activate")
    print("    uvicorn api.main:app --host 0.0.0.0 --port 8000")
    print()
    print("  Or simply:")
    print("    make serve-api")
    print()
    
    print("🌐 STEP 2: Launch the UI (in another new terminal)")
    print("-" * 70)
    print("  Windows:")
    print("    venv\\Scripts\\activate")
    print("    streamlit run ui/app.py --server.port 8501")
    print()
    print("  Mac/Linux:")
    print("    source venv/bin/activate")
    print("    streamlit run ui/app.py --server.port 8501")
    print()
    print("  Or simply:")
    print("    make serve-ui")
    print()
    
    print("🔥 STEP 3: Open the UI in your browser")
    print("-" * 70)
    print("  Navigate to: http://localhost:8501")
    print()
    
    print("📚 Additional Resources")
    print("-" * 70)
    print("  • API Documentation: http://localhost:8000/docs")
    print("  • Setup Guide: docs/POC_SETUP.md")
    print("  • Main README: README.md")
    print("  • POC Overview: README_POC.md")
    print()


def main():
    """Main demo script."""
    print_banner("EmberGuide POC Demo")
    
    print("This script will guide you through running the EmberGuide POC.\n")
    
    # Check setup
    if not check_setup():
        print("\n❌ Setup incomplete. Please run:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    print("\n✅ Setup verified!\n")
    
    # Run pipeline
    if not run_pipeline():
        print("\n⚠️  Pipeline did not complete successfully.")
        print("You may need to fix errors before proceeding.")
        sys.exit(1)
    
    # Show next steps
    show_next_steps()
    
    print_banner("Demo Script Complete")
    print("Follow the steps above to start the API and UI.")
    print("Enjoy exploring EmberGuide! 🔥\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user. Goodbye!")
        sys.exit(0)

