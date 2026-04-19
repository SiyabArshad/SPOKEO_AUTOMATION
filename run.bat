@echo off
echo ========================================================
echo Spokeo Automator Setup ^& Run Script
echo ========================================================
echo.

echo [1/2] Installing/Verifying Python dependencies...
python -m pip install streamlit selenium -q

echo.
echo [2/2] Starting Streamlit...
echo.
echo  Open the URL below in your browser.
echo  On first scrape, Chrome will open automatically and log into Spokeo.
echo  After that, the session is saved and login is skipped!
echo.
python -m streamlit run app.py

pause
