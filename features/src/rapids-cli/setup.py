#!/usr/bin/env python3
"""
RAPIDS CLI - Modern Python-based build system for RAPIDS

This file exists for compatibility but pyproject.toml is the primary configuration.
"""

from setuptools import setup

# Configuration is in pyproject.toml
# This setup.py exists for:
# 1. Backward compatibility with older pip versions
# 2. Editable installs (pip install -e .)
# 3. Direct setup.py install (deprecated but still works)

setup()

