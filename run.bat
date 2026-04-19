@echo off
echo ========================================================
echo Spokeo Automator Setup ^& Run Script
echo ========================================================
echo.

echo [1/3] Installing/Verifying Python dependencies...
python -m pip install streamlit playwright

echo.
echo [2/3] Installing/Verifying Playwright browsers...
python -m playwright install chromium

echo.
echo [3/3] Starting the application...
echo REMINDER: Please make sure Chrome is fully closed from your System Tray!
echo.
python -m streamlit run app.py

pause
