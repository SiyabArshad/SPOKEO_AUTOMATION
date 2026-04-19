#!/bin/bash

echo "========================================================"
echo "Spokeo Automator Setup & Run Script"
echo "========================================================"
echo ""

echo "[1/3] Installing/Verifying Python dependencies..."
pip install -r requirements.txt

echo ""
echo "[2/3] Installing/Verifying Playwright browsers..."
playwright install chromium

echo ""
echo "[3/3] Starting the application..."
echo "REMINDER: Please make sure Chrome is fully closed from your System Tray!"
echo ""
streamlit run app.py
