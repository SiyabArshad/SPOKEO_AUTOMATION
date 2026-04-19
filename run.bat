@echo off
echo ========================================================
echo Spokeo Automator Setup ^& Run Script
echo ========================================================
echo.

echo [1/3] Installing/Verifying Python dependencies...
python -m pip install streamlit playwright -q

echo.
echo [2/3] Installing/Verifying Playwright browsers...
python -m playwright install chromium

echo.
echo [3/3] Closing any open Chrome windows to free profile lock...
taskkill /F /IM chrome.exe /T >nul 2>&1
timeout /t 5 /nobreak >nul
echo Chrome closed. Profile is free.

echo.
echo ================================================================
echo  Starting Streamlit...
echo  Open the URL below in Microsoft Edge or Firefox (NOT Chrome)
echo  Chrome will be used automatically by the scraper in background
echo ================================================================
echo.
python -m streamlit run app.py

pause
