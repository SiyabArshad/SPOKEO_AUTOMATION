@echo off
echo ========================================================
echo Spokeo Automator Setup ^& Run Script
echo ========================================================
echo.

echo [1/4] Installing/Verifying Python dependencies...
python -m pip install streamlit playwright -q

echo.
echo [2/4] Installing/Verifying Playwright browsers...
python -m playwright install chromium

echo.
echo [3/4] Launching Chrome with debugging port (closing any existing Chrome first)...
taskkill /F /IM chrome.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --profile-directory=Default --no-first-run --no-default-browser-check
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --profile-directory=Default --no-first-run --no-default-browser-check
) else (
    echo ERROR: Could not find Chrome installation!
    pause
    exit /b 1
)

echo Waiting for Chrome to start...
timeout /t 5 /nobreak >nul

echo.
echo [4/4] Starting Streamlit...
echo.
echo ================================================================
echo  IMPORTANT: Open the Streamlit URL in Microsoft Edge or Firefox
echo  NOT in the Chrome window that just opened (that one is for scraping)
echo ================================================================
echo.
python -m streamlit run app.py

pause
