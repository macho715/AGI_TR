"""Pytest configuration and fixtures"""
import pytest
from pathlib import Path

@pytest.fixture
def project_root():
    return Path(__file__).parent.parent

@pytest.fixture
def execution_dir(project_root):
    return project_root / "01_EXECUTION_FILES"
