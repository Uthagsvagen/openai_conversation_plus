#!/usr/bin/env python3
"""
Test runner for OpenAI Conversation Plus integration.

This script sets up the test environment and runs pytest with proper configuration.
It can be run as a background agent for continuous testing.
"""
import os
import sys
import subprocess
import venv
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
VENV_DIR = Path(__file__).parent / "venv_test"
REQUIREMENTS_FILE = Path(__file__).parent / "requirements_test.txt"


def create_virtual_environment():
    """Create a virtual environment for testing."""
    logger.info(f"Creating virtual environment at {VENV_DIR}")
    venv.create(VENV_DIR, with_pip=True)
    

def get_pip_path():
    """Get the path to pip in the virtual environment."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def get_python_path():
    """Get the path to python in the virtual environment."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def install_dependencies():
    """Install test dependencies."""
    pip_path = get_pip_path()
    logger.info("Installing test dependencies...")
    
    # Upgrade pip first
    subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
    
    # Install requirements
    subprocess.run([str(pip_path), "install", "-r", str(REQUIREMENTS_FILE)], check=True)
    
    # Install the integration in development mode
    subprocess.run([str(pip_path), "install", "-e", "."], check=True)
    
    logger.info("Dependencies installed successfully")


def run_pre_commit():
    """Run pre-commit hooks."""
    logger.info("Running pre-commit hooks...")
    python_path = get_python_path()
    
    try:
        # Install pre-commit hooks
        subprocess.run([str(python_path), "-m", "pre_commit", "install"], check=True)
        
        # Run pre-commit on all files
        result = subprocess.run(
            [str(python_path), "-m", "pre_commit", "run", "--all-files"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning("Pre-commit checks failed:")
            logger.warning(result.stdout)
            logger.warning(result.stderr)
        else:
            logger.info("Pre-commit checks passed")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Pre-commit failed: {e}")


def run_pytest():
    """Run pytest tests."""
    logger.info("Running pytest...")
    python_path = get_python_path()
    
    # Set PYTHONPATH to include custom_components
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)
    
    try:
        result = subprocess.run(
            [str(python_path), "-m", "pytest", "-v"],
            env=env,
            capture_output=True,
            text=True
        )
        
        logger.info("Test output:")
        print(result.stdout)
        
        if result.stderr:
            logger.error("Test errors:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Pytest failed: {e}")
        return False


def run_hassfest():
    """Run hassfest validation."""
    logger.info("Running hassfest validation...")
    python_path = get_python_path()
    
    try:
        result = subprocess.run(
            [str(python_path), "-m", "hassfest", "--action", "validate"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning("Hassfest validation failed:")
            logger.warning(result.stdout)
            logger.warning(result.stderr)
        else:
            logger.info("Hassfest validation passed")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Hassfest failed: {e}")


def main():
    """Main test runner function."""
    logger.info("Starting OpenAI Conversation Plus test runner")
    
    # Create virtual environment if it doesn't exist
    if not VENV_DIR.exists():
        create_virtual_environment()
        install_dependencies()
    else:
        logger.info("Virtual environment already exists")
    
    # Run static checks
    logger.info("\n" + "="*50)
    logger.info("Running static checks...")
    logger.info("="*50)
    run_pre_commit()
    
    # Run hassfest validation
    logger.info("\n" + "="*50)
    logger.info("Running manifest validation...")
    logger.info("="*50)
    run_hassfest()
    
    # Run tests
    logger.info("\n" + "="*50)
    logger.info("Running tests...")
    logger.info("="*50)
    test_passed = run_pytest()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("Test run complete!")
    logger.info("="*50)
    
    if test_passed:
        logger.info("All tests passed! ✅")
        return 0
    else:
        logger.error("Some tests failed! ❌")
        return 1


if __name__ == "__main__":
    sys.exit(main())
