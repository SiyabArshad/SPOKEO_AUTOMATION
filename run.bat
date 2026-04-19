@echo off
echo ========================================================
echo Spokeo Automator Setup ^& Run Script
echo ========================================================
echo.

echo [1/2] Installing/Verifying Python dependencies...
python -m pip install streamlit selenium undetected-chromedriver -q

echo.
echo [2/2] Starting Streamlit...
echo.
echo ================================================================
echo  Open the URL below in Microsoft Edge or Firefox (NOT Chrome)
echo  Chrome will open automatically in the background when scraping
echo ================================================================
echo.
python -m streamlit run app.py

pause
