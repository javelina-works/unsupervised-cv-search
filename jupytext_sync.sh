#!/bin/bash
SOURCE_DIR="content/notebooks"
TARGET_DIR="content/notebooks/jupytext"
source venv/bin/activate
mkdir -p "$TARGET_DIR"
# jupytext --to py,md "$SOURCE_DIR"/*.ipynb --output "$TARGET_DIR"

# Configure paired formats for .ipynb, .py, and .md
jupytext --set-formats ipynb,py,md "$SOURCE_DIR"/*.ipynb --sync --output "$TARGET_DIR"
