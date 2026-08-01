#!/bin/bash
set -e

# Build script for Render
echo "Building Land Scanner Prototype..."

# Ensure we're using the correct Python version
python --version

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

echo "Build completed successfully!"
